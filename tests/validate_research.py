
import json
from pathlib import Path
from urllib.parse import urlparse


def validate_research_data(data):
    """Validate research output structure, evidence IDs, URLs and references."""

    errors = []

    required_sections = [
        "research_questions",
        "competitors",
        "evidence",
        "market_opportunities",
        "limitations",
    ]

    for section in required_sections:
        if section not in data:
            errors.append(f"Missing section: {section}")

    list_sections = [
        "research_questions",
        "competitors",
        "evidence",
        "market_opportunities",
    ]

    for section in list_sections:
        if section in data and not isinstance(data[section], list):
            errors.append(f"Section '{section}' must be a list.")

    if errors:
        return {"errors": errors}

    evidence = data["evidence"]
    competitors = data["competitors"]
    questions = data["research_questions"]

    evidence_ids = []
    missing_urls = []
    invalid_urls = []
    broken_references = []

    # Validate evidence records
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"Evidence record at index {index} must be an object.")
            continue

        evidence_id = item.get("evidence_id")

        if not evidence_id:
            errors.append(f"Evidence record at index {index} has no evidence_id.")
        else:
            evidence_ids.append(evidence_id)

        source_url = item.get("source_url")

        if not source_url:
            missing_urls.append(evidence_id or f"index {index}")
        else:
            parsed_url = urlparse(source_url)

            if (
                parsed_url.scheme not in ("http", "https")
                or not parsed_url.netloc
            ):
                invalid_urls.append(evidence_id or f"index {index}")

    # Detect duplicate evidence IDs
    seen_ids = set()
    duplicate_ids = []

    for evidence_id in evidence_ids:
        if evidence_id in seen_ids:
            duplicate_ids.append(evidence_id)
        seen_ids.add(evidence_id)

    valid_ids = set(evidence_ids)

    # Validate evidence references
    reference_groups = [
        ("competitor", competitors),
        ("research question", questions),
    ]

    for label, records in reference_groups:
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                errors.append(
                    f"{label.capitalize()} at index {index} must be an object."
                )
                continue

            references = record.get("evidence_ids", [])

            if not isinstance(references, list):
                errors.append(
                    f"{label.capitalize()} at index {index}: "
                    "evidence_ids must be a list."
                )
                continue

            for evidence_id in references:
                if evidence_id not in valid_ids:
                    broken_references.append(evidence_id)

    return {
        "errors": errors,
        "research_questions": len(questions),
        "competitors": len(competitors),
        "evidence_records": len(evidence),
        "missing_urls": missing_urls,
        "invalid_urls": invalid_urls,
        "duplicate_ids": duplicate_ids,
        "broken_references": broken_references,
    }


def main():
    project_root = Path(__file__).resolve().parent.parent
    path = project_root / "outputs" / "research_evidence.json"

    if not path.exists():
        raise FileNotFoundError(
            f"Research output not found: {path}. Run main.py first."
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    result = validate_research_data(data)

    print("Research output validation")
    print("--------------------------")

    if "research_questions" in result:
        print("Research questions:", result["research_questions"])
        print("Competitors:", result["competitors"])
        print("Evidence records:", result["evidence_records"])
        print("Evidence without URLs:", len(result["missing_urls"]))
        print("Invalid URLs:", len(result["invalid_urls"]))
        print("Duplicate evidence IDs:", len(result["duplicate_ids"]))
        print("Broken evidence references:", len(result["broken_references"]))

    if result["errors"]:
        print("\nStructural errors:", result["errors"])

    for key in [
        "missing_urls",
        "invalid_urls",
        "duplicate_ids",
        "broken_references",
    ]:
        if result.get(key):
            print(f"{key}:", result[key])

    has_failures = (
        result["errors"]
        or result.get("missing_urls")
        or result.get("invalid_urls")
        or result.get("duplicate_ids")
        or result.get("broken_references")
    )

    if has_failures:
        raise SystemExit("Research validation failed.")

    print("Research structural validation passed.")


if __name__ == "__main__":
    main()
