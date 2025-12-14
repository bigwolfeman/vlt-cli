import os
import tomllib
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

class ProjectConfig(BaseModel):
    name: str
    id: str
    description: Optional[str] = None

class VltConfig(BaseModel):
    project: ProjectConfig

def find_vlt_toml(start_path: Path = Path(".")) -> Optional[Path]:
    """Recursively search for vlt.toml in parent directories."""
    current = start_path.resolve()
    for _ in range(len(current.parts)):
        check_path = current / "vlt.toml"
        if check_path.exists():
            return check_path
        if current == current.parent: # Root reached
            break
        current = current.parent
    return None

def load_project_identity(start_path: Path = Path(".")) -> Optional[ProjectConfig]:
    """Load project identity from the nearest vlt.toml."""
    toml_path = find_vlt_toml(start_path)
    if not toml_path:
        return None
    
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        config = VltConfig(**data)
        return config.project
    except Exception as e:
        # Malformed TOML
        return None

def create_vlt_toml(path: Path, name: str, id: str, description: str = ""):
    """Create a vlt.toml file."""
    content = f"""[project]
name = "{name}"
id = "{id}"
description = "{description}"

[rag]
include = ["src/**/*.py", "docs/*.md"]
exclude = ["tests/", "legacy/"]
"""
    with open(path / "vlt.toml", "w") as f:
        f.write(content)
