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
        background: $surface;
    }
    
    #main-container {
        height: 100%;
    }
    
    #input-container {
        dock: bottom;
        height: auto;
        background: $panel;
        padding: 1 2;
        border-top: heavy $primary;
    }
    
    Input {
        width: 100%;
    }
    
    Header {
        background: $primary;
    }
    
    Footer {
        background: $primary-darken-1;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear", "Clear", show=True),
        Binding("ctrl+r", "reset", "Reset", show=False),
        Binding("ctrl+h", "help", "Help", show=True),
        Binding("ctrl+w", "workspace_info", "Workspace", show=True),
    ]
    
    TITLE = "Codex CLI - AI Coding Assistant"
    
    def __init__(self, workspace_path: Path):
        super().__init__()
        self.workspace_path = workspace_path
        self.client = CodexClient(self.workspace_path)
        self.is_processing = False
        self.sub_title = f"📁 {self.workspace_path.name}"
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with Vertical(id="main-container"):
            yield ConversationView()
            
            with Container(id="input-container"):
                yield Input(
                    placeholder="Ask me anything about your code... (Press Enter to send)",
                    id="message-input"
                )
        
        yield StatusBar(workspace_path=self.workspace_path)
        yield Footer()
    
    async def on_mount(self) -> None:
        """Called when app starts."""
        # Show welcome message
        conv_view = self.query_one(ConversationView)
        
        welcome_msg = f"""# Welcome to Codex CLI! 🚀

I'm your AI coding assistant powered by **Claude 3.5 Sonnet**. I can help you with:

- 📝 Reading and writing files
- 🔍 Searching your codebase
- 🏃 Running shell commands
- 🐛 Debugging code
- 💡 Generating new code
- 📚 Explaining complex concepts

**Workspace:** `{self.workspace_path}`

**Available Tools:**
- `read_file` - Read file contents
- `write_file` - Create or update files
- `list_directory` - List directory contents
- `execute_command` - Run shell commands
- `search_files` - Find files by pattern
- `delete_file` - Remove files
- `get_workspace_info` - Get workspace information

**Keyboard Shortcuts:**
- `Ctrl+C` - Quit
- `Ctrl+L` - Clear conversation
- `Ctrl+H` - Show this help
- `Ctrl+W` - Show workspace info

What can I help you with today?
"""
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
        
        # Update status
        status_bar = self.query_one(StatusBar)
        status_bar.set_thinking()
        
        self.is_processing = True
        
        try:
            # Track assistant response
            assistant_response = []
            
            # Send message and handle tool calls
            async for content, tool_info in self.client.send_message(message):
                if tool_info:
                    # Handle tool call or result
                    if tool_info["type"] == "tool_call":
                        tool_msg = f"**Calling:** `{tool_info['name']}`\n**Arguments:** ```json\n{json.dumps(tool_info['arguments'], indent=2)}\n```"
                        conv_view.add_message("tool_call", tool_msg)
                    
                    elif tool_info["type"] == "tool_result":
                        conv_view.add_message("tool_result", tool_info["result"])
                
                else:
                    # Regular content
                    if content:
                        assistant_response.append(content)
            
            # Add final assistant response if any
            if assistant_response:
                final_response = "".join(assistant_response)
                conv_view.add_message("assistant", final_response)
        
        except Exception as e:
            conv_view.add_message("error", f"An error occurred: {str(e)}")
            status_bar.set_error(str(e))
        
        finally:
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
        
        # Add welcome message again
        conv_view.add_message("assistant", "Conversation cleared. How can I help you?")
    
    def action_reset(self) -> None:
        """Reset the application."""
        self.action_clear()
        status_bar = self.query_one(StatusBar)
        status_bar.set_ready()
    
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
        
        workspace_info = f"""# Workspace Information

**Path:** `{self.workspace_path}`  
**Absolute Path:** `{self.workspace_path.resolve()}`  
**Name:** `{self.workspace_path.name}`  
**Parent:** `{self.workspace_path.parent}`

**Statistics:**
- Files: {file_count}
- Directories: {dir_count}

**Tip:** To work in a different directory:
- Quit this session (Ctrl+C)
- Run: `codex /path/to/other/directory`
- Or: `codex ../relative/path`

**Example:**
```bash
# Open a specific project
codex ~/projects/my-app

# Open parent directory
codex ..

# Open from anywhere
codex /absolute/path/to/project
```
"""
        conv_view.add_message("assistant", workspace_info)
    
    def action_help(self) -> None:
        """Show help message."""
        conv_view = self.query_one(ConversationView)
        
        help_msg = """# Codex CLI Help

## Keyboard Shortcuts
- `Ctrl+C` - Quit the application
- `Ctrl+L` - Clear conversation history
- `Ctrl+H` - Show this help message
- `Ctrl+W` - Show workspace information

## Available Tools

### File Operations
- **read_file** - Read contents of a file
- **write_file** - Create or update a file
- **delete_file** - Remove a file
- **search_files** - Find files matching a pattern

### Directory Operations
- **list_directory** - List contents of a directory
- **get_workspace_info** - Get current workspace information

### Command Execution
- **execute_command** - Run shell commands (use with caution)

## Working with Different Directories

To open a different workspace:
1. Press `Ctrl+C` to quit
2. Run `codex /path/to/directory`

Examples:
- `codex ~/projects/my-app` - Open specific project
- `codex ..` - Open parent directory
- `codex /absolute/path` - Open absolute path

## Tips
- Be specific in your requests
- I can handle multiple files at once
- I'll automatically use tools when needed
- You can ask me to explain what I'm doing

## Examples
- "Read the README.md file"
- "Create a new Python file called hello.py with a hello world function"
- "List all Python files in the current directory"
- "Execute the command 'ls -la'"
- "Search for all .js files in the src directory"
"""
        conv_view.add_message("assistant", help_msg)


def run(workspace_path: Path = None):
    """Run the Codex CLI application."""
    if workspace_path is None:
        workspace_path = Config.WORKSPACE_PATH
    
    app = CodexApp(workspace_path)
    app.run()
