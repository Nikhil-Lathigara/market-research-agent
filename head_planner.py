import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Process, Task

from tools.prompt_loader import load_prompt_config
from tools.usage_tracker import record_agent_usage


# --------------------------------------------------
# 1. Setup
# --------------------------------------------------

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

RESEARCH_FILE = OUTPUT_DIR / "research_evidence.json"
ANALYSIS_FILE = OUTPUT_DIR / "analysis_report.json"
STRATEGY_FILE = OUTPUT_DIR / "gtm_strategy.json"

REPORT_FILE = OUTPUT_DIR / "final_market_research_report.md"

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from your .env file")


# Use the exact model identifier that works in your project.
# Store it in .env as GEMINI_MODEL to avoid repeating it in every file.
model_name = os.getenv("GEMINI_MODEL")

if not model_name:
    raise ValueError(
        "GEMINI_MODEL is missing from .env. "
        "Add the exact Gemini model identifier currently working in your project."
    )

llm = LLM(
    model=model_name,
    api_key=api_key,
    temperature=0.2,
)


# --------------------------------------------------
# 2. Load and check existing outputs
# --------------------------------------------------

def load_json_file(file_path: Path) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {file_path}\n"
            "Run the preceding pipeline stages first."
        )

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_pipeline_outputs() -> dict:
    print("Loading pipeline outputs...")

    research_data = load_json_file(RESEARCH_FILE)
    analysis_data = load_json_file(ANALYSIS_FILE)
    strategy_data = load_json_file(STRATEGY_FILE)

    print("Research output loaded.")
    print("Analysis output loaded.")
    print("GTM strategy loaded.")

    return {
        "research": research_data,
        "analysis": analysis_data,
        "strategy": strategy_data,
    }


# --------------------------------------------------
# 3. Define the Head Planner Agent & Task from prompts/head_planner.yaml
# --------------------------------------------------

prompt_cfg = load_prompt_config("head_planner")

head_planner = Agent(
    role=prompt_cfg["agent"]["role"],
    goal=prompt_cfg["agent"]["goal"],
    backstory=prompt_cfg["agent"]["backstory"],
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

report_task = Task(
    description=prompt_cfg["task"]["description"],
    expected_output=prompt_cfg["task"]["expected_output"],
    agent=head_planner,
)


# --------------------------------------------------
# 5. Run the Head Planner
# --------------------------------------------------

def main():
    start_time = time.perf_counter()

    pipeline_data = load_pipeline_outputs()

    input_json = json.dumps(
        pipeline_data,
        ensure_ascii=False,
        indent=2,
    )

    print("\nStarting Head Planner Agent...")

    crew = Crew(
        agents=[head_planner],
        tasks=[report_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff(
        inputs={"pipeline_data": input_json}
    )

    report_content = result.raw.strip()
    report_content = report_content.replace("â‚¹", "₹")
    report_content = report_content.replace(
        "clandestine interview assistance",
        "real-time interview assistance",
    )

    if not report_content:
        raise ValueError("The Head Planner returned an empty report.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    REPORT_FILE.write_text(
        report_content + "\n",
        encoding="utf-8",
    )

    duration = time.perf_counter() - start_time

    record_agent_usage(
        agent_name="Head Planner Agent",
        model_name=llm.model,
        crew_output=result,
        duration_seconds=duration,
    )

    print("\n" + "=" * 50)
    print("HEAD PLANNER COMPLETED")
    print("=" * 50)
    print(f"Final report saved to: {REPORT_FILE}")
    print(f"Total duration: {duration:.2f} seconds")


if __name__ == "__main__":
    main()