from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"


def load_prompt_config(name: str, prompts_dir: Path | None = None) -> dict[str, Any]:
    """Load an agent/task prompt configuration from prompts/<name>.yaml."""
    target_dir = prompts_dir or PROMPTS_DIR
    path = target_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt configuration not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Prompt configuration must be a YAML mapping: {path}")

    for section in ("agent", "task"):
        if section not in data or not isinstance(data[section], dict):
            raise ValueError(f"Missing '{section}' section in {path}")

    for field in ("role", "goal", "backstory"):
        if not data["agent"].get(field):
            raise ValueError(f"Missing 'agent.{field}' in {path}")

    for field in ("description", "expected_output"):
        if not data["task"].get(field):
            raise ValueError(f"Missing 'task.{field}' in {path}")

    return data
