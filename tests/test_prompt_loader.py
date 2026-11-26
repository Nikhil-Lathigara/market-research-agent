import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.prompt_loader import load_prompt_config


@pytest.mark.parametrize(
    ("name", "expected_placeholder"),
    [
        ("research", "{market_brief}"),
        ("analyst", "{research_data}"),
        ("strategy", "{input_data}"),
        ("head_planner", "{pipeline_data}"),
    ],
)
def test_load_prompt_config_validates_all_agents(name, expected_placeholder):
    cfg = load_prompt_config(name)
    assert cfg["agent"]["role"]
    assert cfg["agent"]["goal"]
    assert cfg["agent"]["backstory"]
    assert expected_placeholder in cfg["task"]["description"]
    assert cfg["task"]["expected_output"]


def test_load_prompt_config_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_prompt_config("nonexistent", prompts_dir=tmp_path)
