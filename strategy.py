import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv

from tools.prompt_loader import load_prompt_config
from tools.usage_tracker import record_agent_usage

load_dotenv()

# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

RESEARCH_FILE = OUTPUT_DIR / "research_evidence.json"
ANALYSIS_FILE = OUTPUT_DIR / "analysis_report.json"

OUTPUT_FILE = OUTPUT_DIR / "gtm_strategy.json"
RAW_OUTPUT_FILE = OUTPUT_DIR / "gtm_strategy_raw.txt"

OUTPUT_DIR.mkdir(exist_ok=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

for file_path in [RESEARCH_FILE, ANALYSIS_FILE]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Required input not found: {file_path}. "
            "Run the preceding pipeline stages first."
        )

research_data = json.loads(
    RESEARCH_FILE.read_text(encoding="utf-8")
)

analysis_data = json.loads(
    ANALYSIS_FILE.read_text(encoding="utf-8")
)

# Combine both inputs without discarding their original structure.
input_data = {
    "research": research_data,
    "analysis": analysis_data,
}

input_json = json.dumps(
    input_data,
    ensure_ascii=False,
    indent=2,
)

llm = LLM(
    model="gemini/gemini-3.5-flash-lite",
    api_key=api_key,
    temperature=0.2,
)

def validate_strategy_structure(strategy: dict):
    """Check that all mandatory GTM sections exist."""

    required_sections = [
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

    missing_sections = [
        section
        for section in required_sections
        if section not in strategy
    ]

    if missing_sections:
        raise ValueError(
            "Strategy output is missing sections: "
            + ", ".join(missing_sections)
        )

    # Validate SWOT categories.
    swot = strategy["swot_analysis"]

    for category in [
        "strengths",
        "weaknesses",
        "opportunities",
        "threats",
    ]:
        if not isinstance(swot.get(category), list) or not swot[category]:
            raise ValueError(
                f"SWOT category is missing or empty: {category}"
            )

    # Validate all seven marketing mix elements.
    marketing_mix = strategy["marketing_mix_7p"]

    required_7p = [
        "product",
        "price",
        "place",
        "promotion",
        "people",
        "process",
        "physical_evidence",
    ]

    missing_7p = [
        item for item in required_7p
        if not isinstance(marketing_mix.get(item), dict)
    ]

    if missing_7p:
        raise ValueError(
            "Missing 7P marketing elements: "
            + ", ".join(missing_7p)
        )

    # Validate four launch phases.
    if len(strategy["launch_plan"]) < 4:
        raise ValueError(
            "Launch plan must contain at least four phases."
        )

    # Validate all six funnel stages.
    required_stages = {
        "awareness",
        "acquisition",
        "activation",
        "engagement",
        "conversion",
        "retention",
    }

    actual_stages = {
        item.get("funnel_stage", "").strip().lower()
        for item in strategy["measurement_framework"]
        if isinstance(item, dict)
    }

    missing_stages = required_stages - actual_stages

    if missing_stages:
        raise ValueError(
            "Missing KPI funnel stages: "
            + ", ".join(sorted(missing_stages))
        )

    print("Strategy structure validation passed.")

# --------------------------------------------------
# 2. Strategy Agent & Task from prompts/strategy.yaml
# --------------------------------------------------

prompt_cfg = load_prompt_config("strategy")

strategy_agent = Agent(
    role=prompt_cfg["agent"]["role"],
    goal=prompt_cfg["agent"]["goal"],
    backstory=prompt_cfg["agent"]["backstory"],
    llm=llm,
    verbose=True,
    allow_delegation=False,
    max_iter=8,
)

strategy_task = Task(
    description=prompt_cfg["task"]["description"],
    expected_output=prompt_cfg["task"]["expected_output"],
    agent=strategy_agent,
)

# --------------------------------------------------
# 4. Run strategy generation
# --------------------------------------------------

start_time = time.perf_counter()

crew = Crew(
    agents=[strategy_agent],
    tasks=[strategy_task],
    process=Process.sequential,
    verbose=True,
)

result = crew.kickoff(
    inputs={"input_data": input_json}
)

duration_seconds = round(
    time.perf_counter() - start_time,
    2,
)

record_agent_usage(
    agent_name="Strategy Agent",
    model_name=llm.model,
    crew_output=result,
    duration_seconds=duration_seconds,
)

raw_output = str(result).strip()
json_text = raw_output

# Handle accidental Markdown fences.
if json_text.startswith("```"):
    lines = json_text.splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    json_text = "\n".join(lines).strip()

# --------------------------------------------------
# 5. Save output
# --------------------------------------------------

try:
    strategy = json.loads(json_text)
    
    validate_strategy_structure(strategy)
    
    # Always use the actual execution timestamp.
    generated_at = datetime.now(timezone.utc).isoformat()

    strategy["generated_at"] = generated_at
    strategy["run_metadata"] = {
        "generated_at": generated_at,
        "duration_seconds": duration_seconds,
        "model": "gemini/gemini-3.5-flash-lite",
        "research_input": str(RESEARCH_FILE),
        "analysis_input": str(ANALYSIS_FILE),
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            strategy,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\nGTM strategy saved to: {OUTPUT_FILE}")

except json.JSONDecodeError:
    RAW_OUTPUT_FILE.write_text(
        raw_output,
        encoding="utf-8",
    )

    print("\nThe model did not return valid JSON.")
    print(f"Raw output saved to: {RAW_OUTPUT_FILE}")

print(f"Strategy generation duration: {duration_seconds} seconds")
print("Strategy Agent finished.")