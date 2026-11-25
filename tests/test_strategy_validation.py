
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from validate_strategy import validate_strategy_data


def sample_research():
    return {
        "evidence": [
            {"evidence_id": "E001"},
            {"evidence_id": "E002"},
        ]
    }


def sample_strategy():
    timestamp = "2026-11-22T10:00:00"

    return {
        "ideal_customer_profiles": [],
        "positioning": {},
        "messaging_framework": {},
        "channel_strategy": {},
        "swot_analysis": {
            "strengths": ["Strong product"],
            "weaknesses": ["Low awareness"],
            "opportunities": ["Growing demand"],
            "threats": ["Competition"],
        },
        "marketing_mix_7p": {
            "product": {},
            "price": {},
            "place": {},
            "promotion": {},
            "people": {},
            "process": {},
            "physical_evidence": {},
        },
        "pricing_strategy": {},
        "launch_plan": [
            {"phase": f"Phase {i}", "activities": ["Activity"]}
            for i in range(1, 5)
        ],
        "measurement_framework": [
            {"funnel_stage": stage}
            for stage in [
                "awareness",
                "acquisition",
                "activation",
                "engagement",
                "conversion",
                "retention",
            ]
        ],
        "risks_and_mitigations": [],
        "experiments": [],
        "evidence_limitations": [],
        "evidence_ids": ["E001"],
        "generated_at": timestamp,
        "run_metadata": {
            "generated_at": timestamp,
            "model": "test-model",
        },
    }


def test_valid_strategy():
    result = validate_strategy_data(sample_strategy(), sample_research())

    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["invalid_evidence_ids"] == []


def test_missing_required_section():
    strategy = sample_strategy()
    del strategy["positioning"]

    result = validate_strategy_data(strategy, sample_research())

    assert "Missing section: positioning" in result["errors"]


def test_empty_swot_category():
    strategy = sample_strategy()
    strategy["swot_analysis"]["strengths"] = []

    result = validate_strategy_data(strategy, sample_research())

    assert any("strengths" in error for error in result["errors"])


def test_missing_7p_element():
    strategy = sample_strategy()
    del strategy["marketing_mix_7p"]["promotion"]

    result = validate_strategy_data(strategy, sample_research())

    assert any("promotion" in error for error in result["errors"])


def test_insufficient_launch_phases():
    strategy = sample_strategy()
    strategy["launch_plan"] = strategy["launch_plan"][:2]

    result = validate_strategy_data(strategy, sample_research())

    assert any("four phases" in error for error in result["errors"])


def test_missing_kpi_stage():
    strategy = sample_strategy()
    strategy["measurement_framework"] = [
        item
        for item in strategy["measurement_framework"]
        if item["funnel_stage"] != "retention"
    ]

    result = validate_strategy_data(strategy, sample_research())

    assert any("retention" in error for error in result["errors"])


def test_invalid_evidence_reference():
    strategy = sample_strategy()
    strategy["evidence_ids"] = ["E999"]

    result = validate_strategy_data(strategy, sample_research())

    assert result["invalid_evidence_ids"] == ["E999"]


def test_missing_metadata_generates_warning():
    strategy = sample_strategy()
    strategy["run_metadata"] = {}

    result = validate_strategy_data(strategy, sample_research())

    assert result["errors"] == []
    assert len(result["warnings"]) >= 1


def test_invalid_launch_phase_structure():
    strategy = sample_strategy()
    strategy["launch_plan"][0] = "Invalid phase"

    result = validate_strategy_data(strategy, sample_research())

    assert any("must be an object" in error for error in result["errors"])
