import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

INPUT_FILE = OUTPUT_DIR / "research_evidence.json"
OUTPUT_FILE = OUTPUT_DIR / "analysis_report.json"
RAW_OUTPUT_FILE = OUTPUT_DIR / "analysis_raw.txt"

OUTPUT_DIR.mkdir(exist_ok=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Research file not found: {INPUT_FILE}. "
        "Run main.py first."
    )

research_data = json.loads(
    INPUT_FILE.read_text(encoding="utf-8")
)

research_json = json.dumps(
    research_data,
    ensure_ascii=False,
    indent=2,
)

llm = LLM(
    model="gemini/gemini-3.5-flash-lite",
    api_key=api_key,
    temperature=0.2,
)

# --------------------------------------------------
# 2. Analyst Agent
# --------------------------------------------------

analyst_agent = Agent(
    role="Market Intelligence Analyst",
    goal=(
        "Transform research evidence into a traceable competitor "
        "analysis and actionable market insights."
    ),
    backstory=(
        "You are a market intelligence analyst specializing in "
        "competitive positioning, product strategy, pricing analysis, "
        "SWOT, and marketing frameworks. You distinguish verified "
        "facts from analytical inferences and never invent evidence."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False,
    max_iter=8,
)

# --------------------------------------------------
# 3. Analysis Task
# --------------------------------------------------

analysis_task = Task(
    description="""
Analyze the supplied market research JSON.

RESEARCH DATA:
{research_data}

YOUR RESPONSIBILITIES

1. COMPETITOR COMPARISON

- Compare all competitors using only supplied research.
- Include target users, features, differentiators and pricing.
- Every factual competitor claim must reference relevant evidence IDs.
- Do not invent features, customer numbers, market share or capabilities.
- If information is unavailable, write "unknown".
- Preserve the distinction between verified facts and inferences.

2. PRICING MATRIX

For every competitor, provide:
- Competitor name
- Pricing description
- Currency
- Pricing source URL
- Verification status
- Supporting evidence IDs

Rules:
- Preserve the original price, billing period and plan details.
- Never infer a price from incomplete information.
- Do not infer credit quantities from subscription prices.
- Do not describe secondary-source pricing as independently verified.
- Use "verified" only when the supplied evidence directly supports
  the pricing claim through a primary source.
- Use "unverified" when pricing is based on secondary sources or
  incomplete evidence.
- Use "unknown" when pricing cannot be established.
- Do not treat unknown pricing as free.

Specific evidence cautions:
- CoPrep AI evidence E002 supports a $29 Starter plan.
  Do not add 150 credits unless the supplied evidence explicitly
  establishes that quantity.
- CoPrep AI evidence E007 supports 20 free credits.
- Hello Interview evidence E006 is secondary-source evidence.
  Treat its pricing as unverified.
- Final Round AI evidence E005 is secondary-source evidence.
  Treat its pricing as unverified.
- AceInterview pricing is unknown unless new evidence is supplied.

3. SWOT ANALYSIS

Build a SWOT for the proposed market offering, not a list of
competitor characteristics.

STRENGTHS:
- Internal advantages of the proposed product.
- Only include established product capabilities or resources
  when the supplied research establishes them.
- Do not claim competitor capabilities as our strengths.

WEAKNESSES:
- Internal limitations of the proposed product.
- Do not classify competitor pricing or competitor limitations
  as our own weaknesses.
- If product-specific information is unavailable, return an
  empty array rather than inventing weaknesses.

OPPORTUNITIES:
- External market gaps and potential areas for differentiation.
- Clearly distinguish evidence-backed findings from hypotheses.
- Localized INR pricing may be an opportunity, but do not claim
  proven willingness to pay without supporting research.

THREATS:
- External competitive, market and technology risks.
- Competitor capabilities, established brands and pricing pressure
  can be considered here when supported by evidence.

For each SWOT item:
- Include finding.
- Include type: "evidence" or "inference".
- Include relevant evidence IDs.
- Never invent evidence IDs.
- An inference must not be represented as a verified fact.

4. MARKETING MIX

Analyze all 7Ps.

4P:
- Product
- Price
- Place
- Promotion

Additional 3P:
- People
- Process
- Physical Evidence

Distinguish current market observations from proposed
recommendations. Do not claim that our proposed product already
has features, customers, testimonials, partnerships or applications
that have not been established.

5. MARKET OPPORTUNITIES

For each opportunity:
- Provide a descriptive title.
- Explain the reasoning.
- Set type to "evidence" or "inference".
- Include supporting evidence IDs.
- Include validation_needed actions.

Potential opportunities may include:
- Localized INR pricing.
- Credit-based pricing.
- Preparation paths for Indian service companies.
- Preparation paths for Indian product companies.
- If an opportunity is a hypothesis derived from secondary research,
  classify it as "inference", not "evidence".
- Use "evidence" only when the supplied sources directly establish
  the opportunity being claimed.

- Clearly label proposed product capabilities as proposed.
- Never imply that proposed capabilities are already implemented.
These are hypotheses unless the supplied evidence establishes
actual demand.

6. RESEARCH QUALITY

Identify:
- Missing primary sources.
- Incomplete competitor pricing.
- Missing Indian market data.
- Claims supported only by secondary sources.
- Missing customer demand and willingness-to-pay evidence.

Do not assume that a URL is reliable merely because it exists.

7. EVIDENCE RULES

- Use only evidence IDs from the supplied evidence collection.
- Every factual competitor claim must reference relevant evidence.
- Do not attach an unrelated evidence ID just to support an inference.
- If no relevant evidence exists, use an empty evidence_ids array.
- Clearly distinguish primary and secondary sources.
- A source's existence does not prove that it supports a claim.
- Do not claim independent source verification unless established
  by the supplied evidence.

OUTPUT FORMAT

Return one valid JSON object with this structure:

{
  "analysis_timestamp": "ISO 8601 timestamp",
  "market": "string",
  "competitor_comparison": [
    {
      "competitor": "string",
      "target_users": "string or unknown",
      "key_features": ["string"],
      "pricing": "string or unknown",
      "differentiators": ["string"],
      "evidence_ids": ["E001"],
      "limitations": ["string"]
    }
  ],
  "pricing_matrix": [
    {
      "competitor": "string",
      "pricing_description": "string or unknown",
      "currency": "string or unknown",
      "pricing_source": "URL or null",
      "verification_status": "verified or unverified or unknown",
      "evidence_ids": ["E001"]
    }
  ],
  "swot_analysis": {
    "strengths": [
      {
        "finding": "string",
        "type": "evidence or inference",
        "evidence_ids": ["E001"]
      }
    ],
    "weaknesses": [],
    "opportunities": [],
    "threats": []
  },
  "marketing_mix_4p": {
    "product": "string",
    "price": "string",
    "place": "string",
    "promotion": "string"
  },
  "marketing_mix_7p": {
    "people": "string",
    "process": "string",
    "physical_evidence": "string"
  },
  "market_opportunities": [
    {
      "opportunity": "string",
      "reasoning": "string",
      "type": "evidence or inference",
      "evidence_ids": ["E001"],
      "validation_needed": ["string"]
    }
  ],
  "research_gaps": ["string"],
  "limitations": ["string"]
}

IMPORTANT:
- Return JSON only.
- Do not include Markdown fences.
- Do not invent information to fill empty sections.
- Preserve all four competitors when they are present in research.
- Empty arrays are acceptable when evidence is insufficient.
""",
    expected_output=(
        "A valid JSON analysis report containing competitor comparison, "
        "pricing matrix, SWOT, 4P/7P analysis, market opportunities, "
        "research gaps, and evidence references."
    ),
    agent=analyst_agent,
)

def validate_evidence_references(report, research):
    valid_ids = {
        item["evidence_id"]
        for item in research.get("evidence", [])
        if item.get("evidence_id")
    }

    referenced_ids = set()

    def collect_ids(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "evidence_ids" and isinstance(item, list):
                    referenced_ids.update(item)
                else:
                    collect_ids(item)

        elif isinstance(value, list):
            for item in value:
                collect_ids(item)

    collect_ids(report)

    invalid_ids = referenced_ids - valid_ids

    if invalid_ids:
        raise ValueError(
            f"Invalid evidence IDs: {sorted(invalid_ids)}"
        )

    print(f"Valid evidence IDs: {len(referenced_ids)}")
    print("Invalid evidence IDs: 0")

# --------------------------------------------------
# 4. Execute analysis
# --------------------------------------------------

start_time = time.perf_counter()

crew = Crew(
    agents=[analyst_agent],
    tasks=[analysis_task],
    process=Process.sequential,
    verbose=True,
)

result = crew.kickoff(
    inputs={"research_data": research_json}
)

duration_seconds = round(
    time.perf_counter() - start_time,
    2,
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
# 5. Save analysis
# --------------------------------------------------

try:
    report = json.loads(json_text)
    
    validate_evidence_references(report, research_data)

    # Generate one authoritative timestamp for this run.
    generated_at = datetime.now(timezone.utc).isoformat()

    # Do not trust the timestamp generated by the LLM.
    report["analysis_timestamp"] = generated_at

    report["run_metadata"] = {
        "generated_at": generated_at,
        "duration_seconds": duration_seconds,
        "model": "gemini/gemini-3.5-flash-lite",
        "input_file": str(INPUT_FILE),
    }
    OUTPUT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\nAnalysis saved to: {OUTPUT_FILE}")

except json.JSONDecodeError:
    RAW_OUTPUT_FILE.write_text(
        raw_output,
        encoding="utf-8",
    )

    print("\nThe model did not return valid JSON.")
    print(f"Raw output saved to: {RAW_OUTPUT_FILE}")

print(f"Analysis duration: {duration_seconds} seconds")
print("Analyst Agent finished.")