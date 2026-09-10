import os
import subprocess

def read_file(path: str) -> str:
    """Read contents of a file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {path}: {e}"

def write_file(path: str, content: str) -> str:
    """Write content to a file, overwriting existing content."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file {path}: {e}"

def list_directory(path: str) -> str:
    """List contents of a directory."""
    try:
        items = os.listdir(path)
        return f"Directory {path} contains:\n" + "\n".join(items)
    except Exception as e:
        return f"Error listing directory {path}: {e}"

def run_command(command: str) -> str:
    """Run a shell command and return its output."""
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

def register_native_tools(agent):
    """Registers standard native tools with the agent."""
    agent.register_tool(
        name="read_file",
        description="Reads the contents of a file at the given path.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        },
        func=read_file
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
        func=write_file
    )

    agent.register_tool(
        name="list_directory",
        description="Lists the contents of a directory.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        },
        func=list_directory
    )

    agent.register_tool(
        name="run_command",
        description="Runs a shell command and returns the output.",
        parameters={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"]
        },
        func=run_command
    )
