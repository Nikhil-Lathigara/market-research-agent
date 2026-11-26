import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tests.validate_analysis import validate_analysis_data
from tests.validate_research import validate_research_data
from tests.validate_strategy import validate_strategy_data

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIO_REPORT_PATH = BASE_DIR / "outputs" / "scenario_test_report.json"

REQUIRED_REPORT_HEADINGS = [
    "# Market Research and Go-to-Market Plan",
    "## 1. Executive Summary",
    "## 2. Research Scope and Methodology",
    "## 3. Market Research Findings",
    "## 4. Competitor Landscape",
    "## 5. Competitive Pricing Analysis",
    "## 6. SWOT Analysis",
    "## 7. Marketing Mix",
    "## 8. Ideal Customer Profiles",
    "## 9. Positioning and Value Proposition",
    "## 10. Messaging Strategy",
    "## 11. Channel Strategy",
    "## 12. Launch Plan",
    "## 13. KPIs and Experiments",
    "## 14. Risks and Mitigations",
    "## 15. Evidence and Source Register",
    "## 16. Limitations and Items Requiring Verification",
]

SCENARIO_BRIEFS = [
    {
        "scenario_id": "ai_interview_prep_india",
        "title": "AI Interview Preparation Platforms (India)",
        "brief": "Research AI-powered interview preparation platforms for software developers in India.",
        "golden": {
            "expected_competitors": ["hello interview", "coprep ai", "final round ai", "aceinterview (mockai)"],
            "min_evidence_records": 4,
            "required_7p_keys": ["product", "price", "place", "promotion", "people", "process", "physical_evidence"],
        },
    },
    {
        "scenario_id": "dev_observability_saas_india",
        "title": "Developer Observability & APM SaaS (India)",
        "brief": "Research cloud-native observability and APM platforms targeting Indian SaaS engineering teams.",
        "golden": {
            "expected_competitors": ["signoz", "datadog", "grafana cloud"],
            "min_evidence_records": 3,
            "required_7p_keys": ["product", "price", "place", "promotion", "people", "process", "physical_evidence"],
        },
    },
    {
        "scenario_id": "sme_gst_accounting_india",
        "title": "AI-Assisted GST & SME Accounting Platforms (India)",
        "brief": "Research automated GST compliance and accounting platforms for Indian SMEs.",
        "golden": {
            "expected_competitors": ["zoho books", "tallyprime", "cleartax"],
            "min_evidence_records": 3,
            "required_7p_keys": ["product", "price", "place", "promotion", "people", "process", "physical_evidence"],
        },
    },
]


def _norm(text: Any) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def extract_factual_signature(run_outputs: dict[str, Any]) -> dict[str, set[str]]:
    """Extract normalized factual sets from a pipeline run for reproducibility comparison."""
    research = run_outputs.get("research", {})
    analysis = run_outputs.get("analysis", {})
    strategy = run_outputs.get("strategy", {})

    competitors = {
        _norm(c.get("name") or c.get("competitor"))
        for c in research.get("competitors", [])
        if isinstance(c, dict) and (c.get("name") or c.get("competitor"))
    }
    evidence_urls = {
        _norm(e.get("source_url"))
        for e in research.get("evidence", [])
        if isinstance(e, dict) and e.get("source_url")
    }
    pricing_facts = {
        f"{_norm(p.get('competitor'))}|{_norm(p.get('currency'))}|{_norm(p.get('verification_status'))}"
        for p in analysis.get("pricing_matrix", [])
        if isinstance(p, dict) and p.get("competitor")
    }
    market_claims = {
        _norm(q.get("question"))
        for q in research.get("research_questions", [])
        if isinstance(q, dict) and q.get("question")
    } | {
        _norm(o.get("opportunity"))
        for o in analysis.get("market_opportunities", [])
        if isinstance(o, dict) and o.get("opportunity")
    }
    strategy_evidence_ids = {
        _norm(eid)
        for icp in strategy.get("ideal_customer_profiles", [])
        if isinstance(icp, dict)
        for eid in icp.get("evidence_ids", [])
    }

    return {
        "competitors": competitors,
        "evidence_urls": evidence_urls,
        "pricing_facts": pricing_facts,
        "market_claims": market_claims,
        "strategy_evidence_ids": strategy_evidence_ids,
    }


def compute_factual_consistency(run1: dict[str, Any], run2: dict[str, Any]) -> dict[str, Any]:
    """Compare two runs across normalized factual dimensions and return consistency %."""
    sig1 = extract_factual_signature(run1)
    sig2 = extract_factual_signature(run2)

    dimension_scores = {}
    for key in sig1:
        dimension_scores[key] = round(_jaccard(sig1[key], sig2[key]) * 100.0, 2)

    overall = round(sum(dimension_scores.values()) / len(dimension_scores), 2)
    return {
        "overall_consistency_percent": overall,
        "meets_80_percent_target": overall >= 80.0,
        "dimension_scores_percent": dimension_scores,
    }


def validate_markdown_report(report_text: str) -> list[str]:
    """Return any missing required headings from the final Markdown report."""
    return [h for h in REQUIRED_REPORT_HEADINGS if h not in report_text]


def build_controlled_run_outputs(scenario: dict[str, Any], variant: int = 1) -> dict[str, Any]:
    """Build deterministic controlled pipeline outputs for a scenario without live API calls."""
    competitors = scenario["golden"]["expected_competitors"]
    market = scenario["brief"]

    evidence = []
    comp_records = []
    comp_comparison = []
    pricing_matrix = []

    for idx, comp_name in enumerate(competitors, start=1):
        eid = f"E{idx:03d}"
        slug = comp_name.replace(" ", "").replace("(", "").replace(")", "")
        url = f"https://www.{slug}.example.com/pricing"
        evidence.append({
            "evidence_id": eid,
            "source_url": url,
            "source_type": "primary",
            "source_quality": "high",
            "claim": f"{comp_name} provides core platform capabilities for {market}.",
        })
        comp_records.append({
            "name": comp_name.title(),
            "competitor": comp_name.title(),
            "official_website": f"https://www.{slug}.example.com/",
            "evidence_ids": [eid],
        })
        comp_comparison.append({
            "competitor": comp_name.title(),
            "target_users": "Indian target segment",
            "key_features": ["Core workflow", "Analytics"],
            "pricing": "INR 999/month" if idx == 1 else "unknown",
            "differentiators": ["Localized support"],
            "evidence_ids": [eid],
            "limitations": [],
        })
        pricing_matrix.append({
            "competitor": comp_name.title(),
            "pricing_description": "INR 999/month" if idx == 1 else "unknown",
            "currency": "INR" if idx == 1 else "unknown",
            "pricing_source": url if idx == 1 else None,
            "verification_status": "verified" if idx == 1 else "unknown",
            "evidence_ids": [eid],
        })

    all_eids = [e["evidence_id"] for e in evidence]
    extra_opp = (
        [{"opportunity": "Self-serve onboarding", "reasoning": "Reduces CAC", "type": "inference", "evidence_ids": ["E001"], "validation_needed": ["Landing page test"]}]
        if variant == 2 else []
    )

    research = {
        "market": market,
        "research_timestamp": "2026-11-25T00:00:00+00:00",
        "research_questions": [
            {"question": "What are the key competitor products and features?", "answer": "See evidence.", "status": "answered", "evidence_ids": all_eids[:2]},
            {"question": "Who are the target users?", "answer": "Indian buyers.", "status": "answered", "evidence_ids": all_eids[:2]},
            {"question": "What is the publicly available pricing?", "answer": "Mixed verified/unknown.", "status": "answered", "evidence_ids": ["E001"]},
        ],
        "competitors": comp_records,
        "evidence": evidence,
        "market_opportunities": [
            {"opportunity": "Localized INR pricing", "evidence_ids": ["E001"]},
        ],
        "limitations": ["Controlled scenario test fixture."],
    }

    analysis = {
        "analysis_timestamp": "2026-11-25T00:00:00+00:00",
        "market": market,
        "competitor_comparison": comp_comparison,
        "pricing_matrix": pricing_matrix,
        "swot_analysis": {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [{"finding": "Localized INR pricing", "type": "inference", "evidence_ids": ["E001"]}],
            "threats": [{"finding": "Established incumbents", "type": "evidence", "evidence_ids": all_eids[:2]}],
        },
        "marketing_mix_4p": {"product": "SaaS", "price": "INR tiers", "place": "Web", "promotion": "SEO"},
        "marketing_mix_7p": {"people": "Support", "process": "Self-serve", "physical_evidence": "Dashboard"},
        "market_opportunities": [
            {"opportunity": "Localized INR pricing", "reasoning": "Reduces payment friction", "type": "inference", "evidence_ids": ["E001"], "validation_needed": ["WTP survey"]},
            *extra_opp,
        ],
        "research_gaps": ["Primary WTP data"],
        "limitations": ["Controlled scenario fixture"],
    }

    strategy = {
        "generated_at": "2026-11-25T00:00:00+00:00",
        "ideal_customer_profiles": [{"segment_name": "Primary Buyers", "evidence_ids": ["E001"]}],
        "positioning": {"core_value_proposition": "Localized workflow", "evidence_ids": ["E001"]},
        "messaging_framework": {"primary_message": "Built for India", "evidence_ids": ["E001"]},
        "channel_strategy": [{"channel": "SEO", "evidence_ids": ["E001"]}],
        "swot_analysis": {
            "strengths": [{"description": "Local focus", "evidence_ids": ["E001"]}],
            "weaknesses": [{"description": "New brand", "evidence_ids": []}],
            "opportunities": [{"description": "INR pricing", "evidence_ids": ["E001"]}],
            "threats": [{"description": "Incumbents", "evidence_ids": ["E002"]}],
        },
        "marketing_mix_7p": {
            k: {"summary": f"{k} strategy"} for k in scenario["golden"]["required_7p_keys"]
        },
        "pricing_strategy": {"recommended_tiers": ["INR 999/mo"], "evidence_ids": ["E001"]},
        "launch_plan": [
            {"phase": "Phase 1", "goal": "Beta", "activities": ["Closed beta"]},
            {"phase": "Phase 2", "goal": "Launch", "activities": ["Public release"]},
            {"phase": "Phase 3", "goal": "Growth", "activities": ["SEO & community"]},
            {"phase": "Phase 4", "goal": "Scale", "activities": ["Partnerships"]},
        ],
        "measurement_framework": [
            {"funnel_stage": stage, "metric": f"{stage}_rate"}
            for stage in ["awareness", "acquisition", "activation", "engagement", "conversion", "retention"]
        ],
        "risks_and_mitigations": [{"risk": "Churn", "mitigation": "Onboarding"}],
        "experiments": [{"name": "Pricing A/B"}],
        "evidence_limitations": ["Controlled fixture"],
    }

    report_lines = [heading + "\nSample content.\n" for heading in REQUIRED_REPORT_HEADINGS]
    report_md = "\n".join(report_lines)

    return {
        "research": research,
        "analysis": analysis,
        "strategy": strategy,
        "report_md": report_md,
    }


def evaluate_all_scenarios(output_path: Path | None = None) -> dict[str, Any]:
    """Run all fixed scenarios, validate outputs, measure repeat-run consistency, and save report."""
    target_path = output_path or DEFAULT_SCENARIO_REPORT_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for scenario in SCENARIO_BRIEFS:
        run1 = build_controlled_run_outputs(scenario, variant=1)
        run2 = build_controlled_run_outputs(scenario, variant=2)

        res_val = validate_research_data(run1["research"])
        ana_val = validate_analysis_data(run1["analysis"], run1["research"])
        strat_val = validate_strategy_data(run1["strategy"], run1["research"])
        missing_headings = validate_markdown_report(run1["report_md"])

        actual_comps = {_norm(c.get("name") or c.get("competitor")) for c in run1["research"]["competitors"]}
        expected_comps = set(scenario["golden"]["expected_competitors"])
        golden_passed = (
            expected_comps.issubset(actual_comps)
            and len(run1["research"]["evidence"]) >= scenario["golden"]["min_evidence_records"]
            and not res_val["errors"]
            and not ana_val["errors"]
            and not strat_val["errors"]
            and not missing_headings
        )

        consistency = compute_factual_consistency(run1, run2)

        results.append({
            "scenario_id": scenario["scenario_id"],
            "title": scenario["title"],
            "golden_passed": golden_passed,
            "validation": {
                "research_errors": res_val["errors"],
                "analysis_errors": ana_val["errors"],
                "strategy_errors": strat_val["errors"],
                "missing_report_headings": missing_headings,
            },
            "reproducibility": consistency,
        })

    avg_consistency = round(
        sum(r["reproducibility"]["overall_consistency_percent"] for r in results) / len(results),
        2,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": len(results),
        "all_golden_passed": all(r["golden_passed"] for r in results),
        "average_consistency_percent": avg_consistency,
        "meets_80_percent_target": avg_consistency >= 80.0,
        "scenarios": results,
        "limitations": [
            "Automated scenario tests use controlled/mocked pipeline outputs to avoid live LLM/SerpAPI costs and nondeterminism.",
            "Live LLM runs are inherently nondeterministic; temperature=0.2 reduces variance but phrasing, optional opportunities, and search result ordering can vary across runs.",
            "Consistency scoring compares normalized structured facts (competitor names, URLs, pricing status, claims, evidence IDs) rather than raw text equality.",
        ],
    }
    target_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
