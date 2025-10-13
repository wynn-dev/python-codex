"""Main Textual application for Codex CLI."""

import json
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input
from textual.containers import Container, Vertical
from textual.binding import Binding
from rich.panel import Panel
from rich.text import Text

from .client import CodexClient
from .widgets import ConversationView, StatusBar
from .config import Config


class CodexApp(App):
    """Main application for Codex CLI."""
    
    CSS = """
    Screen {
        background: #0d0d0d;
    }
    
    #main-container {
        height: 100%;
        background: #0d0d0d;
    }
    
    #input-container {
        dock: bottom;
        height: auto;
        background: #121212;
        padding: 1 2;
        border-top: solid #2a2a2a;
    }
    
    Input {
        width: 100%;
        background: #121212;
        border: none;
        padding: 0 0;
    }
    
    Input:focus {
        border: none;
    }
    
    Header {
        background: #0d0d0d;
        color: #888888;
        height: 1;
        padding: 0 2;
    }
    
    Footer {
        background: #0d0d0d;
        color: #666666;
        height: 1;
    }
    
    ConversationView {
        scrollbar-background: #0d0d0d;
        scrollbar-color: #3a3a3a;
        scrollbar-color-hover: #4a4a4a;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear", "Clear", show=True),
        Binding("ctrl+h", "help", "Help", show=True),
        Binding("ctrl+w", "workspace_info", "Info", show=True),
    ]
    
    TITLE = "codex"
    
    def __init__(self, workspace_path: Path):
        super().__init__()
        self.workspace_path = workspace_path
        self.client = CodexClient(self.workspace_path)
        self.is_processing = False
        self.sub_title = f"{self.workspace_path.name}"
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with Vertical(id="main-container"):
            yield ConversationView()
            
            with Container(id="input-container"):
                yield Input(
                    placeholder="›",
                    id="message-input"
                )
        
        yield StatusBar(workspace_path=self.workspace_path)
        yield Footer()
    
    async def on_mount(self) -> None:
        """Called when app starts."""
        # Show minimal welcome message
        conv_view = self.query_one(ConversationView)
        
        welcome_msg = f"""codex — ai coding assistant

workspace: {self.workspace_path}

available commands:
  ctrl+h — help
  ctrl+w — workspace info
  ctrl+l — clear history
  ctrl+c — exit

ready"""
        conv_view.add_message("assistant", welcome_msg)
        
        # Focus input
        self.query_one("#message-input", Input).focus()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        if self.is_processing:
            return
        
        message = event.value.strip()
        if not message:
            return
        
        # Clear input
        event.input.value = ""
        
        # Add user message to conversation
        conv_view = self.query_one(ConversationView)
        conv_view.add_message("user", message)
        
        # Show loading indicator
        conv_view.show_loading("processing")
        
        # Update status
        status_bar = self.query_one(StatusBar)
        status_bar.set_thinking()
        
        self.is_processing = True
        streaming_started = False
        has_content = False
        
        try:
            # Send message and handle streaming
            async for content, info in self.client.send_message(message):
                if info:
                    info_type = info.get("type")
                    
                    # Handle thinking/reasoning
                    if info_type == "thinking_start":
                        conv_view.hide_loading()
                        if not streaming_started:
                            conv_view.start_streaming()
                            streaming_started = True
                        conv_view.start_thinking()
                        status_bar.set_thinking()
                        has_content = True
                    
                    elif info_type == "reasoning":
                        if content:
                            conv_view.append_thinking(content)
                    
                    elif info_type == "thinking_end":
                        conv_view.end_thinking()
                        # Show loader while waiting for content after thinking
                        conv_view.show_loading("generating response")
                        status_bar.set_streaming()
                    
                    # Handle streaming content
                    elif info_type == "content":
                        conv_view.hide_loading()
                        if not streaming_started:
                            conv_view.start_streaming()
                            streaming_started = True
                            status_bar.set_streaming()
                        
                        if content:
                            conv_view.append_to_stream(content)
                            has_content = True
                    
                    # Handle tool calls
                    elif info_type == "tool_call":
                        if streaming_started:
                            conv_view.finalize_stream()
                            streaming_started = False
                        
                        # Format tool call in a user-friendly way
                        tool_name = info['name']
                        args = info['arguments']
                        
                        # Create readable description based on tool
                        if tool_name == "read_file":
                            tool_msg = f"{tool_name}\n→ reading {args.get('file_path', 'file')}"
                        elif tool_name == "write_file":
                            tool_msg = f"{tool_name}\n→ writing to {args.get('file_path', 'file')}"
                        elif tool_name == "delete_file":
                            tool_msg = f"{tool_name}\n→ deleting {args.get('file_path', 'file')}"
                        elif tool_name == "list_directory":
                            path = args.get('directory_path', '.')
                            tool_msg = f"{tool_name}\n→ listing {path if path else 'current directory'}"
                        elif tool_name == "execute_command":
                            cmd = args.get('command', '')
                            # Truncate long commands
                            display_cmd = cmd if len(cmd) < 50 else cmd[:47] + "..."
                            tool_msg = f"{tool_name}\n→ running: {display_cmd}"
                        elif tool_name == "search_files":
                            tool_msg = f"{tool_name}\n→ searching for {args.get('pattern', '*')}"
                        elif tool_name == "get_workspace_info":
                            tool_msg = f"{tool_name}\n→ gathering workspace stats"
                        else:
                            # Fallback for unknown tools - show args in a clean way
                            arg_str = ", ".join(f"{k}={v}" for k, v in args.items())
                            if len(arg_str) > 60:
                                arg_str = arg_str[:57] + "..."
                            tool_msg = f"{tool_name}\n→ {arg_str}"
                        
                        conv_view.add_message("tool_call", tool_msg)
                        
                        # Show loading for tool execution
                        conv_view.show_loading(f"executing {info['name']}")
                        status_bar.update_status(f"exec {info['name']}")
                    
                    elif info_type == "tool_result":
                        conv_view.hide_loading()
                        conv_view.add_message("tool_result", info["result"])
                        # Show loader while waiting for next response after tool execution
                        conv_view.show_loading("processing tool result")
                        status_bar.set_thinking()
                    
                    # Handle completion
                    elif info_type == "complete":
                        conv_view.hide_loading()
                        if streaming_started:
                            conv_view.finalize_stream()
                            streaming_started = False
                    
                    # Handle errors
                    elif info_type == "error":
                        conv_view.hide_loading()
                        if streaming_started:
                            conv_view.finalize_stream()
                            streaming_started = False
                        if content:
                            conv_view.add_message("error", content)
                        status_bar.set_error("error")
                    
                    elif info_type == "warning":
                        if content:
                            conv_view.add_message("error", content)
                
                else:
                    # Regular content without info
                    if content and not streaming_started:
                        conv_view.hide_loading()
                        conv_view.start_streaming()
                        streaming_started = True
                    
                    if content:
                        conv_view.append_to_stream(content)
                        has_content = True
            
            # Ensure stream is finalized
            if streaming_started:
                conv_view.finalize_stream()
        
        except Exception as e:
            conv_view.hide_loading()
            conv_view.add_message("error", f"error: {str(e)}")
            status_bar.set_error("error")
        
        finally:
            conv_view.hide_loading()
            self.is_processing = False
            status_bar.set_ready()
            
            # Re-focus input
            self.query_one("#message-input", Input).focus()
    
    def action_clear(self) -> None:
        """Clear the conversation."""
        conv_view = self.query_one(ConversationView)
        conv_view.clear_messages()
        
        # Also clear client history
        self.client.clear_history()
        
        # Add minimal message
        conv_view.add_message("assistant", "history cleared")
    
    def action_workspace_info(self) -> None:
        """Show workspace information."""
        conv_view = self.query_one(ConversationView)
        
        # Get workspace stats
        try:
            file_count = sum(1 for _ in self.workspace_path.rglob('*') if _.is_file())
            dir_count = sum(1 for _ in self.workspace_path.rglob('*') if _.is_dir())
        except:
            file_count = "?"
            dir_count = "?"
        
        workspace_info = f"""workspace info

path        {self.workspace_path}
absolute    {self.workspace_path.resolve()}
files       {file_count}
directories {dir_count}

to change workspace:
  codex /path/to/directory"""
        conv_view.add_message("assistant", workspace_info)
    
    def action_help(self) -> None:
        """Show help message."""
        conv_view = self.query_one(ConversationView)
        
        help_msg = """codex — help

keyboard shortcuts
  ctrl+c — quit
  ctrl+l — clear history
  ctrl+h — show help
  ctrl+w — workspace info

available tools
  read_file          read file contents
  write_file         create or update files
  delete_file        remove files
  list_directory     list directory contents
  search_files       find files by pattern
  execute_command    run shell commands
  get_workspace_info workspace statistics

workspace management
  codex ~/projects/app    open specific directory
  codex ..               open parent directory
  codex /abs/path        open absolute path

streaming features
  real-time responses
  extended reasoning (watch the ai think)
  live tool execution feedback"""
        conv_view.add_message("assistant", help_msg)


def run(workspace_path: Path = None):
    """Run the Codex CLI application."""
    if workspace_path is None:
        workspace_path = Config.WORKSPACE_PATH
    
    app = CodexApp(workspace_path)
    app.run()
