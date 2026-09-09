import os
from typing import Tuple, Optional
from openai import AsyncOpenAI
from .config import AppConfig

async def test_model(client: AsyncOpenAI, model: str) -> bool:
    """Test if a given model works on the provided client."""
    print(f"Testing model: {model}...")
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Ping. Reply only with 'pong'."}],
            max_tokens=10,
            timeout=10,
        )
        reply = response.choices[0].message.content.strip().lower()
        print(f"[{model}] Response: {reply}")
        return True
    except Exception as e:
        print(f"[{model}] Failed to respond: {e}")
        return False

async def get_working_client(config: AppConfig) -> Tuple[Optional[AsyncOpenAI], Optional[str]]:
    """Iterate through config and return the first working client and model."""
    for provider in config.providers:
        print(f"Checking provider: {provider.name} ({provider.type})")
        api_key = provider.api_key
        if api_key.startswith("ENV_"):
            env_var = api_key[4:]
            api_key = os.environ.get(env_var, "placeholder")
        
        client = AsyncOpenAI(
            base_url=provider.base_url,
            api_key=api_key,
        )
        
        for model in provider.models:
            if await test_model(client, model):
                print(f"✅ Selected provider '{provider.name}' with model '{model}'")
                return client, model
                
    print("❌ No working models found across all providers.")
    return None, None
