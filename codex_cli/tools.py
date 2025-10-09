"""Tool definitions and implementations for agentic behavior."""

import os
import json
import subprocess
import aiofiles
from pathlib import Path
from typing import Any, Dict, List, Callable
from dataclasses import dataclass


@dataclass
class Tool:
    """Represents a tool that can be called by the agent."""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable


class ToolRegistry:
    """Registry for all available tools."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.tools: Dict[str, Tool] = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools."""
        self.register_tool(
            name="read_file",
            description="Read the contents of a file from the workspace",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The relative path to the file to read"
                    }
                },
                "required": ["file_path"]
            },
            function=self.read_file
        )
        
        self.register_tool(
            name="write_file",
            description="Write content to a file in the workspace. Creates directories if needed.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The relative path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["file_path", "content"]
            },
            function=self.write_file
        )
        
        self.register_tool(
            name="list_directory",
            description="List files and directories in a given path",
            parameters={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "The relative path to the directory to list (default: current directory)"
                    }
                },
                "required": []
            },
            function=self.list_directory
        )
        
        self.register_tool(
            name="execute_command",
            description="Execute a shell command in the workspace directory. Use with caution.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            },
            function=self.execute_command
        )
        
        self.register_tool(
            name="search_files",
            description="Search for files by name pattern in the workspace",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The glob pattern to search for (e.g., '*.py', 'src/**/*.js')"
                    }
                },
                "required": ["pattern"]
            },
            function=self.search_files
        )
        
        self.register_tool(
            name="delete_file",
            description="Delete a file from the workspace",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The relative path to the file to delete"
                    }
                },
                "required": ["file_path"]
            },
            function=self.delete_file
        )
    
    def register_tool(self, name: str, description: str, parameters: Dict[str, Any], function: Callable):
        """Register a new tool."""
        self.tools[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=function
        )
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas for OpenAI/Claude function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in self.tools.values()
        ]
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        if name not in self.tools:
            return f"Error: Tool '{name}' not found"
        
        try:
            tool = self.tools[name]
            result = await tool.function(**arguments)
            return result
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"
    
    async def read_file(self, file_path: str) -> str:
        """Read a file from the workspace."""
        try:
            full_path = self.workspace_path / file_path
            if not full_path.exists():
                return f"Error: File '{file_path}' not found"
            
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            return f"File: {file_path}\n\n{content}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    async def write_file(self, file_path: str, content: str) -> str:
        """Write content to a file."""
        try:
            full_path = self.workspace_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    async def list_directory(self, directory_path: str = ".") -> str:
        """List contents of a directory."""
        try:
            full_path = self.workspace_path / directory_path
            if not full_path.exists():
                return f"Error: Directory '{directory_path}' not found"
            
            items = []
            for item in sorted(full_path.iterdir()):
                rel_path = item.relative_to(self.workspace_path)
                item_type = "DIR" if item.is_dir() else "FILE"
                size = item.stat().st_size if item.is_file() else "-"
                items.append(f"{item_type:6} {size:>10} {rel_path}")
            
            return f"Directory: {directory_path}\n\n" + "\n".join(items)
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    async def execute_command(self, command: str) -> str:
        """Execute a shell command."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_path,
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
            return f"Error executing command: {str(e)}"
    
    async def search_files(self, pattern: str) -> str:
        """Search for files matching a pattern."""
        try:
            matches = list(self.workspace_path.glob(pattern))
            if not matches:
                return f"No files found matching pattern: {pattern}"
            
            results = []
            for match in sorted(matches):
                rel_path = match.relative_to(self.workspace_path)
                results.append(str(rel_path))
            
            return f"Found {len(results)} file(s) matching '{pattern}':\n\n" + "\n".join(results)
        except Exception as e:
            return f"Error searching files: {str(e)}"
    
    async def delete_file(self, file_path: str) -> str:
        """Delete a file."""
        try:
            full_path = self.workspace_path / file_path
            if not full_path.exists():
                return f"Error: File '{file_path}' not found"
            
            if full_path.is_dir():
                return f"Error: '{file_path}' is a directory. Use a file manager to delete directories."
            
            full_path.unlink()
            return f"Successfully deleted {file_path}"
        except Exception as e:
            return f"Error deleting file: {str(e)}"

