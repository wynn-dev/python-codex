"""OpenRouter client wrapper with tool calling support."""

import json
from typing import List, Dict, Any, Optional, AsyncIterator
from openai import AsyncOpenAI
from .config import Config
from .tools import ToolRegistry


class Message:
    """Represents a chat message."""
    
    def __init__(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None, name: Optional[str] = None):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls or []
        self.name = name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format for API."""
        msg = {
            "role": self.role,
            "content": self.content
        }
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.name:
            msg["name"] = self.name
        return msg


class CodexClient:
    """Client for interacting with OpenRouter API with tool calling support."""
    
    def __init__(self, workspace_path):
        Config.validate()
        
        self.client = AsyncOpenAI(
            api_key=Config.OPENROUTER_API_KEY,
            base_url=Config.OPENROUTER_BASE_URL
        )
        
        self.model = Config.OPENROUTER_DEFAULT_MODEL
        self.tool_registry = ToolRegistry(workspace_path)
        self.conversation_history: List[Message] = []
        
        # System prompt for the assistant
        self.system_prompt = """You are Codex, an advanced AI coding assistant with access to powerful tools for file operations, code execution, and workspace management.

You can:
- Read and write files in the workspace
- Execute shell commands
- Search for files
- List directories
- Analyze and generate code
- Help with debugging and problem-solving

When the user asks you to perform tasks, use the appropriate tools to accomplish them. Always be helpful, precise, and explain what you're doing.

When writing code:
- Write clean, well-documented code
- Follow best practices
- Include error handling
- Add helpful comments

When using tools:
- Be explicit about what you're doing
- Explain the results
- Handle errors gracefully
"""
    
    async def send_message(self, user_message: str) -> AsyncIterator[tuple[str, Optional[Dict]]]:
        """
        Send a message and handle tool calls automatically.
        Yields tuples of (content_chunk, tool_info) where tool_info is present for tool calls.
        """
        # Add user message to history
        self.conversation_history.append(Message(role="user", content=user_message))
        
        # Prepare messages for API
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend([msg.to_dict() for msg in self.conversation_history])
        
        tools = self.tool_registry.get_tool_schemas()
        
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Call the API
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS,
                    extra_body={"route": Config.ROUTE_BY}
                )
                
                assistant_message = response.choices[0].message
                
                # Check if the model wants to use tools
                if assistant_message.tool_calls:
                    # Add assistant message with tool calls to history
                    tool_calls_data = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                    
                    self.conversation_history.append(
                        Message(
                            role="assistant",
                            content=assistant_message.content or "",
                            tool_calls=tool_calls_data
                        )
                    )
                    
                    # Execute each tool call
                    for tool_call in assistant_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Yield tool call information
                        yield "", {
                            "type": "tool_call",
                            "name": function_name,
                            "arguments": function_args,
                            "id": tool_call.id
                        }
                        
                        # Execute the tool
                        result = await self.tool_registry.execute_tool(function_name, function_args)
                        
                        # Yield tool result
                        yield "", {
                            "type": "tool_result",
                            "name": function_name,
                            "result": result,
                            "id": tool_call.id
                        }
                        
                        # Add tool result to conversation
                        self.conversation_history.append(
                            Message(
                                role="tool",
                                content=result,
                                name=function_name
                            )
                        )
                        
                        # Update messages for next iteration
                        messages.append({
                            "role": "assistant",
                            "content": assistant_message.content or "",
                            "tool_calls": tool_calls_data
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                            "name": function_name
                        })
                    
                    # Continue the loop to get the final response
                    continue
                else:
                    # No tool calls, return the response
                    content = assistant_message.content or ""
                    
                    # Add to history
                    self.conversation_history.append(
                        Message(role="assistant", content=content)
                    )
                    
                    # Yield the final response
                    yield content, None
                    break
                    
            except Exception as e:
                error_msg = f"Error communicating with API: {str(e)}"
                yield error_msg, None
                break
        
        if iteration >= max_iterations:
            yield "\n\n[Warning: Maximum tool call iterations reached]", None
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def get_history(self) -> List[Message]:
        """Get conversation history."""
        return self.conversation_history

