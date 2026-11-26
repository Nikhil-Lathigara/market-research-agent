import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
PRICING_CONFIG_PATH = BASE_DIR / "pricing_config.json"
DEFAULT_USAGE_REPORT_PATH = BASE_DIR / "outputs" / "usage_report.json"


def load_pricing_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configurable model pricing and budget settings."""
    path = config_path or PRICING_CONFIG_PATH
    if not path.exists():
        return {
            "currency": "USD",
            "budget_limit_usd": 1.0,
            "models": {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def get_budget_limit_usd(config: dict[str, Any] | None = None) -> float:
    """Return configured budget limit in USD, allowing PIPELINE_BUDGET_USD override."""
    env_val = os.getenv("PIPELINE_BUDGET_USD")
    if env_val:
        try:
            return float(env_val)
        except ValueError:
            pass
    cfg = config if config is not None else load_pricing_config()
    return float(cfg.get("budget_limit_usd", 1.0))


def extract_token_usage(crew_output: Any) -> dict[str, Any]:
    """Extract provider-reported token usage from a CrewAI CrewOutput object.

    Never fabricates token counts or estimates them from execution time.
    """
    usage_obj = getattr(crew_output, "token_usage", None)
    if usage_obj is None:
        return {
            "usage_available": False,
            "usage_source": "unavailable",
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "cached_prompt_tokens": None,
            "reasoning_tokens": None,
            "successful_requests": None,
        }

    def _get(field: str):
        if isinstance(usage_obj, dict):
            return usage_obj.get(field)
        return getattr(usage_obj, field, None)

    prompt_tokens = _get("prompt_tokens")
    completion_tokens = _get("completion_tokens")
    total_tokens = _get("total_tokens")

    has_any = any(
        isinstance(v, (int, float))
        for v in (prompt_tokens, completion_tokens, total_tokens)
    )

    if not has_any:
        return {
            "usage_available": False,
            "usage_source": "unavailable",
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "cached_prompt_tokens": None,
            "reasoning_tokens": None,
            "successful_requests": _get("successful_requests"),
        }

    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "usage_available": True,
        "usage_source": "provider_reported",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cached_prompt_tokens": _get("cached_prompt_tokens"),
        "reasoning_tokens": _get("reasoning_tokens"),
        "successful_requests": _get("successful_requests"),
    }


def estimate_cost_usd(
    model_name: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    pricing_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate estimated API cost from configured per-1M-token rates."""
    if prompt_tokens is None and completion_tokens is None:
        return {
            "estimated_cost_usd": None,
            "cost_source": "unavailable",
            "pricing_configured": False,
        }

    cfg = pricing_config if pricing_config is not None else load_pricing_config()
    models = cfg.get("models", {})
    rates = (
        models.get(model_name)
        or models.get(model_name.split("/")[-1])
        or models.get(f"gemini/{model_name}")
    )

    if not rates:
        return {
            "estimated_cost_usd": None,
            "cost_source": "unavailable_no_model_rate",
            "pricing_configured": False,
        }

    in_rate = float(rates.get("input_per_1m_tokens_usd", 0.0))
    out_rate = float(rates.get("output_per_1m_tokens_usd", 0.0))
    in_cost = ((prompt_tokens or 0) / 1_000_000.0) * in_rate
    out_cost = ((completion_tokens or 0) / 1_000_000.0) * out_rate
    total_cost = round(in_cost + out_cost, 6)

    return {
        "estimated_cost_usd": total_cost,
        "cost_source": "estimated_from_configured_rates",
        "pricing_configured": True,
        "rates_used": {
            "input_per_1m_tokens_usd": in_rate,
            "output_per_1m_tokens_usd": out_rate,
        },
    }


def init_usage_report(report_path: Path | None = None) -> Path:
    """Initialize a fresh usage report for a pipeline run."""
    path = report_path or DEFAULT_USAGE_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = load_pricing_config()
    budget = get_budget_limit_usd(cfg)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "currency": cfg.get("currency", "USD"),
        "budget_limit_usd": budget,
        "budget_exceeded": False,
        "agents": {},
        "totals": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "agents_with_usage": 0,
            "agents_missing_usage": 0,
        },
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _recompute_totals(report: dict[str, Any], budget_limit: float) -> None:
    agents = report.get("agents", {})
    prompt_sum = 0
    completion_sum = 0
    total_sum = 0
    cost_sum = 0.0
    with_usage = 0
    missing_usage = 0

    for entry in agents.values():
        if entry.get("usage_available"):
            with_usage += 1
            prompt_sum += entry.get("prompt_tokens") or 0
            completion_sum += entry.get("completion_tokens") or 0
            total_sum += entry.get("total_tokens") or 0
        else:
            missing_usage += 1

        est_cost = entry.get("estimated_cost_usd")
        if isinstance(est_cost, (int, float)):
            cost_sum += float(est_cost)

    cost_sum = round(cost_sum, 6)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["budget_limit_usd"] = budget_limit
    report["budget_exceeded"] = cost_sum > budget_limit
    report["totals"] = {
        "prompt_tokens": prompt_sum,
        "completion_tokens": completion_sum,
        "total_tokens": total_sum,
        "estimated_cost_usd": cost_sum,
        "agents_with_usage": with_usage,
        "agents_missing_usage": missing_usage,
    }


def record_agent_usage(
    agent_name: str,
    model_name: str,
    crew_output: Any,
    duration_seconds: float,
    report_path: Path | None = None,
    pricing_config_path: Path | None = None,
) -> dict[str, Any]:
    """Record token usage and estimated cost for one agent in outputs/usage_report.json."""
    path = report_path or DEFAULT_USAGE_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    cfg = load_pricing_config(pricing_config_path)
    budget_limit = get_budget_limit_usd(cfg)

    if path.exists():
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = {"agents": {}}
    else:
        report = {"agents": {}}

    if "agents" not in report or not isinstance(report["agents"], dict):
        report["agents"] = {}

    usage = extract_token_usage(crew_output)
    cost_info = estimate_cost_usd(
        model_name=model_name,
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        pricing_config=cfg,
    )

    entry = {
        "agent": agent_name,
        "model": model_name,
        "duration_seconds": round(duration_seconds, 2),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        **usage,
        **cost_info,
    }

    report["agents"][agent_name] = entry
    report["currency"] = cfg.get("currency", "USD")
    _recompute_totals(report, budget_limit)

    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
