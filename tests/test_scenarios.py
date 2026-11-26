import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.scenario_evaluator import (
    SCENARIO_BRIEFS,
    build_controlled_run_outputs,
    compute_factual_consistency,
    evaluate_all_scenarios,
)


def test_at_least_three_fixed_scenarios_exist():
    assert len(SCENARIO_BRIEFS) >= 3


def test_scenario_golden_outputs_and_reproducibility(tmp_path):
    report_path = tmp_path / "scenario_test_report.json"
    report = evaluate_all_scenarios(output_path=report_path)

    assert report_path.exists()
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["total_scenarios"] >= 3
    assert saved["all_golden_passed"] is True
    assert saved["meets_80_percent_target"] is True
    assert saved["average_consistency_percent"] >= 80.0

    for scenario_result in saved["scenarios"]:
        assert scenario_result["golden_passed"] is True
        assert scenario_result["reproducibility"]["overall_consistency_percent"] >= 80.0


def test_reproducibility_calculation_distinguishes_identical_and_disjoint_runs():
    scenario = SCENARIO_BRIEFS[0]
    run_a = build_controlled_run_outputs(scenario, variant=1)
    run_b = build_controlled_run_outputs(scenario, variant=1)
    identical = compute_factual_consistency(run_a, run_b)
    assert identical["overall_consistency_percent"] == 100.0

    disjoint_run = {
        "research": {"competitors": [{"name": "Other"}], "evidence": [{"source_url": "https://other.example.com"}], "research_questions": []},
        "analysis": {"pricing_matrix": [], "market_opportunities": []},
        "strategy": {"ideal_customer_profiles": []},
    }
    disjoint = compute_factual_consistency(run_a, disjoint_run)
    assert disjoint["overall_consistency_percent"] < 50.0
    assert disjoint["meets_80_percent_target"] is False
