
import json
from pathlib import Path


def validate_analysis_data(report, research):
    """Validate Analyst output structure and evidence references."""

    errors = []

    required_sections = [
        "competitor_comparison",
        "pricing_matrix",
        "swot_analysis",
        "marketing_mix_4p",
        "marketing_mix_7p",
        "market_opportunities",
        "research_gaps",
        "limitations",
    ]

    for section in required_sections:
        if section not in report:
            errors.append(f"Missing section: {section}")

    list_sections = [
        "competitor_comparison",
        "pricing_matrix",
        "market_opportunities",
        "research_gaps",
        "limitations",
    ]

    for section in list_sections:
        if section in report and not isinstance(report[section], list):
            errors.append(f"Section '{section}' must be a list.")

    if errors:
        return {"errors": errors}

    valid_ids = {
        item.get("evidence_id")
        for item in research.get("evidence", [])
        if isinstance(item, dict) and item.get("evidence_id")
    }

    referenced_ids = set()

    def collect_evidence_ids(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "evidence_ids" and isinstance(item, list):
                    referenced_ids.update(item)
                else:
                    collect_evidence_ids(item)

        elif isinstance(value, list):
            for item in value:
                collect_evidence_ids(item)

    collect_evidence_ids(report)

    invalid_ids = referenced_ids - valid_ids

    return {
        "errors": errors,
        "competitors": len(report["competitor_comparison"]),
        "pricing_records": len(report["pricing_matrix"]),
        "market_opportunities": len(report["market_opportunities"]),
        "evidence_ids_referenced": len(referenced_ids),
        "invalid_evidence_ids": sorted(invalid_ids),
    }


def main():
    project_root = Path(__file__).resolve().parent.parent

    analysis_path = project_root / "outputs" / "analysis_report.json"
    research_path = project_root / "outputs" / "research_evidence.json"

    if not analysis_path.exists():
        raise FileNotFoundError(f"Analysis report not found: {analysis_path}")

    if not research_path.exists():
        raise FileNotFoundError(f"Research output not found: {research_path}")

    report = json.loads(analysis_path.read_text(encoding="utf-8"))
    research = json.loads(research_path.read_text(encoding="utf-8"))

    result = validate_analysis_data(report, research)

    print("Analyst report validation")
    print("-------------------------")

    if "competitors" in result:
        print("Competitors analyzed:", result["competitors"])
        print("Pricing records:", result["pricing_records"])
        print("Market opportunities:", result["market_opportunities"])
        print("Evidence IDs referenced:", result["evidence_ids_referenced"])
        print("Invalid evidence IDs:", len(result["invalid_evidence_ids"]))

    if result["errors"]:
        print("Structural errors:", result["errors"])

    if result.get("invalid_evidence_ids"):
        print("Invalid IDs:", result["invalid_evidence_ids"])

    if result["errors"] or result.get("invalid_evidence_ids"):
        raise SystemExit("Analysis validation failed.")

    print("Analysis structural validation passed.")


if __name__ == "__main__":
    main()
