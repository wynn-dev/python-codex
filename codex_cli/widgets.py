"""Custom Textual widgets for Codex CLI."""

from pathlib import Path
from textual.widgets import Static
from textual.containers import Container, VerticalScroll
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.console import Group


class LoadingWidget(Static):
    """Animated loading indicator."""
    
    DEFAULT_CSS = """
    LoadingWidget {
        margin: 0 0 1 0;
        padding: 1 2;
        background: #121212;
        border-left: solid #5a5a5a;
    }
    """
    
    # Spinner frames - braille dots animation
    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    # Additional animation for dots
    DOTS = ["", ".", "..", "..."]
    
    def __init__(self, message: str = "loading", **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.frame = 0
        self.dots_frame = 0
        self.is_active = True
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
        text.append(f"{self.SPINNER[self.frame]} ", style="bold #888888")
        text.append(self.message, style="#999999")
        text.append(self.DOTS[self.dots_frame], style="#777777")
        self.update(text)
    
    def stop(self) -> None:
        """Stop the animation."""
        self.is_active = False


class StreamingMessageWidget(Static):
    """Widget for displaying a streaming message that updates in real-time."""
    
    DEFAULT_CSS = """
    StreamingMessageWidget {
        margin: 0 0 1 0;
        padding: 1 2;
        background: #121212;
        border-left: solid #3a3a3a;
    }
    
    StreamingMessageWidget.thinking {
        background: #121212;
        border-left: solid #4a4a4a;
    }
    """
    
    # Animation frames for cursor
    CURSOR_FRAMES = ["│", "│", " ", " "]
    
    def __init__(self, role: str = "assistant", **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content_buffer = ""
        self.is_thinking = False
        self.thinking_buffer = ""
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
    
    def append_thinking(self, text: str):
        """Append reasoning/thinking content."""
        self.thinking_buffer += text
        self.is_thinking = True
        self._update_display()
    
    def end_thinking(self):
        """End the thinking phase."""
        self.is_thinking = False
        self._update_display()
    
    def _update_display(self):
        """Update the widget display."""
        if self.is_thinking and self.thinking_buffer:
            # Show thinking content with spinner
            self.add_class("thinking")
            
            thinking_text = Text()
            thinking_text.append("thinking\n", style="#777777")
            thinking_text.append(self.thinking_buffer, style="#888888 italic")
            
            self.update(thinking_text)
        elif self.content_buffer:
            # Show regular content with animated cursor
            self.remove_class("thinking")
            
            cursor = self.CURSOR_FRAMES[self.cursor_frame] if self.is_streaming else ""
            display_content = self.content_buffer + cursor
            self.update(Markdown(display_content))
    
    def finalize(self):
        """Finalize the message (stop animation, remove cursor)."""
        self.is_streaming = False
        self.remove_class("thinking")
        
        if self.content_buffer:
            self.update(Markdown(self.content_buffer))


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
    
    MessageWidget.tool-call {
        background: #121212;
        border-left: solid #3a3a3a;
    }
    
    MessageWidget.tool-result {
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
            
        elif self.role == "tool_call":
            self.add_class("tool-call")
            text = Text()
            text.append("tool\n", style="#777777")
            text.append(self.message_content, style="#999999")
            self.update(text)
            
        elif self.role == "tool_result":
            self.add_class("tool-result")
            # Limit very long outputs
            content = self.message_content
            if len(content) > 5000:
                content = content[:5000] + "\n\n[output truncated]"
            
            text = Text()
            text.append("result\n", style="#777777")
            text.append(content, style="#999999")
            self.update(text)
            
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
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation."""
        message = MessageWidget(role, content)
        self.mount(message)
        # Auto-scroll to bottom
        self.scroll_end(animate=False)
    
    def show_loading(self, message: str = "loading"):
        """Show an animated loading indicator."""
        if self.loading_widget:
            self.loading_widget.remove()
        
        self.loading_widget = LoadingWidget(message)
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
        """Start showing thinking/reasoning."""
        if self.streaming_widget:
            self.thinking_content = ""
    
    def append_thinking(self, text: str):
        """Append to thinking content."""
        if self.streaming_widget:
            self.thinking_content += text
            self.streaming_widget.append_thinking(text)
            self.scroll_end(animate=False)
    
    def end_thinking(self):
        """End the thinking phase."""
        if self.streaming_widget and self.thinking_content:
            self.streaming_widget.end_thinking()
    
    def finalize_stream(self):
        """Finalize the current streaming message."""
        if self.streaming_widget:
            self.streaming_widget.finalize()
            self.streaming_widget = None
            self.thinking_content = ""
    
    def clear_messages(self):
        """Clear all messages."""
        self.streaming_widget = None
        self.thinking_content = ""
        self.loading_widget = None
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
