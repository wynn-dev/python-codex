"""Custom Textual widgets for Codex CLI."""

import time
import json
from pathlib import Path
from textual.widgets import Static, Collapsible
from textual.containers import Container, VerticalScroll
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.text import Text


class LoadingWidget(Static):
    """Animated loading indicator."""
    
    DEFAULT_CSS = """
    LoadingWidget {
        margin: 0 0 1 0;
        padding: 1 2;
        background: #1a1a1a;
        border-left: solid #6a6a6a;
    }
    
    LoadingWidget.tool-loading {
        background: #1a1a0a;
        border-left: solid #7a7a3a;
    }
    """
    
    # Spinner frames - braille dots animation
    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    # Additional animation for dots
    DOTS = ["", ".", "..", "..."]
    
    def __init__(self, message: str = "loading", is_tool: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.is_tool = is_tool
        self.frame = 0
        self.dots_frame = 0
        self.is_active = True
        if is_tool:
            self.add_class("tool-loading")
        self._update_display()
    
    def on_mount(self) -> None:
        """Start animation when mounted."""
        self.set_interval(0.08, self.advance_frame)
    
    def advance_frame(self) -> None:
        """Advance to next animation frame."""
        if not self.is_active:
            return
        self.frame = (self.frame + 1) % len(self.SPINNER)
        self.dots_frame = (self.dots_frame + 1) % len(self.DOTS)
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the display with current frame."""
        text = Text()
        spinner_style = "bold #bbbb55" if self.is_tool else "bold #888888"
        message_style = "#cccc88" if self.is_tool else "#999999"
        
        text.append(f"{self.SPINNER[self.frame]} ", style=spinner_style)
        text.append(self.message, style=message_style)
        text.append(self.DOTS[self.dots_frame], style="#777777")
        self.update(text)
    
    def stop(self) -> None:
        """Stop the animation."""
        self.is_active = False
    
    def update_message(self, message: str) -> None:
        """Update the loading message."""
        self.message = message
        self._update_display()


class StreamingMessageWidget(Static):
    """Widget for displaying a streaming message that updates in real-time."""
    
    DEFAULT_CSS = """
    StreamingMessageWidget {
        margin: 0 0 1 0;
        padding: 1 2;
        background: #121212;
        border-left: solid #3a3a3a;
    }
    """
    
    # Animation frames for cursor
    CURSOR_FRAMES = ["│", "│", " ", " "]
    
    def __init__(self, role: str = "assistant", **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content_buffer = ""
        self.cursor_frame = 0
        self.is_streaming = True
    
    def on_mount(self) -> None:
        """Start cursor animation when mounted."""
        self.set_interval(0.5, self.advance_cursor)
    
    def advance_cursor(self) -> None:
        """Advance cursor animation."""
        if not self.is_streaming:
            return
        self.cursor_frame = (self.cursor_frame + 1) % len(self.CURSOR_FRAMES)
        self._update_display()
    
    def append_content(self, text: str):
        """Append content to the message."""
        self.content_buffer += text
        self._update_display()
    
    def _update_display(self):
        """Update the widget display."""
        if self.content_buffer:
            cursor = self.CURSOR_FRAMES[self.cursor_frame] if self.is_streaming else ""
            display_content = self.content_buffer + cursor
            self.update(Markdown(display_content))
    
    def finalize(self):
        """Finalize the message (stop animation, remove cursor)."""
        self.is_streaming = False
        
        if self.content_buffer:
            self.update(Markdown(self.content_buffer))


class CollapsibleThinkingWidget(Collapsible):
    """Collapsible widget showing thinking duration and content."""
    
    DEFAULT_CSS = """
    CollapsibleThinkingWidget {
        margin: 0 0 1 0;
        padding: 0;
        background: #0d0d0d;
        height: auto;
    }
    
    CollapsibleThinkingWidget > CollapsibleTitle {
        background: #0d0d0d;
        color: #666666;
        padding: 0 2;
    }
    
    CollapsibleThinkingWidget > CollapsibleTitle:hover {
        background: #121212;
        color: #888888;
    }
    
    CollapsibleThinkingWidget > Contents {
        padding: 1 2;
        background: #0d0d0d;
        border-left: solid #3a3a3a;
    }
    """
    
    def __init__(self, duration: float, thinking_content: str, **kwargs):
        # Create title with duration
        title_text = f"thought for {duration:.1f} seconds"
        self.thinking_content = thinking_content
        super().__init__(title=title_text, collapsed=True, **kwargs)
    
    def compose(self):
        """Compose the collapsible content."""
        content_widget = Static()
        content_text = Text()
        content_text.append(self.thinking_content, style="#888888 italic")
        content_widget.update(content_text)
        yield content_widget


class ToolCallWidget(Static):
    """Simplified tool call display with spinner and status."""
    
    DEFAULT_CSS = """
    ToolCallWidget {
        margin: 0 0 1 0;
        padding: 1 2;
        background: #121212;
        border-left: solid #3a3a3a;
        height: auto;
    }
    
    ToolCallWidget.executing {
        border-left: solid #7a7a5a;
    }
    
    ToolCallWidget.completed {
        border-left: solid #5a7a5a;
    }
    
    ToolCallWidget.error {
        border-left: solid #7a4a4a;
    }
    """
    
    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(self, tool_name: str, tool_args: dict, **kwargs):
        super().__init__("", **kwargs)
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.status = "executing"
        self.spinner_frame = 0
        self._spinner_interval = None
    
    def _get_description(self) -> str:
        """Get a brief description of the tool action."""
        args = self.tool_args
        if self.tool_name == "read_file":
            return args.get('file_path', 'file')
        elif self.tool_name == "write_file":
            return args.get('file_path', 'file')
        elif self.tool_name == "delete_file":
            return args.get('file_path', 'file')
        elif self.tool_name == "list_directory":
            return args.get('directory_path', '.') or '.'
        elif self.tool_name == "execute_command":
            cmd = args.get('command', '')
            return cmd if len(cmd) < 50 else cmd[:47] + "..."
        elif self.tool_name == "search_files":
            return args.get('pattern', '*')
        return ""
    
    def render(self) -> Text:
        """Render the tool call display."""
        # Ensure we have required attributes
        if not hasattr(self, 'tool_name'):
            return Text("loading...", style="#888888")
        
        text = Text()
        
        # Status indicator
        status = getattr(self, 'status', 'executing')
        spinner_frame = getattr(self, 'spinner_frame', 0)
        
        if status == "executing":
            text.append(f"{self.SPINNER[spinner_frame]} ", style="bold #888888")
        elif status == "completed":
            text.append("✓ ", style="bold #5a7a5a")
        elif status == "error":
            text.append("✗ ", style="bold #7a4a4a")
        
        # Tool name and description
        text.append(self.tool_name.replace("_", " "), style="#cccccc")
        desc = self._get_description()
        if desc:
            text.append(f" → {desc}", style="#888888")
        
        return text
    
    def set_status(self, status: str):
        """Update the status of the tool call."""
        self.status = status
        self.remove_class("executing", "completed", "error")
        self.add_class(status)
        
        # Start/stop spinner based on status
        if status == "executing":
            self._start_spinner()
        else:
            self._stop_spinner()
        
        # Trigger re-render
        self.refresh()
    
    def on_mount(self) -> None:
        """Start spinner if executing."""
        if self.status == "executing":
            self._start_spinner()
    
    def on_unmount(self) -> None:
        """Clean up spinner."""
        self._stop_spinner()
    
    def _start_spinner(self):
        """Start the spinner animation."""
        if not hasattr(self, '_spinner_interval'):
            self._spinner_interval = None
        if self._spinner_interval is None and self.is_mounted:
            self._spinner_interval = self.set_interval(0.08, self._advance_spinner)
    
    def _stop_spinner(self):
        """Stop the spinner animation."""
        if hasattr(self, '_spinner_interval') and self._spinner_interval is not None:
            self._spinner_interval.stop()
            self._spinner_interval = None
    
    def _advance_spinner(self) -> None:
        """Advance spinner animation."""
        if self.status != "executing":
            self._stop_spinner()
            return
        self.spinner_frame = (self.spinner_frame + 1) % len(self.SPINNER)
        self.refresh()


class ToolResultWidget(Static):
    """Simplified tool result display with basic formatting."""
    
    DEFAULT_CSS = """
    ToolResultWidget {
        margin: 0 0 1 0;
        padding: 1 2;
        background: #0d0d0d;
        border-left: solid #3a3a3a;
        height: auto;
    }
    
    ToolResultWidget.error {
        border-left: solid #7a4a4a;
        background: #0a0a0a;
    }
    """
    
    def __init__(self, tool_name: str, result: str, is_error: bool = False, **kwargs):
        super().__init__("", **kwargs)
        self.tool_name = tool_name
        self.result = result
        self.is_error = is_error
        
        if is_error:
            self.add_class("error")
    
    def render(self):
        """Render the result."""
        # Ensure we have required attributes
        if not hasattr(self, 'tool_name') or not hasattr(self, 'result'):
            return Text("loading...", style="#888888")
        
        return self._format_content()
    
    def _format_content(self):
        """Format the result content. Returns Rich renderable."""
        if self.is_error:
            text = Text()
            text.append(self.result[:500], style="#dd7777")
            if len(self.result) > 500:
                text.append("...", style="#666666")
            return text
        
        # Format based on tool type
        if self.tool_name == "read_file":
            # Use syntax highlighting for code
            if self.result.startswith("File:"):
                parts = self.result.split("\n\n", 1)
                if len(parts) == 2:
                    file_path = parts[0].replace("File: ", "")
                    content = parts[1]
                    
                    # Detect language
                    ext = Path(file_path).suffix
                    lang_map = {
                        ".py": "python", ".js": "javascript", ".ts": "typescript",
                        ".json": "json", ".md": "markdown", ".html": "html",
                        ".css": "css", ".sh": "bash", ".rs": "rust", ".go": "go",
                    }
                    language = lang_map.get(ext, "text")
                    
                    # Limit lines
                    lines = content.split("\n")
                    if len(lines) > 100:
                        content = "\n".join(lines[:100]) + f"\n\n... ({len(lines) - 100} more lines)"
                    
                    return Syntax(content, language, theme="monokai", line_numbers=False)
            
            return Text(self.result[:2000], style="#999999")
        
        elif self.tool_name == "list_directory":
            return self._format_directory_listing()
        
        elif self.tool_name == "execute_command":
            return self._format_command_output()
        
        # Default: plain text, truncated
        text = Text()
        if len(self.result) > 2000:
            text.append(self.result[:2000], style="#999999")
            text.append("\n...", style="#666666")
        else:
            text.append(self.result, style="#999999")
        return text
    
    def _format_directory_listing(self) -> Text:
        """Format directory listing simply."""
        text = Text()
        lines = self.result.split("\n")
        
        # Show first 50 items
        for i, line in enumerate(lines[:50]):
            if i > 0 and line.strip():  # Skip header
                text.append(line + "\n", style="#999999")
        
        if len(lines) > 50:
            text.append(f"\n... and {len(lines) - 50} more items", style="#666666")
        
        return text
    
    def _format_command_output(self) -> Text:
        """Format command output with sections."""
        text = Text()
        
        if "STDOUT:" in self.result:
            parts = self.result.split("STDOUT:")
            if len(parts) > 1:
                stdout = parts[1].split("STDERR:")[0].strip()
                if stdout:
                    text.append(stdout[:1000], style="#999999")
                    if len(stdout) > 1000:
                        text.append("\n...", style="#666666")
        
        if "STDERR:" in self.result:
            parts = self.result.split("STDERR:")
            if len(parts) > 1:
                stderr = parts[1].split("Exit code:")[0].strip()
                if stderr:
                    if text.plain:
                        text.append("\n\n", style="")
                    text.append(stderr[:1000], style="#aa6666")
        
        if "Exit code:" in self.result:
            exit_code = self.result.split("Exit code:")[-1].strip()
            if text.plain:
                text.append(" ", style="")
            code_style = "#7a9a7a" if exit_code == "0" else "#9a7a7a"
            text.append(f"[exit: {exit_code}]", style=code_style)
        
        return text


class MessageWidget(Static):
    """Widget for displaying a single message."""
    
    DEFAULT_CSS = """
    MessageWidget {
        margin: 0 0 1 0;
        padding: 1 2;
        background: #0d0d0d;
    }
    
    MessageWidget.user-message {
        background: #121212;
        border-left: solid #3a3a3a;
    }
    
    MessageWidget.assistant-message {
        background: #0d0d0d;
        border-left: solid #2a2a2a;
    }
    
    MessageWidget.error-message {
        background: #1a0a0a;
        border-left: solid #4a2a2a;
    }
    
    MessageWidget.thinking-message {
        background: #121212;
        border-left: solid #3a3a3a;
    }
    """
    
    def __init__(self, role: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.message_content = content
        self._update_display()
    
    def _update_display(self):
        """Update the widget display."""
        if self.role == "user":
            self.add_class("user-message")
            content = Text()
            content.append("you\n", style="#777777")
            content.append(self.message_content, style="#dddddd")
            self.update(content)
            
        elif self.role == "assistant":
            self.add_class("assistant-message")
            self.update(Markdown(self.message_content))
            
        elif self.role == "thinking":
            self.add_class("thinking-message")
            thinking_text = Text()
            thinking_text.append("thinking\n", style="#777777")
            thinking_text.append(self.message_content, style="#888888 italic")
            self.update(thinking_text)
            
        elif self.role == "error":
            self.add_class("error-message")
            text = Text()
            text.append("error\n", style="#cc5555")
            text.append(self.message_content, style="#dd7777")
            self.update(text)


class ConversationView(VerticalScroll):
    """Container for displaying the conversation."""
    
    DEFAULT_CSS = """
    ConversationView {
        background: #0d0d0d;
        height: 1fr;
        border: none;
        padding: 1 0;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.streaming_widget = None
        self.thinking_content = ""
        self.loading_widget = None
        self.thinking_start_time = None
        self.current_tool_widgets: dict[str, ToolCallWidget] = {}  # Map tool_call_id -> widget
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation."""
        message = MessageWidget(role, content)
        self.mount(message)
        # Auto-scroll to bottom
        self.scroll_end(animate=False)
    
    def show_loading(self, message: str = "loading", is_tool: bool = False):
        """Show an animated loading indicator."""
        if self.loading_widget:
            self.loading_widget.remove()
        
        self.loading_widget = LoadingWidget(message, is_tool=is_tool)
        self.mount(self.loading_widget)
        self.scroll_end(animate=False)
        return self.loading_widget
    
    def hide_loading(self):
        """Hide the loading indicator."""
        if self.loading_widget:
            self.loading_widget.stop()
            self.loading_widget.remove()
            self.loading_widget = None
    
    def start_streaming(self, role: str = "assistant"):
        """Start a streaming message."""
        # Hide any loading indicator
        self.hide_loading()
        
        if self.streaming_widget:
            self.streaming_widget.finalize()
        
        self.streaming_widget = StreamingMessageWidget(role)
        self.mount(self.streaming_widget)
        self.scroll_end(animate=False)
        return self.streaming_widget
    
    def append_to_stream(self, text: str):
        """Append text to the current streaming message."""
        if self.streaming_widget:
            self.streaming_widget.append_content(text)
            self.scroll_end(animate=False)
    
    def start_thinking(self):
        """Start showing thinking/reasoning with a loader."""
        # Start timing
        self.thinking_start_time = time.time()
        # Show loader below current content
        self.show_loading("thinking", is_tool=False)
    
    def append_thinking(self, text: str):
        """Append to thinking content (stored but not displayed)."""
        # Just accumulate thinking content without displaying it
        self.thinking_content += text
    
    def end_thinking(self):
        """End the thinking phase and show collapsible summary."""
        # Hide the thinking loader
        self.hide_loading()
        
        # Calculate duration and show collapsible thinking widget
        if self.thinking_start_time is not None and self.thinking_content:
            duration = time.time() - self.thinking_start_time
            collapsible_widget = CollapsibleThinkingWidget(duration, self.thinking_content)
            self.mount(collapsible_widget)
            self.scroll_end(animate=False)
            self.thinking_start_time = None
        
        self.thinking_content = ""  # Clear stored thinking content
    
    def finalize_stream(self):
        """Finalize the current streaming message."""
        if self.streaming_widget:
            self.streaming_widget.finalize()
            self.streaming_widget = None
            self.thinking_content = ""
            self.thinking_start_time = None
    
    def add_tool_call(self, tool_name: str, tool_args: dict, tool_call_id: str = None):
        """Add a tool call widget."""
        tool_widget = ToolCallWidget(tool_name, tool_args)
        self.mount(tool_widget)
        self.scroll_end(animate=False)
        
        if tool_call_id:
            self.current_tool_widgets[tool_call_id] = tool_widget
        
        return tool_widget
    
    def update_tool_status(self, tool_call_id: str, status: str):
        """Update the status of a tool call."""
        if tool_call_id in self.current_tool_widgets:
            self.current_tool_widgets[tool_call_id].set_status(status)
    
    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str, is_error: bool = False):
        """Add a result widget."""
        # Update tool call status if it exists
        if tool_call_id in self.current_tool_widgets:
            self.current_tool_widgets[tool_call_id].set_status("error" if is_error else "completed")
        
        # Add result widget
        result_widget = ToolResultWidget(tool_name, result, is_error=is_error)
        self.mount(result_widget)
        self.scroll_end(animate=False)
    
    def clear_messages(self):
        """Clear all messages."""
        self.streaming_widget = None
        self.thinking_content = ""
        self.loading_widget = None
        self.thinking_start_time = None
        self.current_tool_widgets = {}
        self.remove_children()


class StatusBar(Static):
    """Status bar widget."""
    
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: #0d0d0d;
        color: #666666;
        padding: 0 2;
    }
    """
    
    # Spinner for status bar
    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(self, workspace_path: Path = None, **kwargs):
        super().__init__("", **kwargs)
        self.workspace_path = workspace_path
        self.is_busy = False
        self.spinner_frame = 0
        self.current_message = "ready"
        self.update_status()
    
    def on_mount(self) -> None:
        """Start status bar animation."""
        self.set_interval(0.08, self.advance_spinner)
    
    def advance_spinner(self) -> None:
        """Advance spinner animation."""
        if not self.is_busy:
            return
        self.spinner_frame = (self.spinner_frame + 1) % len(self.SPINNER)
        self._render_status()
    
    def update_status(self, message: str = "ready"):
        """Update the status bar."""
        self.current_message = message
        self.is_busy = message not in ["ready", ""]
        self._render_status()
    
    def _render_status(self):
        """Render the status bar."""
        status_text = Text()
        
        if self.workspace_path:
            status_text.append(f"{self.workspace_path.name}", style="#777777")
            status_text.append(" · ", style="#555555")
        
        if self.is_busy:
            status_text.append(f"{self.SPINNER[self.spinner_frame]} ", style="bold #999999")
        
        status_text.append(self.current_message, style="#999999" if self.is_busy else "#888888")
        self.update(status_text)
    
    def set_thinking(self):
        """Set status to thinking."""
        self.update_status("thinking")
    
    def set_streaming(self):
        """Set status to streaming."""
        self.update_status("streaming")
    
    def set_ready(self):
        """Set status to ready."""
        self.update_status("ready")
    
    def set_error(self, error: str):
        """Set status to error."""
        self.is_busy = False
        status_text = Text()
        if self.workspace_path:
            status_text.append(f"{self.workspace_path.name}", style="#777777")
            status_text.append(" · ", style="#555555")
        status_text.append(error, style="#cc5555")
        self.update(status_text)
