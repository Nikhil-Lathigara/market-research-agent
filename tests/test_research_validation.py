
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from validate_research import validate_research_data


def sample_data():
    return {
        "research_questions": [
            {"question": "What features do competitors offer?",
             "evidence_ids": ["E001"]}
        ],
        "competitors": [
            {"name": "Example", "evidence_ids": ["E001"]}
        ],
        "evidence": [
            {
                "evidence_id": "E001",
                "source_url": "https://example.com",
            }
        ],
        "market_opportunities": [],
        "limitations": [],
    }


def test_valid_research_data():
    result = validate_research_data(sample_data())

    assert result["errors"] == []
    assert result["missing_urls"] == []
    assert result["invalid_urls"] == []
    assert result["duplicate_ids"] == []
    assert result["broken_references"] == []


def test_missing_required_section():
    data = sample_data()
    del data["limitations"]

    result = validate_research_data(data)

    assert any("Missing section: limitations" in error
               for error in result["errors"])


def test_duplicate_evidence_ids():
    data = sample_data()
    data["evidence"].append({
        "evidence_id": "E001",
        "source_url": "https://another-example.com",
    })

    result = validate_research_data(data)

    assert result["duplicate_ids"] == ["E001"]


def test_missing_evidence_url():
    data = sample_data()
    data["evidence"][0]["source_url"] = ""

    result = validate_research_data(data)

    assert result["missing_urls"] == ["E001"]


def test_invalid_evidence_url():
    data = sample_data()
    data["evidence"][0]["source_url"] = "not-a-valid-url"

    result = validate_research_data(data)

    assert result["invalid_urls"] == ["E001"]


def test_broken_competitor_evidence_reference():
    data = sample_data()
    data["competitors"][0]["evidence_ids"] = ["E999"]

    result = validate_research_data(data)

    assert "E999" in result["broken_references"]


def test_broken_research_question_reference():
    data = sample_data()
    data["research_questions"][0]["evidence_ids"] = ["E999"]

    result = validate_research_data(data)

    assert "E999" in result["broken_references"]
