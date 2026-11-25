
import json
from pathlib import Path


REQUIRED_SECTIONS = [
    "ideal_customer_profiles",
    "positioning",
    "messaging_framework",
    "channel_strategy",
    "swot_analysis",
    "marketing_mix_7p",
    "pricing_strategy",
    "launch_plan",
    "measurement_framework",
    "risks_and_mitigations",
    "experiments",
    "evidence_limitations",
]

REQUIRED_7P = [
    "product",
    "price",
    "place",
    "promotion",
    "people",
    "process",
    "physical_evidence",
]

REQUIRED_STAGES = {
    "awareness",
    "acquisition",
    "activation",
    "engagement",
    "conversion",
    "retention",
}


def collect_evidence_ids(data):
    ids = set()

    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() in {
                "evidence_id",
                "evidence_ids",
                "source_evidence_id",
            }:
                if isinstance(value, str):
                    ids.add(value)
                elif isinstance(value, list):
                    ids.update(
                        item for item in value
                        if isinstance(item, str)
                    )
            else:
                ids.update(collect_evidence_ids(value))

    elif isinstance(data, list):
        for item in data:
            ids.update(collect_evidence_ids(item))

    return ids


def find_research_ids(data):
    ids = set()

    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() in {"evidence_id", "id"}:
                if isinstance(value, str) and value.startswith("E"):
                    ids.add(value)

            ids.update(find_research_ids(value))

    elif isinstance(data, list):
        for item in data:
            ids.update(find_research_ids(item))

    return ids


def validate_strategy_data(strategy, research):
    errors = []
    warnings = []

    if not isinstance(strategy, dict):
        return {
            "errors": ["Strategy output must be a JSON object."],
            "warnings": [],
        }

    if not isinstance(research, dict):
        return {
            "errors": ["Research output must be a JSON object."],
            "warnings": [],
        }

    # 1. Required sections
    for section in REQUIRED_SECTIONS:
        if section not in strategy:
            errors.append(f"Missing section: {section}")

    if errors:
        return {"errors": errors, "warnings": warnings}

    # 2. SWOT validation
    swot = strategy.get("swot_analysis")

    if not isinstance(swot, dict):
        errors.append("SWOT analysis must be an object.")
        swot = {}

    for category in [
        "strengths",
        "weaknesses",
        "opportunities",
        "threats",
    ]:
        if not isinstance(swot.get(category), list) or not swot[category]:
            errors.append(f"Missing or empty SWOT category: {category}")

    # 3. 7P validation
    marketing_mix = strategy.get("marketing_mix_7p")

    if not isinstance(marketing_mix, dict):
        errors.append("Marketing mix 7P must be an object.")
        marketing_mix = {}

    for item in REQUIRED_7P:
        if not isinstance(marketing_mix.get(item), dict):
            errors.append(f"Missing 7P element: {item}")

    # 4. Launch plan validation
    launch_plan = strategy.get("launch_plan")

    if not isinstance(launch_plan, list):
        errors.append("Launch plan must be a list.")
        launch_plan = []

    if len(launch_plan) < 4:
        errors.append("Launch plan must have at least four phases.")

    for index, phase in enumerate(launch_plan, start=1):
        if not isinstance(phase, dict):
            errors.append(f"Launch phase {index} must be an object.")
            continue

        if not phase.get("phase"):
            errors.append(f"Launch phase {index} has no name.")

        if not phase.get("activities"):
            errors.append(f"Launch phase {index} has no activities.")

    # 5. Funnel KPI validation
    measurement = strategy.get("measurement_framework")

    if not isinstance(measurement, list):
        errors.append("Measurement framework must be a list.")
        measurement = []

    actual_stages = {
        item.get("funnel_stage", "").strip().lower()
        for item in measurement
        if isinstance(item, dict)
        and isinstance(item.get("funnel_stage"), str)
    }

    missing_stages = REQUIRED_STAGES - actual_stages

    if missing_stages:
        errors.append(
            "Missing funnel KPI stages: "
            + ", ".join(sorted(missing_stages))
        )

    # 6. Evidence ID validation
    research_ids = find_research_ids(research)
    strategy_ids = collect_evidence_ids(strategy)
    invalid_ids = strategy_ids - research_ids

    if invalid_ids:
        errors.append(f"Invalid evidence IDs: {sorted(invalid_ids)}")

    # 7. Metadata validation
    metadata = strategy.get("run_metadata")

    if not isinstance(metadata, dict):
        metadata = {}
        warnings.append("Missing or invalid run metadata.")

    if not metadata.get("generated_at"):
        warnings.append("Missing run metadata timestamp.")

    if not metadata.get("model"):
        warnings.append("Missing model information.")

    if strategy.get("generated_at") != metadata.get("generated_at"):
        warnings.append(
            "Top-level and run metadata timestamps do not match."
        )

    return {
        "errors": errors,
        "warnings": warnings,
        "required_sections": len(REQUIRED_SECTIONS),
        "swot_categories": len(swot),
        "7p_elements": len(marketing_mix),
        "launch_phases": len(launch_plan),
        "kpi_stages": len(actual_stages),
        "evidence_ids_referenced": len(strategy_ids),
        "invalid_evidence_ids": sorted(invalid_ids),
    }


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def main():
    base_dir = Path(__file__).resolve().parent.parent

    strategy = load_json(base_dir / "outputs" / "gtm_strategy.json")
    research = load_json(base_dir / "outputs" / "research_evidence.json")

    result = validate_strategy_data(strategy, research)

    print("\nSTRATEGY VALIDATION")
    print("=" * 55)

    if "required_sections" in result:
        print(
            f"Required sections: "
            f"{result['required_sections']}/"
            f"{len(REQUIRED_SECTIONS)}"
        )
        print(f"SWOT categories: {result['swot_categories']}")
        print(f"7P elements: {result['7p_elements']}")
        print(f"Launch phases: {result['launch_phases']}")
        print(f"KPI stages: {result['kpi_stages']}")
        print(f"Evidence IDs referenced: {result['evidence_ids_referenced']}")
        print(f"Invalid evidence IDs: {len(result['invalid_evidence_ids'])}")

    print("\nERRORS")
    if result["errors"]:
        for error in result["errors"]:
            print(f"[FAIL] {error}")
    else:
        print("[PASS] No structural validation errors.")

    print("\nWARNINGS")
    if result["warnings"]:
        for warning in result["warnings"]:
            print(f"[WARNING] {warning}")
    else:
        print("[PASS] No metadata warnings.")

    if result["errors"]:
        print("\nStrategy validation FAILED.")
        raise SystemExit(1)

    print("\nStrategy structural validation PASSED.")


if __name__ == "__main__":
    main()
