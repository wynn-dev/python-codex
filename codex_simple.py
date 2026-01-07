#!/usr/bin/env python3
"""Simplified Codex CLI - Single file, no classes, functional style."""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "openai/gpt-5.2")
MAX_TOKENS = 20000
TEMPERATURE = 0

# Global state
console = Console()
workspace_path = Path.cwd()
conversation_history = []

# System prompt
SYSTEM_PROMPT = """You are Codex, an advanced AI coding assistant with access to powerful tools for file operations, code execution, and workspace management. Default language is Python.

You can:
- Read and write files in the workspace
- Execute shell commands
- Search for files
- List directories
- Help with debugging and problem-solving

When the user asks you to write code, use the appropriate tools to accomplish them.
"""

# =============================================================================
# TOOLS - Simple async functions
# =============================================================================

async def read_file(file_path: str) -> str:
    """Read a file from the workspace."""
    try:
        full_path = workspace_path / file_path
        if not full_path.exists():
            return f"Error: File '{file_path}' not found"
        content = full_path.read_text(encoding='utf-8')
        return f"File: {file_path}\n\n{content}"
    except Exception as e:
        return f"Error reading file: {e}"


async def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    try:
        full_path = workspace_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


async def list_directory(directory_path: str = ".") -> str:
    """List contents of a directory."""
    try:
        full_path = workspace_path / directory_path
        if not full_path.exists():
            return f"Error: Directory '{directory_path}' not found"
        
        items = []
        for item in sorted(full_path.iterdir()):
            rel_path = item.relative_to(workspace_path)
            item_type = "DIR" if item.is_dir() else "FILE"
            size = item.stat().st_size if item.is_file() else "-"
            items.append(f"{item_type:6} {size:>10} {rel_path}")
        
        return f"Directory: {directory_path}\n\n" + "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {e}"


async def execute_command(command: str) -> str:
    """Execute a shell command."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        output.append(f"Exit code: {result.returncode}")
        
        return "\n\n".join(output)
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {e}"


async def search_files(pattern: str) -> str:
    """Search for files matching a pattern."""
    try:
        matches = list(workspace_path.glob(pattern))
        if not matches:
            return f"No files found matching pattern: {pattern}"
        
        results = [str(m.relative_to(workspace_path)) for m in sorted(matches)]
        return f"Found {len(results)} file(s) matching '{pattern}':\n\n" + "\n".join(results)
    except Exception as e:
        return f"Error searching files: {e}"


async def delete_file(file_path: str) -> str:
    """Delete a file."""
    try:
        full_path = workspace_path / file_path
        if not full_path.exists():
            return f"Error: File '{file_path}' not found"
        if full_path.is_dir():
            return f"Error: '{file_path}' is a directory"
        full_path.unlink()
        return f"Successfully deleted {file_path}"
    except Exception as e:
        return f"Error deleting file: {e}"


async def get_workspace_info() -> str:
    """Get information about the current workspace."""
    try:
        file_count = sum(1 for _ in workspace_path.rglob('*') if _.is_file())
        dir_count = sum(1 for _ in workspace_path.rglob('*') if _.is_dir())
        
        return f"""Workspace Information:
Path: {workspace_path}
Absolute: {workspace_path.resolve()}
Files: {file_count}
Directories: {dir_count}"""
    except Exception as e:
        return f"Error getting workspace info: {e}"


# Tool registry
TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "execute_command": execute_command,
    "search_files": search_files,
    "delete_file": delete_file,
    "get_workspace_info": get_workspace_info,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the workspace",
            "parameters": {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "The relative path to the file"}},
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the workspace. Creates directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The relative path to the file"},
                    "content": {"type": "string", "description": "The content to write"}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories in a given path",
            "parameters": {
                "type": "object",
                "properties": {"directory_path": {"type": "string", "description": "The relative path to the directory"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell command in the workspace directory",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "The shell command to execute"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files by name pattern in the workspace",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string", "description": "The glob pattern (e.g., '*.py')"}},
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file from the workspace",
            "parameters": {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "The relative path to the file"}},
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_workspace_info",
            "description": "Get information about the current workspace",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
]


# =============================================================================
# API CLIENT
# =============================================================================

def create_client():
    """Create the OpenAI client."""
    if not API_KEY:
        console.print("[red]Error: OPENROUTER_API_KEY not set[/red]")
        sys.exit(1)
    return AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)


async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name."""
    if name not in TOOLS:
        return f"Error: Tool '{name}' not found"
    try:
        return await TOOLS[name](**args)
    except Exception as e:
        return f"Error executing '{name}': {e}"


def format_tool_result(tool_name: str, result: str) -> None:
    """Display a tool result nicely."""
    # Truncate long results
    if len(result) > 2000:
        result = result[:2000] + "\n... (truncated)"
    
    # Syntax highlight for file reads
    if tool_name == "read_file" and result.startswith("File:"):
        parts = result.split("\n\n", 1)
        if len(parts) == 2:
            file_path = parts[0].replace("File: ", "")
            content = parts[1]
            ext = Path(file_path).suffix
            lang_map = {".py": "python", ".js": "javascript", ".ts": "typescript", 
                       ".json": "json", ".md": "markdown", ".html": "html"}
            lang = lang_map.get(ext, "text")
            console.print(f"[dim]{file_path}[/dim]")
            console.print(Syntax(content[:1500], lang, theme="monokai", line_numbers=False))
            return
    
    console.print(Text(result, style="dim"))


async def send_message(user_message: str) -> None:
    """Send a message and handle the streaming response with tool calls."""
    global conversation_history
    
    client = create_client()
    conversation_history.append({"role": "user", "content": user_message})
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history
    
    for iteration in range(10):  # Max 10 tool call iterations
        try:
            stream = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=True,
            )
            
            accumulated_content = ""
            accumulated_reasoning = ""
            tool_calls_dict = {}
            reasoning_active = False
            
            # Stream the response
            with Live(console=console, refresh_per_second=15, transient=True) as live:
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    # Handle reasoning (thinking)
                    if hasattr(delta, 'reasoning') and delta.reasoning:
                        if not reasoning_active:
                            reasoning_active = True
                        accumulated_reasoning += delta.reasoning
                        live.update(Text(f"thinking... ({len(accumulated_reasoning)} chars)", style="dim italic"))
                    
                    # Handle content
                    if delta.content:
                        if reasoning_active:
                            reasoning_active = False
                            if accumulated_reasoning:
                                console.print(f"\n[dim italic]thought for a moment[/dim italic]\n")
                        
                        accumulated_content += delta.content
                        live.update(Markdown(accumulated_content + "▌"))
                    
                    # Handle tool calls
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_dict:
                                tool_calls_dict[idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                            if tc.id:
                                tool_calls_dict[idx]["id"] = tc.id
                            if tc.function.name:
                                tool_calls_dict[idx]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_dict[idx]["function"]["arguments"] += tc.function.arguments
            
            # Display final content if any
            if accumulated_content:
                console.print(Markdown(accumulated_content))
            
            # Process tool calls if any
            if tool_calls_dict:
                tool_calls_list = [tool_calls_dict[i] for i in sorted(tool_calls_dict.keys())]
                
                # Add assistant message with tool calls
                conversation_history.append({
                    "role": "assistant",
                    "content": accumulated_content,
                    "tool_calls": tool_calls_list
                })
                
                # Execute each tool
                for tc in tool_calls_list:
                    func_name = tc["function"]["name"]
                    func_args = json.loads(tc["function"]["arguments"])
                    
                    # Show tool execution
                    args_display = ", ".join(f"{k}={repr(v)[:50]}" for k, v in func_args.items())
                    console.print(f"\n[bold cyan]> {func_name}[/bold cyan]({args_display})")
                    
                    # Execute
                    result = await execute_tool(func_name, func_args)
                    format_tool_result(func_name, result)
                    
                    # Add to conversation
                    conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                        "name": func_name
                    })
                    
                    # Update messages for next iteration
                    messages.append({
                        "role": "assistant",
                        "content": accumulated_content,
                        "tool_calls": tool_calls_list
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                        "name": func_name
                    })
                
                console.print()
                continue  # Continue to get model's response after tool execution
            
            else:
                # No tool calls - final response
                if accumulated_content:
                    conversation_history.append({"role": "assistant", "content": accumulated_content})
                break
        
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            break


# =============================================================================
# MAIN LOOP
# =============================================================================

def show_welcome():
    """Show welcome message."""
    console.print()
    console.print("[bold]codex[/bold] — ai coding assistant", style="white")
    console.print(f"workspace: [dim]{workspace_path}[/dim]")
    console.print()
    console.print("[dim]commands: /help, /clear, /info, /quit[/dim]")
    console.print()


def show_help():
    """Show help message."""
    console.print("""
[bold]codex — help[/bold]

[dim]commands[/dim]
  /help   — show this help
  /clear  — clear conversation history
  /info   — show workspace info
  /quit   — exit

[dim]available tools[/dim]
  read_file        — read file contents
  write_file       — create or update files
  delete_file      — remove files
  list_directory   — list directory contents
  search_files     — find files by pattern
  execute_command  — run shell commands
  get_workspace_info — workspace statistics
""")


def show_info():
    """Show workspace info."""
    try:
        file_count = sum(1 for _ in workspace_path.rglob('*') if _.is_file())
        dir_count = sum(1 for _ in workspace_path.rglob('*') if _.is_dir())
    except:
        file_count = dir_count = "?"
    
    console.print(f"""
[bold]workspace info[/bold]

path:        {workspace_path}
absolute:    {workspace_path.resolve()}
files:       {file_count}
directories: {dir_count}
""")


async def main():
    """Main entry point."""
    global workspace_path
    
    # Handle command line argument for workspace path
    if len(sys.argv) > 1:
        arg_path = Path(sys.argv[1]).resolve()
        if arg_path.is_dir():
            workspace_path = arg_path
        else:
            console.print(f"[yellow]Warning: '{sys.argv[1]}' is not a directory, using current directory[/yellow]")
    
    show_welcome()
    
    while True:
        try:
            # Get user input
            console.print("[bold green]you[/bold green]")
            user_input = input("› ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() == "/quit" or user_input.lower() == "/exit":
                console.print("[dim]goodbye![/dim]")
                break
            
            elif user_input.lower() == "/help":
                show_help()
                continue
            
            elif user_input.lower() == "/clear":
                conversation_history.clear()
                console.print("[dim]history cleared[/dim]\n")
                continue
            
            elif user_input.lower() == "/info":
                show_info()
                continue
            
            # Send message to AI
            console.print()
            console.print("[bold blue]codex[/bold blue]")
            await send_message(user_input)
            console.print()
        
        except KeyboardInterrupt:
            console.print("\n[dim]goodbye![/dim]")
            break
        
        except EOFError:
            break


if __name__ == "__main__":
    asyncio.run(main())

