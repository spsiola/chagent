import os
import asyncio

def parse_skill_md(file_path: str):
    """
    Парсит SKILL.md и извлекает name и description из YAML-frontmatter.
    Возвращает dict с name, description и content.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        if not lines or not lines[0].strip().startswith("---"):
            return None
            
        yaml_end = -1
        for i in range(1, len(lines)):
            if lines[i].strip().startswith("---"):
                yaml_end = i
                break
                
        if yaml_end == -1:
            return None
            
        name = None
        description = None
        
        # Простой парсинг yaml (без pyyaml)
        for i in range(1, yaml_end):
            line = lines[i].strip()
            if line.startswith("name:"):
                name = line[5:].strip().strip("'\"")
            elif line.startswith("description:"):
                description = line[12:].strip().strip(">-\n\r'\"")
                # Если описание продолжается на следующих строках (multiline)
                if not description:
                    desc_lines = []
                    j = i + 1
                    while j < yaml_end and not ":" in lines[j]:
                        desc_lines.append(lines[j].strip())
                        j += 1
                    description = " ".join(desc_lines)
                    
        content = "".join(lines[yaml_end+1:]).strip()
        
        if not name or not description:
            return None
            
        return {
            "name": name,
            "description": description,
            "content": content
        }
    except Exception as e:
        print(f"Ошибка при чтении {file_path}: {e}")
        return None

async def _default_logger(msg: str) -> None:
    print(msg)

async def load_skills(agent, base_dirs=["data/skills"], log_callback=_default_logger):
    """
    Асинхронно загружает скилы из переданных директорий и регистрирует их в агенте.
    """
    loaded_count = 0
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            continue
            
        # Ищем все SKILL.md в поддиректориях
        for root_dir, _, files in os.walk(base_dir):
            if "SKILL.md" in files:
                skill_path = os.path.join(root_dir, "SKILL.md")
                skill_data = parse_skill_md(skill_path)
                
                if skill_data:
                    name = skill_data["name"]
                    description = skill_data["description"]
                    content = skill_data["content"]
                    
                    # Захватываем content в замыкании
                    def make_tool(content_text):
                        async def activate_skill(**kwargs):
                            return f"Instructions loaded. Follow these instructions strictly:\\n\\n{content_text}"
                        return activate_skill
                    
                    # Имя тулза, чтобы не конфликтовать
                    tool_name = f"read_skill_{name.replace('-', '_')}"
                    
                    agent.register_tool(
                        name=tool_name,
                        description=f"Read instructions for skill: {name}. {description}",
                        parameters={
                            "type": "object",
                            "properties": {},
                            "required": []
                        },
                        func=make_tool(content)
                    )
                    loaded_count += 1
                    msg = f"  ✅ Загружен скилл: {name} из {skill_path}"
                    if log_callback:
                        if asyncio.iscoroutinefunction(log_callback):
                            await log_callback(msg)
                        else:
                            log_callback(msg)
                        
    return loaded_count
