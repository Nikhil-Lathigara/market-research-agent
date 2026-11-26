import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Process, Task
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

from tools.prompt_loader import load_prompt_config
from tools.usage_tracker import record_agent_usage

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

llm = LLM(
    model="gemini/gemini-3.5-flash-lite",
    api_key=api_key,
    temperature=0.2,
)

server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(BASE_DIR / "mcp_server.py")],
    env=os.environ.copy(),
)

# Load prompts & brief from prompts/research.yaml
prompt_cfg = load_prompt_config("research")
KNOWN_COMPETITORS = prompt_cfg.get("known_competitors", [])
MARKET_BRIEF = prompt_cfg["market_brief"].format(
    known_competitors=json.dumps(KNOWN_COMPETITORS)
)

# --------------------------------------------------
# 2. Research Agent & Task from prompts/research.yaml
# --------------------------------------------------

research_agent = Agent(
    role=prompt_cfg["agent"]["role"],
    goal=prompt_cfg["agent"]["goal"],
    backstory=prompt_cfg["agent"]["backstory"],
    llm=llm,
    verbose=True,
    allow_delegation=False,
    max_iter=12,
)

research_task = Task(
    description=prompt_cfg["task"]["description"],
    expected_output=prompt_cfg["task"]["expected_output"],
    agent=research_agent,
)

# --------------------------------------------------
# 4. Run the workflow using MCP tools
# --------------------------------------------------

start_time = time.perf_counter()

print("\nStarting MCP-powered market research...")

with MCPServerAdapter(server_params) as mcp_tools:

    print("\nDiscovered MCP tools:")

    for tool in mcp_tools:
        print(f"- {tool.name}")

    if not mcp_tools:
        raise RuntimeError("No MCP tools were discovered.")

    # Ensure the expected capabilities exist.
    available_names = {tool.name for tool in mcp_tools}

    expected_names = {
        "search_web",
        "fetch_webpage",
        "validate_url",
    }

    missing = expected_names - available_names

    if missing:
        raise RuntimeError(
            f"Missing MCP tools: {', '.join(sorted(missing))}"
        )

    research_agent.tools = mcp_tools

    crew = Crew(
        agents=[research_agent],
        tasks=[research_task],
        process=Process.sequential,
        verbose=True,
    )

    active_brief = os.getenv("MARKET_BRIEF_OVERRIDE", "").strip() or MARKET_BRIEF

    result = crew.kickoff(
        inputs={"market_brief": active_brief}
    )

elapsed_seconds = round(time.perf_counter() - start_time, 2)

record_agent_usage(
    agent_name="Research Agent",
    model_name=llm.model,
    crew_output=result,
    duration_seconds=elapsed_seconds,
)


def calculate_research_metrics(report):
    evidence = report.get("evidence", [])
    questions = report.get("research_questions", [])

    evidence_ids = [
        item.get("evidence_id")
        for item in evidence
        if item.get("evidence_id")
    ]

    # Check for duplicate evidence IDs.
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Duplicate evidence IDs detected.")

    valid_ids = set(evidence_ids)

    # Check all referenced evidence IDs.
    referenced_ids = set()

    def collect_references(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "evidence_ids" and isinstance(item, list):
                    referenced_ids.update(item)
                else:
                    collect_references(item)

        elif isinstance(value, list):
            for item in value:
                collect_references(item)

    collect_references(report)

    invalid_ids = referenced_ids - valid_ids

    if invalid_ids:
        raise ValueError(
            f"Invalid evidence references: {sorted(invalid_ids)}"
        )

    # Validate evidence records.
    for item in evidence:
        if not item.get("source_url"):
            raise ValueError(
                f"Missing source URL: {item.get('evidence_id')}"
            )

        if item.get("source_type") not in {"primary", "secondary"}:
            raise ValueError(
                f"Invalid source_type: {item.get('evidence_id')}"
            )

        if item.get("source_quality") not in {"high", "medium", "low"}:
            raise ValueError(
                f"Invalid source_quality: {item.get('evidence_id')}"
            )

    total_evidence = len(evidence)

    primary_count = sum(
        1 for item in evidence
        if item.get("source_type") == "primary"
    )

    high_quality_count = sum(
        1 for item in evidence
        if item.get("source_quality") == "high"
    )

    primary_or_high_count = sum(
        1 for item in evidence
        if (
            item.get("source_type") == "primary"
            or item.get("source_quality") == "high"
        )
    )

    answered_count = sum(
        1 for item in questions
        if item.get("status") == "answered"
    )

    partially_answered_count = sum(
        1 for item in questions
        if item.get("status") == "partially_answered"
    )

    unanswered_count = sum(
        1 for item in questions
        if item.get("status") == "unanswered"
    )

    question_count = len(questions)

    return {
        "total_evidence_records": total_evidence,
        "primary_source_count": primary_count,
        "high_quality_source_count": high_quality_count,
        "primary_or_high_quality_count": primary_or_high_count,
        "primary_or_high_quality_percentage": round(
            primary_or_high_count / total_evidence * 100, 2
        ) if total_evidence else 0,
        "research_questions_total": question_count,
        "research_questions_answered": answered_count,
        "research_questions_partially_answered": partially_answered_count,
        "research_questions_unanswered": unanswered_count,
        "research_question_coverage_percentage": round(
            (answered_count + partially_answered_count) /
            question_count * 100, 2
        ) if question_count else 0,
        "invalid_evidence_ids": len(invalid_ids),
    }


# --------------------------------------------------
# 5. Save research output
# --------------------------------------------------

raw_output = str(result).strip()

json_text = raw_output

if json_text.startswith("```"):
    lines = json_text.splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    json_text = "\n".join(lines).strip()

json_path = OUTPUT_DIR / "research_evidence.json"
raw_path = OUTPUT_DIR / "research_raw.txt"

try:
    parsed_output = json.loads(json_text)

    if not isinstance(parsed_output, dict):
        raise ValueError("Research output must be a JSON object.")

    # Python is the source of truth for timestamps.
    generated_at = datetime.now(timezone.utc).isoformat()

    parsed_output["research_timestamp"] = generated_at

    metrics = calculate_research_metrics(parsed_output)

    parsed_output["run_metadata"] = {
        "generated_at": generated_at,
        "duration_seconds": elapsed_seconds,
        "model": "gemini/gemini-3.5-flash-lite",
        **metrics,
    }

    json_path.write_text(
        json.dumps(
            parsed_output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\nStructured research saved to: {json_path}")

    print("\nRESEARCH QUALITY METRICS")
    print("=" * 45)
    print(f"Evidence records: {metrics['total_evidence_records']}")
    print(f"Primary sources: {metrics['primary_source_count']}")
    print(
        "Primary or high-quality sources: "
        f"{metrics['primary_or_high_quality_percentage']}%"
    )
    print(
        "Research question coverage: "
        f"{metrics['research_question_coverage_percentage']}%"
    )
    print(
        "Questions answered: "
        f"{metrics['research_questions_answered']}"
    )
    print(
        "Questions partially answered: "
        f"{metrics['research_questions_partially_answered']}"
    )
    print(
        "Questions unanswered: "
        f"{metrics['research_questions_unanswered']}"
    )

except (json.JSONDecodeError, ValueError, TypeError) as exc:
    raw_path.write_text(
        raw_output,
        encoding="utf-8",
    )

    print(f"\nResearch validation failed: {exc}")
    print(f"Raw output saved to: {raw_path}")

    raise

print(f"\nResearch duration: {elapsed_seconds} seconds")
print("\nResearch workflow completed.")
