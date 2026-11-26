# Market Research Agent — Project Progress

> **Purpose:** Keep the capstone aligned with its original objective: build and evaluate a multi-agent market research and go-to-market (GTM) planning system using CrewAI, n8n, and MCP. Update this file whenever a milestone is completed or the project scope changes.

## 1. Original project objective

Build a system that researches a market, analyzes competitors and opportunities, and produces an evidence-backed GTM plan.

### Required agents
1. **Head Planner** — coordinates the workflow and produces the final consolidated report.
2. **Research Agent** — gathers market and competitor evidence with source URLs/citations.
3. **Analyst Agent** — analyzes competitors, pricing, opportunities, and SWOT inputs.
4. **Strategy Agent** — creates ICPs, positioning, messaging, channel strategy, launch plan, pricing, risks, and measurement framework.

### Required implementation and evaluation
- Implement the workflow using **CrewAI** and **n8n**.
- Use MCP for tool connectivity where applicable.
- Produce structured research evidence and analysis outputs with traceable evidence IDs.
- Export a final report to Google Docs; PDF is optional if required.
- Include logging, retries, cost/latency tracking, and robust error handling.
- Test with mocked tools, scenario/golden-output tests, and a human evaluation rubric.
- Compare CrewAI and n8n implementations.

### Capstone success targets
- At least 90% of research questions answered with linked sources.
- At least 80% of citations from primary or high-quality sources.
- 0% broken links.
- End-to-end run under 15 minutes.
- Human evaluation score of at least 4/5.
- At least 80% factual consistency across repeated runs.
- Cost stays within the project budget/cap.

---

## 2. Current environment and project location

- **Project directory:** `C:\Projects\market-research-agent`
- **Environment/tooling:** Windows PowerShell, UV, Python 3.12
- **LLM:** `gemini/gemini-3.5-flash-lite` — confirmed working; retain unless there is a reason to change.
- **Search:** SerpAPI
- **Framework:** CrewAI
- **MCP:** MCP server and tool discovery have been tested.
- **Secrets:** `.env` contains API keys. Never commit or paste secrets. Keep `.env` in `.gitignore`.

## 3. Current project structure

```text
market-research-agent/
├── main.py
├── analyst.py
├── strategy.py
├── head_planner.py
├── run_pipeline.py
├── mcp_server.py
├── mcp_test.py
├── search_test.py
├── validate_research.py
├── validate_analysis.py
├── validate_strategy.py
├── quality_evaluation.py
├── .env
├── pyproject.toml
├── uv.lock
├── tools/
│   └── search_tool.py
├── tests/
│   └── validate_strategy.py
├── logs/
│   └── pipeline.log
└── outputs/
    ├── research_evidence.json
    ├── analysis_report.json
    ├── gtm_strategy.json
    ├── final_market_research_report.md
    └── quality_report.json
```

> Note: Validators have been moved/are being run from `tests/`. Ensure paths are resolved from the project root with `Path(__file__).resolve().parent.parent` when a script is inside `tests/`.

## 4. Completed milestones

### Environment and integrations
- [x] UV/Python environment set up and Gemini API connection works.
- [x] Standalone SerpAPI search test works.
- [x] Custom CrewAI SerpAPI search tool works.
- [x] MCP server starts and tool discovery works.

### CrewAI pipeline
- [x] Research Agent generates `outputs/research_evidence.json`.
- [x] Analyst Agent generates `outputs/analysis_report.json`.
- [x] Strategy Agent generates `outputs/gtm_strategy.json`.
- [x] Head Planner generates `outputs/final_market_research_report.md`.
- [x] `run_pipeline.py` runs the four stages sequentially and checks output existence, freshness/non-empty content, and JSON parseability where applicable.
- [x] One successful full pipeline run completed in approximately 103 seconds:
  - Research: ~49.92 seconds
  - Analyst: ~16.01 seconds
  - Strategy: ~18.28 seconds
  - Head Planner: ~18.94 seconds
- [x] Pipeline runtime is currently below the 15-minute target.

### Quality checks
- [x] Research validator previously passed: 3 research questions, 3 competitors, 8 evidence records, 0 evidence records without URLs, and 0 broken evidence references (at that run).
- [x] Analyst validator previously passed: 3 competitors analyzed, 3 pricing records, 2 market opportunities, 8 evidence IDs referenced, and 0 invalid evidence IDs (at that run).
- [x] Quality evaluator checks URL coverage, URL reachability, evidence references, and required final-report headings.
- [x] Latest reported quality evaluation: 100% evidence URL coverage and 100% URL reachability.
- [x] Strategy structural validator passed:
  - Required sections: 12/12
  - SWOT categories: 4
  - 7P elements: 7
  - Launch phases: 4
  - KPI stages: 6
  - Evidence IDs referenced: 9
  - Invalid evidence IDs: 0
  - Structural errors: 0
  - Metadata warnings: 0

## 5. Important quality caveats

Passing structural validation does **not** prove that the claims are factually correct or adequately supported.

The latest Strategy output review identified these content risks to address:
- SWOT weaknesses included competitor characteristics; distinguish internal weaknesses from external threats/opportunities.
- Do not state proposed product capabilities (for example, Windows app support, unlimited practice, live transcription, or free-credit counts) as existing features unless verified. Label them as **proposed** or **currently available**.
- Label pricing, conversion, and retention targets as provisional assumptions unless backed by evidence.
- Verify claim-to-source support, not merely the existence of evidence IDs.
- Testimonials and other social proof must be real, consented user feedback; otherwise describe them as future activities after collection.

Quality evaluator caveat:
- URL coverage means a URL was detected.
- URL reachability means the automated HTTP check succeeded under its configured status threshold.
- Neither metric proves source authority or factual support. Some sites may block automated requests.

## 6. Current milestone / next step

**Current: Analyst validation passed; final content refinements remain.**

The Analyst stage has had a structural validator pass in an earlier run, but the next task is a content-level audit of the current `outputs/analysis_report.json`.

Review:
1. Competitor names and descriptions are supported by research evidence.
2. Pricing values, currency, billing periods, and plan comparisons are accurate and comparable.
3. Opportunities are derived from evidence rather than unsupported assumptions.
4. SWOT classification is logically correct (internal strengths/weaknesses vs external opportunities/threats).
5. Every referenced evidence ID exists in `research_evidence.json`.
6. Important analytical claims can be traced to relevant source URLs.
7. Assumptions and missing data are explicitly labelled rather than invented.

**To continue:** inspect the current `outputs/analysis_report.json` together with `outputs/research_evidence.json` and, if necessary, `analyst.py`. Do not invent missing source facts.

## 7. Remaining work checklist

### CrewAI quality and reliability
- [x] Regenerate Analyst output after improving SWOT, pricing, and evidence instructions.
- [x] Run `tests/validate_analysis.py`: 4 competitors, 4 pricing records, 2 opportunities, 9 evidence IDs, 0 invalid IDs.
- [x] Review regenerated Analyst output: SWOT internal strengths/weaknesses are left empty where product evidence is unavailable; secondary pricing is marked unverified.
- [ ] Correct the localized INR pricing opportunity classification from `evidence` to `inference` in `market_opportunities`.
- [ ] Ensure marketing-mix statements distinguish proposed capabilities from confirmed current product capabilities.
- [ ] Complete final Analyst content audit after these refinements.
- [ ] Re-run Research, Analyst, Strategy, and final report validators on the same fresh pipeline run.
- [ ] Measure research-question coverage (target ≥90%).
- [ ] Measure primary/high-quality source percentage (target ≥80%).
- [ ] Validate claim-level citation support.
- [ ] Add repeated-run factual consistency evaluation (target ≥80%).
- [ ] Add unit tests with mocked search/tool responses.
- [ ] Add scenario tests with golden/reference outputs.
- [ ] Add human evaluation rubric and record scores (target ≥4/5).
- [ ] Demonstrate retries and failure handling.
- [ ] Track token/API usage or estimated cost and per-stage latency.
- [ ] Confirm zero broken links on the final evidence set.
- [ ] Keep total run under 15 minutes and cost within the defined cap.

### n8n implementation and comparison
- [ ] Build the equivalent n8n workflow.
- [ ] Export and retain the n8n workflow JSON.
- [ ] Test the n8n workflow with the same scenarios/inputs where possible.
- [ ] Compare CrewAI vs n8n on output quality, reliability, latency, cost, maintainability, and observability.

### Deliverables and documentation
- [ ] Sample Google Doc export.
- [ ] Optional PDF export if required.
- [ ] CrewAI chatbot screenshots.
- [ ] README with architecture, setup, environment variables, run instructions, tests, and known limitations.
- [ ] Final project report and evaluation results.

## 8. Working rules to keep the project on track

1. Preserve the original capstone objective and required deliverables; do not drift into unrelated features.
2. Finish and evaluate the CrewAI implementation before expanding the n8n implementation.
3. Make one focused change at a time, then run the relevant validator or test.
4. Do not delete or restructure project files without explicit approval.
5. Keep API keys and `.env` values private.
6. Use the configured Gemini model `gemini/gemini-3.5-flash-lite` unless a measured issue justifies a change.
7. Treat generated claims as unverified until supported by research evidence.
8. Update this file after each meaningful milestone, recording what passed, what failed, and the next concrete action.

---

## 9. Latest known status

**CrewAI pipeline:** operational  
**Strategy structural validation:** passed  
**Quality evaluator:** basic URL/evidence/report checks operational  
**Current focus:** Final Analyst content refinements, then end-to-end CrewAI validation  
**Next major phase:** finish Analyst content refinements, complete CrewAI evaluation, then implement and compare n8n


## 10. Progress update — 2026-11-17

### Analyst Agent checkpoint
- Updated `analyst.py` task instructions to improve SWOT classification, pricing evidence standards, and claim/evidence discipline.
- Regenerated `outputs/analysis_report.json`.
- Basic Analyst validator passed:
  - Competitors analyzed: 4
  - Pricing records: 4
  - Market opportunities: 2
  - Evidence IDs referenced: 9
  - Invalid evidence IDs: 0
- Content review confirms the SWOT no longer treats competitor capabilities/pricing as internal strengths or weaknesses; internal SWOT arrays are empty where product-specific evidence is unavailable.
- Secondary-source pricing for Hello Interview and Final Round AI is marked `unverified`.
- Remaining content refinements:
  1. Change localized INR pricing opportunity type from `evidence` to `inference` in `market_opportunities`, consistent with the SWOT classification.
  2. Clearly label web/desktop delivery, real-time support, and mock-feedback capabilities as proposed unless confirmed as current product capabilities.
  3. Replace the phrase "price sensitivity metering" with "price sensitivity testing".
- The source evidence mix in the current research file is 6 primary and 3 secondary records (66.7% primary). The capstone target is at least 80% primary or high-quality sources; high-quality secondary sources may count only if the evaluation rubric explicitly defines them as such.
- Important upstream issue remains: `research_timestamp` and `analysis_timestamp` in the research file show `2026-03-31`, while run metadata is from November 2026. Fix timestamp generation in the Research Agent after the Analyst refinements.


## 11. Research Agent run checkpoint — 2026-11-17

### Latest run results
- Research Agent completed successfully in 85.25 seconds.
- Generated `outputs/research_evidence.json`.
- Python now overwrites `research_timestamp` with the actual UTC run timestamp.
- Automated metrics from this run:
  - Evidence records: 5
  - Primary sources: 5
  - High-quality source classifications: 5
  - Primary-or-high-quality percentage: 100%
  - Research questions: 3/3 fully answered
  - Partially answered: 0
  - Unanswered: 0
  - Invalid evidence IDs: 0

### Content review findings — milestone not yet complete
- Competitor set changed from the earlier four (Hello Interview, CoPrep AI, Final Round AI, AceInterview) to two (HackerRank, AceInterview). Investigate this run-to-run inconsistency and consider using the prior competitor set as a seed list, while allowing new discoveries.
- HackerRank may be an adjacent competitor rather than a directly comparable candidate-preparation subscription. Establish the buyer/user segment for the product and pricing plan before comparing it with candidate-focused tools.
- HackerRank evidence E004 reports $79/month or $948 annually for AI-assisted evaluation, but the supplied retrieved text does not establish the exact plan scope or whether it is for individual candidates versus hiring teams.
- Five evidence records are a small evidence base for the market comparison. Gather more distinct, relevant evidence where available; do not fabricate evidence to hit a numeric quota.
- The 100% source-quality result is based on model-assigned classifications and is not yet independently audited.
- The coverage metric currently counts partially answered questions as covered. Keep separate counts for fully answered, partially answered, and unanswered questions; report fully answered-with-evidence coverage against the capstone target.
- Need the actual `tests/validate_research.py` output for this latest run; the metrics printed by `main.py` are not a substitute for the standalone validator.

### Next action
Inspect `mcp_server.py` and the latest `tests/validate_research.py` output. Then refine competitor continuity, buyer-segment/pricing verification, evidence sufficiency, and independent source-quality checks before marking Research Agent quality complete.

## 12. MCP server and Research Agent review — 2026-11-22

### Latest standalone validator result
- `uv run python .\\tests\\validate_research.py` passed basic structural validation.
- Research questions: 3
- Competitors: 2
- Evidence records: 5
- Evidence without URLs: 0
- Broken evidence references: 0

### MCP server review
- `mcp_server.py` exposes `search_web`, `validate_url`, and `fetch_webpage`.
- Search currently returns up to 5 organic results.
- URL validation and webpage fetching reject local/private destinations.
- Redirects are not automatically followed. Keep this safe-by-default behavior; validate each redirect destination before fetching it.
- Important security caveat: resolving a hostname for validation and then letting the HTTP client resolve it again is not a complete defense against DNS rebinding. Treat the current checks as a basic safeguard, not production-grade SSRF protection.

### Research consistency issue
- Earlier research included Hello Interview, CoPrep AI, Final Round AI, and AceInterview.
- Latest research included HackerRank and AceInterview only.
- Next improvement: seed the four previously identified competitors in `main.py`, require the agent to investigate each, allow new evidence-backed discoveries, and distinguish candidate-facing direct competitors from employer/hiring-team assessment platforms.
- Do not force inclusion of a competitor when its relevance or existence cannot be verified; record the limitation instead.
- Do not compare B2B hiring-team prices with B2C candidate subscription prices.

### Current status
- Research basic structural validation: passed.
- Research content quality and repeatability: still under review.
- Primary/high-quality source percentage from the latest run: 100% model-classified, not independently audited.
- Fully answered research questions: 3/3 in latest run.
- Latest research runtime: 85.25 seconds.

### Next action
Apply competitor continuity instructions in `main.py` and `research_task`, rerun research, and inspect competitor coverage and evidence. Then independently audit whether each source supports its claim. Do not mark the Research Agent milestone complete based only on automated percentages.

## 13. Full pipeline and stage validation — 2026-11-22

### End-to-end pipeline
- `run_pipeline.py` completed successfully.
- Research Agent: 59.99 seconds.
- Analyst Agent: 14.83 seconds.
- Strategy Agent: 25.91 seconds.
- Head Planner Agent: 19.15 seconds.
- Total pipeline duration: 119.92 seconds (~2 minutes), within the <15-minute target.
- Final report generated at `outputs/final_market_research_report.md`.

### Latest stage validator results
- Research: 3 questions, 4 competitors, 8 evidence records, 0 evidence records without URLs, 0 broken evidence references. Passed.
- Analyst: 4 competitors, 4 pricing records, 3 market opportunities, 7 evidence IDs referenced, 0 invalid IDs. Passed.
- Strategy: 12/12 required sections, 4 SWOT categories, 7P elements, 4 launch phases, 6 KPI stages, 8 evidence IDs referenced, 0 invalid IDs. Passed.
- Quality evaluator: 8 evidence records, 8 URLs present, 8 unique evidence IDs, 0 duplicates, 7 valid Analyst references, 8 valid Strategy references, 0 missing report headings, 6 unique URLs checked, 6 reachable.

### Interpretation / caveats
- Structural validation and end-to-end execution are now passing.
- URL reachability does not establish factual accuracy, source authority, or claim-to-source support.
- The latest run has 8 evidence records (rather than 12 in an earlier run); current stage validators confirm the current references resolve, but repeat-run consistency still needs testing.
- Final report has a known rupee-symbol encoding issue (`â‚¹`) and awkward phrase “clandestine interview assistance”; record these for final report polish. Do not change pricing research now.

### Next milestone
- Build automated tests and evaluation: mock tool tests, evidence/claim validation, repeat-run consistency, and human rubric.
- Then implement the n8n version and compare it with CrewAI.
- Preserve current architecture and outputs; do not delete or restructure files without approval.


---

## 14. CrewAI Capstone Completion Update — 2026-11-25

### Requirement Status Summary

| Requirement | Status | Notes |
| :--- | :--- | :--- |
| Four-agent CrewAI pipeline (`main.py`, `analyst.py`, `strategy.py`, `head_planner.py`) | **Complete** | Preserved existing architecture and `gemini/gemini-3.5-flash-lite` model |
| Pipeline retries & exponential backoff (`run_pipeline.py`) | **Complete** | `MAX_STAGE_ATTEMPTS=2`, `RETRY_BASE_DELAY=2`, permanent config error skip, freshness & JSON checks |
| Token usage & API cost tracking (`tools/usage_tracker.py`, `pricing_config.json`) | **Complete** | Captures `CrewOutput.token_usage`, writes `outputs/usage_report.json`, checks budget threshold |
| Scenario tests & reproducibility (`tools/scenario_evaluator.py`) | **Complete** | 3 fixed briefs, golden-output checks, normalized repeat-run consistency (`outputs/scenario_test_report.json`) |
| Google Docs export (`export_docs.py`, `outputs/export_report.json`) | **Blocked (Missing OAuth Credentials)** | Implemented with graceful skip and setup instructions when `credentials/google_oauth_client.json` is absent |
| CrewAI chatbot demo (`app.py`) | **Complete (Screenshots Pending Interactive Launch)** | Streamlit UI reusing `run_pipeline.py` with custom brief input, stage progress, token/cost metrics, and file downloads |
| Project documentation (`README.md`) | **Complete** | 20-section guide with PowerShell commands, setup, architecture, troubleshooting, and evaluation methodology |
| n8n workflow & CrewAI vs. n8n comparison | **Pending** | Next phase after CrewAI sign-off |

### Files Created
- `pricing_config.json`
- `tools/usage_tracker.py`
- `tools/scenario_evaluator.py`
- `outputs/scenario_test_report.json`
- `outputs/export_report.json`
- `export_docs.py`
- `app.py`
- `screenshots/.gitkeep`
- `tests/test_pipeline_retries.py`
- `tests/test_usage_tracker.py`
- `tests/test_scenarios.py`
- `tests/test_export_docs.py`

### Files Modified
- `run_pipeline.py` (retries, exponential backoff, exit status, usage report init & budget warning)
- `main.py` (`MARKET_BRIEF_OVERRIDE` support + `record_agent_usage`)
- `analyst.py` (`record_agent_usage`)
- `strategy.py` (`record_agent_usage`)
- `head_planner.py` (`record_agent_usage` + rupee symbol/wording sanitization)
- `README.md` (full documentation)
- `progress.md` (this update)
