
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from validate_analysis import validate_analysis_data


def sample_report():
    return {
        "competitor_comparison": [{"name": "Example"}],
        "pricing_matrix": [{"competitor": "Example"}],
        "swot_analysis": {},
        "marketing_mix_4p": {},
        "marketing_mix_7p": {},
        "market_opportunities": [{"opportunity": "Example"}],
        "research_gaps": [],
        "limitations": [],
    }


def sample_research():
    return {
        "evidence": [
            {"evidence_id": "E001"},
            {"evidence_id": "E002"},
        ]
    }


def test_valid_analysis_data():
    result = validate_analysis_data(sample_report(), sample_research())

    assert result["errors"] == []
    assert result["invalid_evidence_ids"] == []


def test_missing_required_section():
    report = sample_report()
    del report["swot_analysis"]

    result = validate_analysis_data(report, sample_research())

    assert "Missing section: swot_analysis" in result["errors"]


def test_invalid_section_type():
    report = sample_report()
    report["pricing_matrix"] = {}

    result = validate_analysis_data(report, sample_research())

    assert any("pricing_matrix" in error for error in result["errors"])


def test_invalid_evidence_reference():
    report = sample_report()
    report["competitor_comparison"][0]["evidence_ids"] = ["E999"]

    result = validate_analysis_data(report, sample_research())

    assert result["invalid_evidence_ids"] == ["E999"]


def test_nested_evidence_references():
    report = sample_report()
    report["swot_analysis"] = {
        "strengths": [
            {"evidence_ids": ["E001"]}
        ]
    }

    result = validate_analysis_data(report, sample_research())

    assert result["invalid_evidence_ids"] == []


def test_multiple_invalid_evidence_references():
    report = sample_report()
    report["market_opportunities"][0]["evidence_ids"] = ["E999", "E888"]

    result = validate_analysis_data(report, sample_research())

    assert set(result["invalid_evidence_ids"]) == {"E999", "E888"}
