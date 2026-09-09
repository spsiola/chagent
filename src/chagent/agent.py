import json
from typing import List, Dict, Any, Callable
from openai import AsyncOpenAI

class AsyncAgent:
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model
        self.tools: List[Dict[str, Any]] = []
        self.tool_funcs: Dict[str, Callable] = {}
        
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
        
    async def run(self, prompt: str):
        print(f"\\n--- Agent starting task ---")
        print(f"Task: {prompt}")
        
        messages = [{"role": "user", "content": prompt}]
        
        while True:
            print("\\n[Agent Thinking...]")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools if self.tools else None,
            )
            
            msg = response.choices[0].message
            
            if msg.content:
                print(f"\\n🤖 Agent says: {msg.content}")
            
            tool_calls = msg.tool_calls
            
            # Fallback for local models that output tool calls as JSON in content
            if not tool_calls and msg.content:
                try:
                    parsed = json.loads(msg.content)
                    if isinstance(parsed, dict) and "name" in parsed and "arguments" in parsed:
                        print(f"⚠️ Recovered tool call from content: {parsed['name']}")
                        class MockToolCall:
                            def __init__(self, id, name, arguments):
                                self.id = id
                                class Function:
                                    def __init__(self, n, a):
                                        self.name = n
                                        self.arguments = a
                                self.function = Function(name, arguments)
                        tool_calls = [MockToolCall(id="call_fallback", name=parsed["name"], arguments=json.dumps(parsed["arguments"]))]
                except json.JSONDecodeError:
                    pass

            # Convert msg to dict for appending to messages
            # AsyncOpenAI v1 returns pydantic objects. Let's safely convert it
            msg_dict = msg.model_dump(exclude_none=True)
            messages.append(msg_dict)
            
            if not tool_calls:
                break
                
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = tool_call.function.arguments
                    
                print(f"🛠️ Executing tool: {func_name}({args})")
                
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
                    
                print(f"📊 Tool result: {result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": getattr(tool_call, "id", "call_fallback"),
                    "name": func_name,
                    "content": str(result)
                })
        
        print("\\n--- Agent finished task ---")
