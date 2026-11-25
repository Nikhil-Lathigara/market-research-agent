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
# 2. Strategy Agent
# --------------------------------------------------

strategy_agent = Agent(
    role="Go-to-Market Strategy Specialist",
    goal=(
        "Develop an actionable, differentiated go-to-market strategy "
        "grounded in supplied market research and competitive analysis."
    ),
    backstory=(
        "You are a product marketing and go-to-market strategist. "
        "You specialize in customer segmentation, positioning, "
        "messaging, channel planning, launch execution, and KPI design. "
        "You distinguish evidence from assumptions and do not invent "
        "market statistics or competitor facts."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False,
    max_iter=8,
)

# --------------------------------------------------
# 3. GTM Strategy Task
# --------------------------------------------------


strategy_task = Task(
    description="""
Create a comprehensive, practical Go-to-Market strategy using
the supplied research and competitor analysis JSON.

INPUT DATA:

{input_data}

IMPORTANT RULES:
- Use supplied research and analysis as factual evidence.
- Do not invent competitor facts, market statistics, prices or customer data.
- Distinguish facts, strategic inferences and assumptions.
- Include evidence IDs wherever factual claims are made.
- Every evidence ID must exist in the supplied research evidence collection.
- If information is unavailable, explicitly state the limitation.
- Proposed targets without supporting data must be labelled provisional.
- Recommendations must be actionable and relevant to the Indian market.

==================================================
1. IDEAL CUSTOMER PROFILES (ICPs)
==================================================

Identify meaningful customer segments.

For each segment include:
- Segment name
- Customer characteristics
- Needs and pain points
- Buying motivations
- Proposed value proposition
- Acquisition approach
- Evidence IDs
- Assumptions requiring validation

Avoid unsupported demographic and market-size claims.

==================================================
2. VALUE PROPOSITION AND POSITIONING
==================================================

Include:
- Core value proposition
- Positioning statement
- Differentiators
- Competitive alternatives
- Reasons customers might choose the product
- Evidence IDs
- Assumptions

Do not claim superiority without evidence.

==================================================
3. MESSAGING FRAMEWORK
==================================================

Include:
- Primary message
- At least three supporting messages
- Target audience for each message
- Call to action
- Evidence IDs
- Assumptions

Avoid unsupported employment, accuracy or performance guarantees.

==================================================
4. CHANNEL STRATEGY
==================================================

Evaluate relevant acquisition and distribution channels.

Consider, where appropriate:
- SEO and educational content
- Digital review and comparison websites
- LinkedIn and developer communities
- YouTube and technical demonstrations
- College and placement-cell partnerships
- Referral and affiliate programs
- Freemium and trial-credit onboarding
- Paid acquisition

Select channels based on the supplied research.
Do not include irrelevant channels merely to increase the count.

For each selected channel include:
- Channel
- Target audience
- Purpose
- Activities
- Funnel stage
- KPI
- Priority: high, medium or low
- Reasoning
- Evidence IDs
- Assumptions

Clearly label strategic hypotheses.

==================================================
5. SWOT ANALYSIS
==================================================

Produce a complete SWOT analysis.

Include four separate categories:

STRENGTHS:
Internal product or business advantages supported by the inputs.

WEAKNESSES:
Internal limitations, capability gaps or constraints.

OPPORTUNITIES:
External market opportunities supported by research or clearly
labelled strategic inferences.

THREATS:
External competition, market uncertainty and other relevant risks.

For every item include:
- Description
- Business implication
- Evidence IDs, if applicable
- Assumptions, if applicable

Do not present an unverified assumption as a proven fact.

==================================================
6. MARKETING MIX: 7Ps
==================================================

Create a complete 7P marketing mix.

Include:

1. Product:
   Product offering, core features and customer benefits.

2. Price:
   Proposed pricing approaches, competitor context and
   pricing validation requirements.

3. Place:
   Distribution, platform access and acquisition touchpoints.

4. Promotion:
   Content, campaigns, partnerships and promotional messaging.

5. People:
   Relevant customer support, product, marketing and
   operational responsibilities.

6. Process:
   User onboarding, mock interview experience, payment,
   feedback and retention processes.

7. Physical Evidence:
   Trust signals such as product demonstrations, testimonials,
   sample reports, reviews and website experience.

For each P include:
- Strategy
- Recommended activities
- Expected outcome
- Evidence IDs, if applicable
- Assumptions

Do not invent existing product features or customer testimonials.

==================================================
7. LAUNCH PLAN
==================================================

Create a phased launch roadmap with FOUR phases:

Phase 1: Foundation and Validation
Phase 2: Initial Launch and Acquisition
Phase 3: Conversion and Optimization
Phase 4: Growth and Retention

Adapt the phase activities to the actual product and market.

For each phase include:
- Phase name
- Duration
- Objective
- Activities
- Deliverables
- Success metrics
- Dependencies
- Risks
- Suggested owner or responsible function

Use relative timelines such as Weeks 1-2.

Do not invent launch dates, budgets or team commitments.

Label unsupported numerical targets as provisional.

==================================================
8. PRICING STRATEGY
==================================================

Include:
- Observed competitor pricing
- Pricing evidence and source limitations
- Potential pricing approaches
- INR localization considerations
- Subscription and credit-based options where relevant
- Willingness-to-pay experiments
- Unknowns
- Evidence IDs
- Assumptions

Never invent competitor pricing.

==================================================
9. MEASUREMENT FRAMEWORK
==================================================

Include KPIs for ALL SIX funnel stages:

1. Awareness
2. Acquisition
3. Activation
4. Engagement
5. Conversion
6. Retention

Provide at least one relevant KPI for each stage.

For each KPI include:
- KPI name
- Funnel stage
- Definition
- Measurement method
- Proposed target or baseline requirement
- Target basis: evidence_based or provisional
- Reasoning

Do not present provisional targets as actual performance.

==================================================
10. RISKS AND MITIGATIONS
==================================================

Include relevant risks involving:
- Competition
- Pricing and affordability
- Product-market fit
- Customer acquisition
- Product reliability
- Trust and user adoption
- Research uncertainty

For each include:
- Risk
- Impact
- Likelihood: high, medium or low
- Mitigation
- Evidence IDs, if applicable

==================================================
11. EXPERIMENTS
==================================================

Recommend actionable experiments.

For each include:
- Hypothesis
- Method
- Target segment
- Success criteria
- Metrics
- Assumptions

Prioritize experiments that validate important business uncertainties.

==================================================
12. EVIDENCE LIMITATIONS
==================================================

Document:
- Missing competitor information
- Unverified pricing
- Weak or secondary sources
- Research gaps
- Assumptions requiring primary research

==================================================
OUTPUT FORMAT
==================================================

Return ONE valid JSON object using this exact structure:

{
  "generated_at": "ISO 8601 timestamp",
  "market": "string",
  "executive_summary": "string",

  "ideal_customer_profiles": [
    {
      "segment": "string",
      "characteristics": ["string"],
      "pain_points": ["string"],
      "buying_motivations": ["string"],
      "value_proposition": "string",
      "acquisition_approach": ["string"],
      "evidence_ids": ["E001"],
      "assumptions": ["string"]
    }
  ],

  "positioning": {
    "value_proposition": "string",
    "positioning_statement": "string",
    "differentiators": ["string"],
    "competitive_alternatives": ["string"],
    "evidence_ids": ["E001"],
    "assumptions": ["string"]
  },

  "messaging_framework": {
    "primary_message": "string",
    "supporting_messages": [
      {
        "message": "string",
        "audience": "string",
        "call_to_action": "string",
        "evidence_ids": ["E001"],
        "assumptions": ["string"]
      }
    ]
  },

  "channel_strategy": [
    {
      "channel": "string",
      "target_audience": "string",
      "purpose": "string",
      "activities": ["string"],
      "funnel_stage": "string",
      "kpi": "string",
      "priority": "high, medium, or low",
      "reasoning": "string",
      "evidence_ids": ["E001"],
      "assumptions": ["string"]
    }
  ],

  "swot_analysis": {
    "strengths": [
      {
        "description": "string",
        "business_implication": "string",
        "evidence_ids": ["E001"],
        "assumptions": ["string"]
      }
    ],
    "weaknesses": [
      {
        "description": "string",
        "business_implication": "string",
        "evidence_ids": ["E001"],
        "assumptions": ["string"]
      }
    ],
    "opportunities": [
      {
        "description": "string",
        "business_implication": "string",
        "evidence_ids": ["E001"],
        "assumptions": ["string"]
      }
    ],
    "threats": [
      {
        "description": "string",
        "business_implication": "string",
        "evidence_ids": ["E001"],
        "assumptions": ["string"]
      }
    ]
  },

  "marketing_mix_7p": {
    "product": {
      "strategy": "string",
      "activities": ["string"],
      "expected_outcome": "string",
      "evidence_ids": ["E001"],
      "assumptions": ["string"]
    },
    "price": {
      "strategy": "string",
      "activities": ["string"],
      "expected_outcome": "string",
      "evidence_ids": ["E001"],
      "assumptions": ["string"]
    },
    "place": {
      "strategy": "string",
      "activities": ["string"],
      "expected_outcome": "string",
      "evidence_ids": ["E001"],
      "assumptions": ["string"]
    },
    "promotion": {
      "strategy": "string",
      "activities": ["string"],
      "expected_outcome": "string",
      "evidence_ids": ["E001"],
      "assumptions": ["string"]
    },
    "people": {
      "strategy": "string",
      "activities": ["string"],
      "expected_outcome": "string",
      "evidence_ids": ["E001"],
      "assumptions": ["string"]
    },
    "process": {
      "strategy": "string",
      "activities": ["string"],
      "expected_outcome": "string",
      "evidence_ids": ["E001"],
      "assumptions": ["string"]
    },
    "physical_evidence": {
      "strategy": "string",
      "activities": ["string"],
      "expected_outcome": "string",
      "evidence_ids": ["E001"],
      "assumptions": ["string"]
    }
  },

  "pricing_strategy": {
    "observed_competitor_pricing": ["string"],
    "potential_approaches": ["string"],
    "validation_experiments": ["string"],
    "unknowns": ["string"],
    "evidence_ids": ["E001"],
    "assumptions": ["string"]
  },

  "launch_plan": [
    {
      "phase": "string",
      "duration": "string",
      "objective": "string",
      "activities": ["string"],
      "deliverables": ["string"],
      "success_metrics": ["string"],
      "dependencies": ["string"],
      "risks": ["string"],
      "owner": "string"
    }
  ],

  "measurement_framework": [
    {
      "kpi": "string",
      "funnel_stage": "string",
      "definition": "string",
      "measurement_method": "string",
      "target": "string",
      "target_basis": "evidence_based or provisional",
      "reasoning": "string"
    }
  ],

  "risks_and_mitigations": [
    {
      "risk": "string",
      "impact": "string",
      "likelihood": "high, medium, or low",
      "mitigation": "string",
      "evidence_ids": ["E001"]
    }
  ],

  "experiments": [
    {
      "hypothesis": "string",
      "method": "string",
      "target_segment": "string",
      "success_criteria": "string",
      "metrics": ["string"],
      "assumptions": ["string"]
    }
  ],

  "evidence_limitations": ["string"]
}

Return JSON only.
Do not use Markdown fences.
Do not add commentary outside the JSON.
""",
    expected_output=(
        "A comprehensive, valid JSON GTM strategy including ICPs, "
        "positioning, messaging, channel strategy, SWOT, 7P marketing "
        "mix, pricing, four-phase launch plan, six-stage KPI framework, "
        "risks, experiments and evidence limitations."
    ),
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