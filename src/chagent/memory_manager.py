import os
import json
from pydantic import BaseModel
from typing import Dict, Optional

MEMORY_DIR = "data/memory"
SYSTEM_PROMPTS_FILE = os.path.join(MEMORY_DIR, "system_prompts.json")
DEFAULTS_FILE = "init_memory/personality/defaults.json"

class SystemPrompts(BaseModel):
    default: str = ""
    models: Dict[str, str] = {}
    tool_rules: str = ""
    system_template: str = ""

class MemoryManager:
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.prompts = self._load_prompts()
        
    def _load_defaults(self) -> dict:
        defaults = {}
        if os.path.exists(DEFAULTS_FILE):
            try:
                with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
                    defaults = json.load(f)
            except Exception as e:
                print(f"Error loading defaults from {DEFAULTS_FILE}: {e}")
        return defaults

    def _load_prompts(self) -> SystemPrompts:
        defaults = self._load_defaults()
        
        if os.path.exists(SYSTEM_PROMPTS_FILE):
            try:
                with open(SYSTEM_PROMPTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # Заполняем пропущенные поля из defaults
                for key in ["default", "tool_rules", "system_template"]:
                    if key not in data and key in defaults:
                        data[key] = defaults[key]
                        
                return SystemPrompts(**data)
            except Exception as e:
                print(f"Error loading system prompts: {e}")
                
        # Возвращаем полностью дефолтный промпт
        return SystemPrompts(**defaults)
        
    def _save_prompts(self):
        with open(SYSTEM_PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.prompts.model_dump(), f, ensure_ascii=False, indent=2)

    def get_prompt_for_model(self, model_id: Optional[str] = None) -> str:
        """Возвращает промпт для конкретной модели (provider/model) или дефолтный."""
        if not model_id:
            return self.prompts.default
        return self.prompts.models.get(model_id, self.prompts.default)
        
    def update_default_prompt(self, new_prompt: str):
        self.prompts.default = new_prompt
        self._save_prompts()
        
    def update_model_prompt(self, model_id: str, new_prompt: str):
        self.prompts.models[model_id] = new_prompt
        self._save_prompts()
        
    def update_tool_rules(self, new_rules: str):
        self.prompts.tool_rules = new_rules
        self._save_prompts()
        
    def update_system_template(self, new_template: str):
        self.prompts.system_template = new_template
        self._save_prompts()
        
    def get_all_prompts(self) -> dict:
        return self.prompts.model_dump()
        
    def build_system_prompt(self, model_id: Optional[str], tools: list) -> str:
        role_prompt = self.get_prompt_for_model(model_id)
        
        if not tools:
            # Если инструментов нет, можно просто вернуть роль, или отрендерить без инструментов
            return role_prompt
            
        tools_list_str = "\\n".join([f"- {t['function']['name']}: {t['function']['description']}" for t in tools])
        
        template = self.prompts.system_template
        
        final_prompt = template.replace("{role_prompt}", role_prompt)
        final_prompt = final_prompt.replace("{tools_list}", tools_list_str)
        final_prompt = final_prompt.replace("{tool_rules}", self.prompts.tool_rules)
        
        return final_prompt
