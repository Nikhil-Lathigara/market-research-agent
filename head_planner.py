import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Process, Task


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
# 3. Define the Head Planner Agent
# --------------------------------------------------

head_planner = Agent(
    role="Head Planner and Market Research Report Editor",
    goal=(
        "Combine the research evidence, competitive analysis, and GTM strategy "
        "into a clear, consistent, evidence-based market research report."
    ),
    backstory=(
        "You are a senior market research lead responsible for reviewing "
        "the work of research analysts and GTM strategists. You turn their "
        "structured outputs into a decision-ready report for business leaders. "
        "You preserve source URLs, identify evidence limitations, distinguish "
        "verified findings from recommendations, and never invent facts."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False,
)


# --------------------------------------------------
# 4. Define the report-generation task
# --------------------------------------------------

report_task = Task(
    description="""
You are given three completed pipeline outputs:

1. Research evidence
2. Competitive and market analysis
3. Go-to-market strategy

INPUT DATA:
{pipeline_data}

Create a comprehensive, professional Markdown report.

Use the following sections:

# Market Research and Go-to-Market Plan

## 1. Executive Summary
Summarize the opportunity, important findings, and recommended direction.

## 2. Research Scope and Methodology
Explain the information available in the supplied research data.
Do not claim that additional research or verification occurred.

## 3. Market Research Findings
Summarize the main findings supported by the research evidence.

## 4. Competitor Landscape
Compare the identified competitors using the supplied analysis.
Include a comparison table where the available data supports one.

## 5. Competitive Pricing Analysis
Summarize pricing information.
Clearly label missing prices, estimates, and unavailable data.
Never invent a competitor's price.

## 6. SWOT Analysis
Present strengths, weaknesses, opportunities, and threats using the
available analysis. Do not present assumptions as verified facts.

## 7. Marketing Mix
Include the 4Ps or 7Ps available in the supplied analysis.
Do not invent missing components.

## 8. Ideal Customer Profiles
Summarize the target customer segments from the GTM strategy.

## 9. Positioning and Value Proposition
Present the recommended positioning, differentiators, and value proposition.

## 10. Messaging Strategy
Summarize the proposed messaging and supporting points.

## 11. Channel Strategy
Explain the recommended marketing and acquisition channels.

## 12. Launch Plan
Organize the proposed launch activities into phases.
Use only timelines and milestones supported by the strategy.
If timing is not provided, label any suggested sequencing as a recommendation.

## 13. KPIs and Experiments
Present the proposed success metrics and experiments.

## 14. Risks and Mitigations
Summarize the risks and corresponding mitigation plans.

## 15. Evidence and Source Register
Include source URLs from the research evidence.
Preserve the URLs exactly as provided.
Where possible, connect findings to their evidence IDs and sources.

## 16. Limitations and Items Requiring Verification
Identify missing information, unsupported claims, uncertain pricing,
and any important evidence gaps.

STRICT RULES:
- Treat the supplied JSON files as the source of truth for this report.
- Do not invent statistics, market sizes, competitor details, prices,
  citations, or source URLs.
- Preserve the distinction between facts, estimates, assumptions,
  and strategic recommendations.
- Keep source URLs attached to the findings they support wherever possible.
- If the inputs disagree, explicitly flag the disagreement instead of
  silently choosing one version.
- Do not claim that a URL is working or that a source is authoritative
  unless that information is established by the inputs.
- Do not expose API keys, environment variables, or secrets.
- Return the complete report in Markdown, without wrapping it in a code block.
""",
    expected_output=(
        "A complete Markdown market research and GTM report with the requested "
        "sections, evidence URLs, competitor comparisons, recommendations, "
        "and a clear limitations section."
    ),
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

    if not report_content:
        raise ValueError("The Head Planner returned an empty report.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    REPORT_FILE.write_text(
        report_content + "\n",
        encoding="utf-8",
    )

    duration = time.perf_counter() - start_time

    print("\n" + "=" * 50)
    print("HEAD PLANNER COMPLETED")
    print("=" * 50)
    print(f"Final report saved to: {REPORT_FILE}")
    print(f"Total duration: {duration:.2f} seconds")


if __name__ == "__main__":
    main()