import os
import subprocess

def _validate_path(target_path: str, settings) -> str | None:
    """Validates if a path is safe to access. Returns error string if invalid, None if valid."""
    if not settings or not getattr(settings, 'safe_mode', False):
        return None
        
    abs_target = os.path.abspath(target_path)
    
    # Check roots
    allowed = False
    allowed_roots = getattr(settings, 'allowed_roots', ["./"])
    for root in allowed_roots:
        abs_root = os.path.abspath(root)
        if abs_target.startswith(abs_root):
            allowed = True
            break
            
    if not allowed:
        return f"Security Error: Path {target_path} is outside of allowed roots."
        
    return None

def read_file(path: str, settings=None) -> str:
    """Read contents of a file."""
    err = _validate_path(path, settings)
    if err: return err
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {path}: {e}"

def write_file(path: str, content: str, settings=None) -> str:
    """Write content to a file, overwriting existing content."""
    err = _validate_path(path, settings)
    if err: return err
    
    # Self-modification protection
    if settings and getattr(settings, 'safe_mode', False):
        if path.endswith(".py"):
            return "Security Error: Modifying .py files is forbidden in safe_mode to prevent self-modification. Disable safe_mode if you need to develop the agent itself."
            
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file {path}: {e}"

def list_directory(path: str, settings=None) -> str:
    """List contents of a directory."""
    err = _validate_path(path, settings)
    if err: return err
    
    try:
        items = os.listdir(path)
        return f"Directory {path} contains:\n" + "\n".join(items)
    except Exception as e:
        return f"Error listing directory {path}: {e}"

def run_command(command: str, settings=None) -> str:
    """Run a shell command and return its output."""
    if settings and getattr(settings, 'safe_mode', False):
        return "Security Error: Arbitrary command execution is disabled in safe_mode."
        
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output if output else "Command executed successfully (no output)."
    except Exception as e:
        return f"Error running command: {e}"

def register_native_tools(agent, settings):
    """Registers standard native tools with the agent, enforcing security settings."""
    agent.register_tool(
        name="read_file",
        description="Reads the contents of a file at the given path.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        },
        func=lambda path: read_file(path, settings)
    )
    
    agent.register_tool(
        name="write_file",
        description="Writes content to a file, creating directories if needed.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        },
        func=lambda path, content: write_file(path, content, settings)
    )

    agent.register_tool(
        name="list_directory",
        description="Lists the contents of a directory.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        },
        func=lambda path: list_directory(path, settings)
    )

    agent.register_tool(
        name="run_command",
        description="Runs a shell command and returns the output.",
        parameters={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"]
        },
        func=lambda command: run_command(command, settings)
    )
