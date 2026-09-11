import json
from typing import List, Dict, Any, Callable
from openai import AsyncOpenAI

import time

class AsyncAgent:
    def __init__(self, client: AsyncOpenAI, model: str, system_prompt: str = "You are a helpful AI assistant. You can use tools to answer user questions.", provider_name: str = "unknown", prompt_builder_func: Callable = None, session_id: str = "default", stats_manager = None):
        self.client = client
        self.model = model
        self.provider_name = provider_name
        self.session_id = session_id
        self.stats_manager = stats_manager
        self.tools: List[Dict[str, Any]] = []
        self.tool_funcs: Dict[str, Callable] = {}
        self.base_system_prompt = system_prompt
        self.prompt_builder_func = prompt_builder_func
        self.history: List[Dict[str, Any]] = [{"role": "system", "content": self.base_system_prompt}]
        
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
        
    def _estimate_tokens(self, text: str) -> int:
        ascii_count = sum(1 for c in text if ord(c) < 128)
        non_ascii_count = len(text) - ascii_count
        return int((ascii_count / 4) + (non_ascii_count / 1.5))
        
    async def stream_run(self, prompt: str):
        self.history.append({"role": "user", "content": prompt})
        
        # Инъекция списка доступных инструментов через билдер контекста
        if self.history and self.history[0].get("role") == "system" and self.prompt_builder_func:
            self.history[0]["content"] = self.prompt_builder_func(self.base_system_prompt, self.tools)
        
        while True:
            # Расчет метрик токенов
            history_str = json.dumps(self.history, ensure_ascii=False)
            chars = len(history_str)
            tokens = self._estimate_tokens(history_str)
            yield {"type": "metrics", "chars": chars, "tokens": tokens}
            
            yield {"type": "info", "content": "Agent Thinking..."}
            
            start_time = time.time()
            
            stream_options = {"include_usage": True} if self.stats_manager else None
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    tools=self.tools if self.tools else None,
                    stream=True,
                    stream_options=stream_options,
                )
            except Exception as e:
                # If stream_options is not supported by this provider (e.g., some OpenAI compatible endpoints)
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    tools=self.tools if self.tools else None,
                    stream=True,
                )
                
            current_content = ""
            current_tool_calls = {}
            first_content_chunk = True
            
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            cache_hit = False

            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    
                    if delta.content:
                        if first_content_chunk:
                            yield {
                                "type": "message_start", 
                                "model": self.model, 
                                "provider": getattr(self, "provider_name", "unknown")
                            }
                            first_content_chunk = False
                            
                        current_content += delta.content
                        yield {"type": "message_chunk", "content": delta.content}
                        
                    if delta.tool_calls:
                        for tc_chunk in delta.tool_calls:
                            idx = tc_chunk.index
                            if idx not in current_tool_calls:
                                current_tool_calls[idx] = {
                                    "id": tc_chunk.id or f"call_{idx}_{int(time.time())}",
                                    "type": "function",
                                    "function": {
                                        "name": tc_chunk.function.name or "",
                                        "arguments": ""
                                    }
                                }
                            else:
                                if tc_chunk.function.name:
                                    current_tool_calls[idx]["function"]["name"] += tc_chunk.function.name
                                    
                            if tc_chunk.function.arguments:
                                current_tool_calls[idx]["function"]["arguments"] += tc_chunk.function.arguments

                # Process usage if provided in chunk (usually last chunk for OpenAI)
                if getattr(chunk, "usage", None):
                    prompt_tokens = chunk.usage.prompt_tokens or 0
                    completion_tokens = chunk.usage.completion_tokens or 0
                    total_tokens = chunk.usage.total_tokens or 0
                    
                    if getattr(chunk.usage, 'prompt_tokens_details', None) and getattr(chunk.usage.prompt_tokens_details, 'cached_tokens', 0) > 0:
                        cache_hit = True

            duration_ms = int((time.time() - start_time) * 1000)
            
            if self.stats_manager:
                self.stats_manager.record_stat(
                    session_id=self.session_id,
                    provider=getattr(self, "provider_name", "unknown"),
                    model=self.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    duration_ms=duration_ms,
                    cache_hit=cache_hit
                )
            
            tool_calls = []
            if current_tool_calls:
                for idx in sorted(current_tool_calls.keys()):
                    class MockToolCall:
                        def __init__(self, id, name, arguments):
                            self.id = id
                            class Function:
                                def __init__(self, n, a):
                                    self.name = n
                                    self.arguments = a
                            self.function = Function(name, arguments)
                    
                    tc_dict = current_tool_calls[idx]
                    tool_calls.append(MockToolCall(id=tc_dict["id"], name=tc_dict["function"]["name"], arguments=tc_dict["function"]["arguments"]))
                    
            is_fallback = False
            
            # Fallback for local models that output tool calls as JSON in content
            if not tool_calls and current_content:
                fallback_calls = []
                decoder = json.JSONDecoder()
                s = current_content
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

            # Convert msg to dict for appending to messages
            msg_dict = {"role": "assistant"}
            if current_content and not is_fallback:
                msg_dict["content"] = current_content
            else:
                msg_dict["content"] = None
                
            if tool_calls:
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
                
            self.history.append(msg_dict)
            
            # Always close the active bubble from this pass
            yield {"type": "finish"}
            
            if not tool_calls:
                break
                
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = tool_call.function.arguments
                    
                    # Fix the history to avoid 400 error on next API call
                    if "tool_calls" in msg_dict:
                        for tc in msg_dict["tool_calls"]:
                            if tc.get("id") == getattr(tool_call, "id", None):
                                tc["function"]["arguments"] = "{}"
                    
                yield {"type": "tool_call", "name": func_name, "args": args}
                
                if func_name in self.tool_funcs:
                    if not isinstance(args, dict):
                        result = "Error: Invalid JSON syntax in tool arguments. You must provide a valid JSON object."
                    else:
                        try:
                            func = self.tool_funcs[func_name]
                            import asyncio
                            if asyncio.iscoroutinefunction(func):
                                result = await func(**args)
                            else:
                                result = func(**args)
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
