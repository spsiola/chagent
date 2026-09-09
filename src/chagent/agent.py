import json
from typing import List, Dict, Any, Callable
from openai import AsyncOpenAI

class AsyncAgent:
    def __init__(self, client: AsyncOpenAI, model: str, system_prompt: str = "You are a helpful AI assistant. You can use tools to answer user questions.", provider_name: str = "unknown"):
        self.client = client
        self.model = model
        self.provider_name = provider_name
        self.tools: List[Dict[str, Any]] = []
        self.tool_funcs: Dict[str, Callable] = {}
        self.history: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        
    def register_tool(self, name: str, description: str, parameters: Dict[str, Any], func: Callable):
        """Register an async or sync Python skill as a tool."""
        self.tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        })
        self.tool_funcs[name] = func
        
    async def stream_run(self, prompt: str):
        self.history.append({"role": "user", "content": prompt})
        
        while True:
            yield {"type": "info", "content": "Agent Thinking..."}
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                tools=self.tools if self.tools else None,
            )
            
            msg = response.choices[0].message
            
            tool_calls = msg.tool_calls
            is_fallback = False
            
            # Fallback for local models that output tool calls as JSON in content
            if not tool_calls and msg.content:
                fallback_calls = []
                decoder = json.JSONDecoder()
                s = msg.content
                pos = 0
                while pos < len(s):
                    pos = s.find('{', pos)
                    if pos == -1:
                        break
                    try:
                        obj, new_pos = decoder.raw_decode(s, pos)
                        if isinstance(obj, dict) and "name" in obj and "arguments" in obj:
                            fallback_calls.append(obj)
                        pos = new_pos
                    except json.JSONDecodeError:
                        pos += 1
                        
                if fallback_calls:
                    tool_calls = []
                    for idx, parsed in enumerate(fallback_calls):
                        class MockToolCall:
                            def __init__(self, id, name, arguments):
                                self.id = id
                                class Function:
                                    def __init__(self, n, a):
                                        self.name = n
                                        self.arguments = a
                                self.function = Function(name, arguments)
                        
                        args = parsed["arguments"]
                        args_str = json.dumps(args) if isinstance(args, dict) else str(args)
                        tool_calls.append(MockToolCall(id=f"call_fallback_{idx}", name=parsed["name"], arguments=args_str))
                    
                    is_fallback = True

            if msg.content and not is_fallback:
                yield {
                    "type": "message", 
                    "role": "assistant", 
                    "content": msg.content,
                    "model": self.model,
                    "provider": getattr(self, "provider_name", "unknown")
                }

            # Convert msg to dict for appending to messages
            msg_dict = msg.model_dump(exclude_none=True)
            if is_fallback:
                # Synthesize tool_calls for the context history so the LLM doesn't get confused
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in tool_calls
                ]
                msg_dict["content"] = None
                
            self.history.append(msg_dict)
            
            if not tool_calls:
                yield {"type": "finish"}
                break
                
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = tool_call.function.arguments
                    
                yield {"type": "tool_call", "name": func_name, "args": args}
                
                if func_name in self.tool_funcs:
                    try:
                        func = self.tool_funcs[func_name]
                        import asyncio
                        if asyncio.iscoroutinefunction(func):
                            result = await func(**args) if isinstance(args, dict) else await func()
                        else:
                            result = func(**args) if isinstance(args, dict) else func()
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    result = f"Unknown tool: {func_name}"
                    
                yield {"type": "tool_result", "name": func_name, "content": str(result)}
                
                self.history.append({
                    "role": "tool",
                    "tool_call_id": getattr(tool_call, "id", "call_fallback"),
                    "name": func_name,
                    "content": str(result)
                })

    async def run(self, prompt: str):
        print(f"\n--- Agent starting task ---")
        print(f"Task: {prompt}")
        
        async for event in self.stream_run(prompt):
            if event["type"] == "info":
                print(f"\n[{event['content']}]")
            elif event["type"] == "message":
                print(f"\n🤖 Agent says: {event['content']}")
            elif event["type"] == "tool_call":
                print(f"🛠️ Executing tool: {event['name']}({event['args']})")
            elif event["type"] == "tool_result":
                print(f"📊 Tool result: {event['content']}")
                
        print("\n--- Agent finished task ---")
