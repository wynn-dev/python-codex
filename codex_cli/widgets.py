"""Custom Textual widgets for Codex CLI."""

from pathlib import Path
from textual.widgets import Static
from textual.containers import Container, VerticalScroll
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.console import Group


class MessageWidget(Static):
    """Widget for displaying a single message."""
    
    DEFAULT_CSS = """
    MessageWidget {
        margin: 1 2;
        padding: 1 2;
    }
    
    MessageWidget.user-message {
        background: $primary-darken-2;
        border: tall $primary;
    }
    
    MessageWidget.assistant-message {
        background: $surface;
        border: tall $accent;
    }
    
    MessageWidget.tool-call {
        background: $warning-darken-3;
        border: tall $warning;
    }
    
    MessageWidget.tool-result {
        background: $success-darken-3;
        border: tall $success;
    }
    
    MessageWidget.error-message {
        background: $error-darken-3;
        border: tall $error;
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
            self.update(Panel(
                Markdown(self.message_content),
                title="[bold cyan]You[/bold cyan]",
                border_style="cyan"
            ))
        elif self.role == "assistant":
            self.add_class("assistant-message")
            self.update(Panel(
                Markdown(self.message_content),
                title="[bold green]Codex[/bold green]",
                border_style="green"
            ))
        elif self.role == "tool_call":
            self.add_class("tool-call")
            self.update(Panel(
                Text(self.message_content, style="yellow"),
                title="[bold yellow]🔧 Tool Call[/bold yellow]",
                border_style="yellow"
            ))
        elif self.role == "tool_result":
            self.add_class("tool-result")
            # Try to detect if it's code and apply syntax highlighting
            content = self.message_content
            if len(content) < 5000:  # Don't syntax highlight very long outputs
                try:
                    self.update(Panel(
                        Text(content),
                        title="[bold blue]📊 Tool Result[/bold blue]",
                        border_style="blue"
                    ))
                except:
                    self.update(Panel(
                        Text(content),
                        title="[bold blue]📊 Tool Result[/bold blue]",
                        border_style="blue"
                    ))
            else:
                self.update(Panel(
                    Text(content[:5000] + "\n\n... [output truncated] ..."),
                    title="[bold blue]📊 Tool Result[/bold blue]",
                    border_style="blue"
                ))
        elif self.role == "error":
            self.add_class("error-message")
            self.update(Panel(
                Text(self.message_content, style="bold red"),
                title="[bold red]❌ Error[/bold red]",
                border_style="red"
            ))


class ConversationView(VerticalScroll):
    """Container for displaying the conversation."""
    
    DEFAULT_CSS = """
    ConversationView {
        background: $panel;
        height: 1fr;
        border: solid $primary;
    }
    """
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation."""
        message = MessageWidget(role, content)
        self.mount(message)
        # Auto-scroll to bottom
        self.scroll_end(animate=False)
    
    def clear_messages(self):
        """Clear all messages."""
        self.remove_children()


class StatusBar(Static):
    """Status bar widget."""
    
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """
    
    def __init__(self, workspace_path: Path = None, **kwargs):
        super().__init__("", **kwargs)
        self.model_name = "claude-3.5-sonnet"
        self.workspace_path = workspace_path
        self.update_status()
    
    def update_status(self, message: str = "Ready"):
        """Update the status bar."""
        status_text = Text()
        status_text.append("Codex CLI", style="bold white")
        status_text.append(" | ", style="dim white")
        status_text.append(f"Model: {self.model_name}", style="cyan")
        if self.workspace_path:
            status_text.append(" | ", style="dim white")
            status_text.append(f"📁 {self.workspace_path.name}", style="yellow")
        status_text.append(" | ", style="dim white")
        status_text.append(message, style="green")
        self.update(status_text)
    
    def set_thinking(self):
        """Set status to thinking."""
        self.update_status("🤔 Thinking...")
    
    def set_ready(self):
        """Set status to ready."""
        self.update_status("Ready")
    
    def set_error(self, error: str):
        """Set status to error."""
        status_text = Text()
        status_text.append("Codex CLI", style="bold white")
        status_text.append(" | ", style="dim white")
        status_text.append(f"Error: {error}", style="bold red")
        self.update(status_text)
