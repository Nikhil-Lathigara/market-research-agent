import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import run_pipeline


def _patch_pipeline_dirs(monkeypatch, tmp_path: Path):
    output_dir = tmp_path / "outputs"
    log_dir = tmp_path / "logs"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    script_file = tmp_path / "dummy_stage.py"
    script_file.write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(run_pipeline, "BASE_DIR", tmp_path)
    monkeypatch.setattr(run_pipeline, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(run_pipeline, "LOG_DIR", log_dir)
    monkeypatch.setattr(run_pipeline, "LOG_FILE", log_dir / "pipeline.log")
    return output_dir


def test_run_stage_retries_and_succeeds_with_exponential_backoff(monkeypatch, tmp_path):
    output_dir = _patch_pipeline_dirs(monkeypatch, tmp_path)
    stage = {"name": "Dummy Stage", "script": "dummy_stage.py", "output": "dummy.json"}
    sleep_calls = []
    attempts = {"count": 0}

    def fake_run(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return SimpleNamespace(returncode=1)
        (output_dir / "dummy.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_run)
    monkeypatch.setattr(run_pipeline.time, "sleep", lambda d: sleep_calls.append(d))

    duration = run_pipeline.run_stage(stage, max_attempts=3, base_delay=2)

    assert attempts["count"] == 2
    assert sleep_calls == [2]
    assert duration >= 0


def test_run_stage_fails_after_exhausting_retries(monkeypatch, tmp_path):
    _patch_pipeline_dirs(monkeypatch, tmp_path)
    stage = {"name": "Dummy Stage", "script": "dummy_stage.py", "output": "dummy.json"}
    sleep_calls = []
    attempts = {"count": 0}

    def fake_run(*args, **kwargs):
        attempts["count"] += 1
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_run)
    monkeypatch.setattr(run_pipeline.time, "sleep", lambda d: sleep_calls.append(d))

    with pytest.raises(RuntimeError, match="failed after 3 attempt"):
        run_pipeline.run_stage(stage, max_attempts=3, base_delay=2)

    assert attempts["count"] == 3
    assert sleep_calls == [2, 4]


def test_run_stage_does_not_retry_missing_script(monkeypatch, tmp_path):
    _patch_pipeline_dirs(monkeypatch, tmp_path)
    stage = {"name": "Missing Stage", "script": "does_not_exist.py", "output": "dummy.json"}

    with pytest.raises(FileNotFoundError):
        run_pipeline.run_stage(stage, max_attempts=3, base_delay=2)


def test_validate_stage_output_detects_missing_output(monkeypatch, tmp_path):
    _patch_pipeline_dirs(monkeypatch, tmp_path)
    stage = {"name": "Dummy Stage", "script": "dummy_stage.py", "output": "missing.json"}

    with pytest.raises(FileNotFoundError, match="Expected output not found"):
        run_pipeline.validate_stage_output(stage, time.time())


def test_validate_stage_output_detects_stale_output(monkeypatch, tmp_path):
    output_dir = _patch_pipeline_dirs(monkeypatch, tmp_path)
    out_file = output_dir / "stale.json"
    out_file.write_text(json.dumps({"old": True}), encoding="utf-8")
    old_time = time.time() - 60
    os.utime(out_file, (old_time, old_time))

    stage = {"name": "Dummy Stage", "script": "dummy_stage.py", "output": "stale.json"}
    with pytest.raises(RuntimeError, match="did not produce a fresh output"):
        run_pipeline.validate_stage_output(stage, time.time())


def test_validate_stage_output_detects_empty_and_invalid_json(monkeypatch, tmp_path):
    output_dir = _patch_pipeline_dirs(monkeypatch, tmp_path)
    empty_file = output_dir / "empty.json"
    empty_file.write_text("", encoding="utf-8")
    stage_empty = {"name": "Dummy Stage", "script": "dummy_stage.py", "output": "empty.json"}

    with pytest.raises(ValueError, match="empty output"):
        run_pipeline.validate_stage_output(stage_empty, time.time() - 5)

    bad_file = output_dir / "bad.json"
    bad_file.write_text("{not valid json", encoding="utf-8")
    stage_bad = {"name": "Dummy Stage", "script": "dummy_stage.py", "output": "bad.json"}

    with pytest.raises(ValueError, match="invalid JSON"):
        run_pipeline.validate_stage_output(stage_bad, time.time() - 5)
