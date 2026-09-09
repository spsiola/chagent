import os
from typing import Tuple, Optional, Callable
from openai import AsyncOpenAI
from .config import AppConfig

async def default_log(msg: str):
    print(msg)

async def test_model(client: AsyncOpenAI, model: str, log_callback: Callable = default_log) -> bool:
    """Test if a given model works on the provided client."""
    await log_callback(f"Harness: Testing model: {model}...")
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Ping. Reply only with 'pong'."}],
            max_tokens=10,
            timeout=10,
        )
        reply = response.choices[0].message.content.strip().lower()
        await log_callback(f"Harness: [{model}] Response: {reply}")
        return True
    except Exception as e:
        await log_callback(f"Harness: [{model}] Failed to respond: {e}")
        return False

async def get_working_client(config: AppConfig, log_callback: Callable = default_log) -> Tuple[Optional[AsyncOpenAI], Optional[str], Optional[str]]:
    """Iterate through config and return the first working client, model, and provider_name."""
    for provider in config.providers:
        await log_callback(f"Harness: Checking provider: {provider.name} ({provider.type})")
        api_key = provider.api_key
        if api_key.startswith("ENV_"):
            env_var = api_key[4:]
            api_key = os.environ.get(env_var, "placeholder")
        
        client = AsyncOpenAI(
            base_url=provider.base_url,
            api_key=api_key,
        )
        
        for model in provider.models:
            if await test_model(client, model, log_callback):
                await log_callback(f"Harness: ✅ Selected provider '{provider.name}' with model '{model}'")
                return client, model, provider.name
                
    await log_callback("Harness: ❌ No working models found across all providers.")
    return None, None, None
