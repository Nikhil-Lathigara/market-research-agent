import json
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import usage_tracker


def test_record_agent_usage_with_provider_tokens(tmp_path):
    report_path = tmp_path / "usage_report.json"
    fake_usage = SimpleNamespace(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cached_prompt_tokens=0,
        reasoning_tokens=0,
        successful_requests=1,
    )
    fake_output = SimpleNamespace(token_usage=fake_usage)

    report = usage_tracker.record_agent_usage(
        agent_name="Research Agent",
        model_name="gemini/gemini-3.5-flash-lite",
        crew_output=fake_output,
        duration_seconds=12.34,
        report_path=report_path,
    )

    assert report_path.exists()
    entry = report["agents"]["Research Agent"]
    assert entry["usage_available"] is True
    assert entry["usage_source"] == "provider_reported"
    assert entry["prompt_tokens"] == 1000
    assert entry["completion_tokens"] == 500
    assert entry["total_tokens"] == 1500
    assert entry["cost_source"] == "estimated_from_configured_rates"
    # 1000/1M * 0.10 + 500/1M * 0.40 = 0.0001 + 0.0002 = 0.0003
    assert entry["estimated_cost_usd"] == 0.0003
    assert report["totals"]["total_tokens"] == 1500
    assert report["budget_exceeded"] is False


def test_record_agent_usage_handles_missing_metadata_gracefully(tmp_path):
    report_path = tmp_path / "usage_report.json"
    fake_output = SimpleNamespace(token_usage=None)

    report = usage_tracker.record_agent_usage(
        agent_name="Analyst Agent",
        model_name="gemini/gemini-3.5-flash-lite",
        crew_output=fake_output,
        duration_seconds=5.0,
        report_path=report_path,
    )

    entry = report["agents"]["Analyst Agent"]
    assert entry["usage_available"] is False
    assert entry["usage_source"] == "unavailable"
    assert entry["prompt_tokens"] is None
    assert entry["completion_tokens"] is None
    assert entry["total_tokens"] is None
    assert entry["estimated_cost_usd"] is None
    assert report["totals"]["agents_missing_usage"] == 1


def test_budget_threshold_warning_flag(monkeypatch, tmp_path):
    report_path = tmp_path / "usage_report.json"
    monkeypatch.setenv("PIPELINE_BUDGET_USD", "0.0001")

    fake_usage = SimpleNamespace(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cached_prompt_tokens=0,
        reasoning_tokens=0,
        successful_requests=1,
    )
    report = usage_tracker.record_agent_usage(
        agent_name="Strategy Agent",
        model_name="gemini/gemini-3.5-flash-lite",
        crew_output=SimpleNamespace(token_usage=fake_usage),
        duration_seconds=10.0,
        report_path=report_path,
    )

    assert report["budget_limit_usd"] == 0.0001
    assert report["budget_exceeded"] is True
