"""OpenRouter client wrapper with tool calling support and streaming."""

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
        self.system_prompt = """You are Codex, an advanced AI coding assistant with access to powerful tools for file operations, code execution, and workspace management. Default language is Python.

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
        Send a message and handle tool calls automatically with streaming.
        Yields tuples of (content_chunk, info_dict) where info_dict contains:
        - type: "reasoning", "content", "tool_call", "tool_result", "thinking_start", "thinking_end"
        - content: the actual content
        - other metadata as needed
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
            
            # Call the API with streaming
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS,
                    extra_body={"route": Config.ROUTE_BY},
                    stream=True,
                    stream_options={"include_usage": True}
                )
                
                # Accumulate the response
                accumulated_content = ""
                accumulated_reasoning = ""
                tool_calls_dict = {}
                current_tool_call_id = None
                reasoning_active = False
                
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    # Handle reasoning tokens (extended thinking)
                    if hasattr(delta, 'reasoning') and delta.reasoning:
                        if not reasoning_active:
                            reasoning_active = True
                            yield "", {"type": "thinking_start"}
                        
                        accumulated_reasoning += delta.reasoning
                        yield delta.reasoning, {"type": "reasoning", "partial": True}
                    
                    # Handle regular content
                    if delta.content:
                        if reasoning_active:
                            reasoning_active = False
                            yield "", {"type": "thinking_end"}
                        
                        accumulated_content += delta.content
                        yield delta.content, {"type": "content", "partial": True}
                    
                    # Handle tool calls
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            
                            if idx not in tool_calls_dict:
                                tool_calls_dict[idx] = {
                                    "id": tc_delta.id or "",
                                    "type": "function",
                                    "function": {
                                        "name": tc_delta.function.name or "",
                                        "arguments": ""
                                    }
                                }
                            
                            if tc_delta.id:
                                tool_calls_dict[idx]["id"] = tc_delta.id
                            
                            if tc_delta.function.name:
                                tool_calls_dict[idx]["function"]["name"] = tc_delta.function.name
                            
                            if tc_delta.function.arguments:
                                tool_calls_dict[idx]["function"]["arguments"] += tc_delta.function.arguments
                
                # End reasoning if still active
                if reasoning_active:
                    yield "", {"type": "thinking_end"}
                
                # Process tool calls if any
                if tool_calls_dict:
                    tool_calls_list = [tool_calls_dict[i] for i in sorted(tool_calls_dict.keys())]
                    
                    # Add assistant message with tool calls to history
                    self.conversation_history.append(
                        Message(
                            role="assistant",
                            content=accumulated_content,
                            tool_calls=tool_calls_list
                        )
                    )
                    
                    # Execute each tool call
                    for tool_call in tool_calls_list:
                        function_name = tool_call["function"]["name"]
                        function_args = json.loads(tool_call["function"]["arguments"])
                        
                        # Yield tool call information
                        yield "", {
                            "type": "tool_call",
                            "name": function_name,
                            "arguments": function_args,
                            "id": tool_call["id"]
                        }
                        
                        # Execute the tool
                        result = await self.tool_registry.execute_tool(function_name, function_args)
                        
                        # Yield tool result
                        yield "", {
                            "type": "tool_result",
                            "name": function_name,
                            "result": result,
                            "id": tool_call["id"]
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
                            "content": accumulated_content,
                            "tool_calls": tool_calls_list
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                            "name": function_name
                        })
                    
                    # Continue the loop to get the final response
                    continue
                else:
                    # No tool calls, this is the final response
                    if accumulated_content:
                        # Add to history
                        self.conversation_history.append(
                            Message(role="assistant", content=accumulated_content)
                        )
                    
                    # Signal completion
                    yield "", {"type": "complete"}
                    break
                    
            except Exception as e:
                error_msg = f"Error communicating with API: {str(e)}"
                yield error_msg, {"type": "error"}
                break
        
        if iteration >= max_iterations:
            yield "\n\n[Warning: Maximum tool call iterations reached]", {"type": "warning"}
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def get_history(self) -> List[Message]:
        """Get conversation history."""
        return self.conversation_history
