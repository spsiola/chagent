import yaml
from pydantic import BaseModel, Field
from typing import List, Optional

class ProviderConfig(BaseModel):
    name: str
    type: str
    base_url: str
    api_key: str
    models: List[str]

class AppConfig(BaseModel):
    providers: List[ProviderConfig]

def load_config(path: str = "config.yaml") -> AppConfig:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)
