# Multi-Agent Market Research & Go-to-Market (GTM) Planning System

A multi-agent market research and Go-to-Market (GTM) planning system built with **CrewAI**, **Gemini**, **SerpAPI**, and **MCP (Model Context Protocol)**, managed with **UV** on Windows PowerShell.

---

## 1. Project Overview

This system automates competitive market research, pricing analysis, SWOT/7P synthesis, and GTM strategy drafting for a given market brief. It produces structured JSON artifacts with traceable `evidence_id` references and compiles a decision-ready Markdown report (with optional Google Docs / PDF export).

## 2. Problem Statement

Product teams often spend days manually collecting sources, comparing competitors, and drafting GTM strategy documents—a process that is slow, error-prone, and inconsistent across research cycles. This project addresses those gaps through a four-agent automated pipeline with structural validation, evidence traceability, retry reliability, and token/cost observability.

## 3. System Architecture

The pipeline executes four sequential CrewAI stages orchestrated by `run_pipeline.py`:

```text
Market Brief
   │
   ▼
[1] Research Agent (main.py) ──► MCP Server (mcp_server.py: search_web, fetch_webpage, validate_url)
   │                                  └─► outputs/research_evidence.json
   ▼
[2] Analyst Agent (analyst.py) ──────► outputs/analysis_report.json
   │
   ▼
[3] Strategy Agent (strategy.py) ────► outputs/gtm_strategy.json
   │
   ▼
[4] Head Planner Agent (head_planner.py) ─► outputs/final_market_research_report.md
                                               ├─► quality_evaluation.py ─► outputs/quality_report.json
                                               ├─► tools/usage_tracker.py ─► outputs/usage_report.json
                                               └─► export_docs.py ─► Google Docs / outputs/export_report.json
```

## 4. Four Agent Responsibilities

1. **Research Agent (`main.py`):** Conducts web discovery via the MCP server (`SerpAPI` + webpage fetching + URL validation) and outputs `outputs/research_evidence.json` with source URLs and `evidence_id` records.
2. **Analyst Agent (`analyst.py`):** Synthesizes competitor comparisons, pricing matrices (marking `verified`, `unverified`, or `unknown`), SWOT analysis, 4P/7P marketing mix, and market opportunities into `outputs/analysis_report.json`.
3. **Strategy Agent (`strategy.py`):** Produces ICPs, positioning, messaging framework, channel strategy, SWOT, 7Ps, launch plan, KPIs, experiments, and risk mitigations in `outputs/gtm_strategy.json`.
4. **Head Planner Agent (`head_planner.py`):** Consolidates all three JSON outputs into a structured, executive-ready Markdown report at `outputs/final_market_research_report.md`.

## 5. Technology Stack

- **Language & Packaging:** Python 3.12+, `uv`
- **Multi-Agent Framework:** CrewAI (`crewai[google-genai]`, `crewai-tools[mcp]`)
- **LLM:** Google Gemini (`gemini/gemini-3.5-flash-lite`)
- **Search & Scraping:** SerpAPI, `httpx`, `beautifulsoup4`
- **Tool Protocol:** Model Context Protocol (`mcp[cli]`)
- **UI Demo:** Streamlit (`app.py`)
- **Testing:** `pytest`

## 6. Project Folder Structure

```text
market-research-agent/
├── app.py                              # Streamlit chatbot/pipeline demo UI
├── main.py                             # Research Agent (MCP + SerpAPI)
├── analyst.py                          # Analyst Agent
├── strategy.py                         # Strategy Agent
├── head_planner.py                     # Head Planner Agent
├── run_pipeline.py                     # Sequential orchestrator with retries & backoff
├── mcp_server.py                       # FastMCP server (search_web, validate_url, fetch_webpage)
├── quality_evaluation.py               # URL reachability, evidence ID & heading evaluator
├── export_docs.py                      # Google Docs (+ optional PDF) exporter
├── pricing_config.json                 # Configurable LLM token pricing & budget cap
├── pyproject.toml                      # UV project dependencies
├── progress.md                         # Milestone & status tracking
├── prompts/                            # Agent & task YAML prompt configs
│   ├── research.yaml
│   ├── analyst.yaml
│   ├── strategy.yaml
│   └── head_planner.yaml
├── tools/
│   ├── search_tool.py                  # Standalone CrewAI SerpAPI tool
│   ├── usage_tracker.py                # Token usage & estimated cost tracker
│   └── scenario_evaluator.py           # Fixed-brief scenario & reproducibility evaluator
├── tests/
│   ├── test_search_tool.py
│   ├── test_pipeline_retries.py
│   ├── test_prompt_loader.py
│   ├── test_usage_tracker.py
│   ├── test_scenarios.py
│   ├── test_export_docs.py
│   ├── test_research_validation.py
│   ├── test_analysis_validation.py
│   ├── test_strategy_validation.py
│   ├── validate_research.py
│   ├── validate_analysis.py
│   └── validate_strategy.py
├── outputs/                            # Generated JSON/MD reports & evaluation artifacts
├── logs/                               # Pipeline execution logs (pipeline.log)
└── screenshots/                        # Streamlit demo screenshots
```

## 7. Installation Instructions

```powershell
# Clone or navigate to the project directory
cd C:\Projects\market-research-agent

# Sync dependencies using UV
uv sync
```

## 8. Environment Variable Configuration

Create a `.env` file in the project root (never commit `.env` to version control):

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini/gemini-3.5-flash-lite
SERPAPI_API_KEY=your_serpapi_api_key_here

# Optional overrides
MAX_STAGE_ATTEMPTS=2
RETRY_BASE_DELAY=2
PIPELINE_BUDGET_USD=1.00
GOOGLE_OAUTH_CLIENT_SECRETS_FILE=credentials/google_oauth_client.json
GOOGLE_OAUTH_TOKEN_FILE=credentials/google_token.json
```

## 9. Gemini Setup

1. Obtain an API key from Google AI Studio.
2. Set `GEMINI_API_KEY` and `GEMINI_MODEL=gemini/gemini-3.5-flash-lite` in `.env`.

## 10. SerpAPI Setup

1. Create a SerpAPI account and copy your API key.
2. Set `SERPAPI_API_KEY` in `.env`.

## 11. MCP Setup

The MCP server (`mcp_server.py`) is launched automatically over stdio by `main.py` via `MCPServerAdapter`. To test MCP tool discovery independently:

```powershell
uv run python tests\mcp_check.py
```

## 12. How to Run the Complete Pipeline

```powershell
uv run python run_pipeline.py
```

`run_pipeline.py` runs all 4 stages sequentially with configurable retries (`MAX_STAGE_ATTEMPTS=2`, exponential backoff `RETRY_BASE_DELAY=2`), validates output freshness and JSON integrity, tracks token usage, and logs to `logs/pipeline.log`.

To run quality evaluation afterwards:

```powershell
uv run python quality_evaluation.py
```

## 13. How to Run Automated Tests

```powershell
uv run pytest -v
```

To run scenario and reproducibility evaluation and generate `outputs/scenario_test_report.json`:

```powershell
uv run python -c "from tools.scenario_evaluator import evaluate_all_scenarios; print(evaluate_all_scenarios()['average_consistency_percent'])"
```

## 14. How to Launch the Chatbot

```powershell
uv run streamlit run app.py
```

Enter a custom market research brief in the sidebar, click **Run Full Pipeline**, monitor stage progress, inspect token usage/costs, and download generated outputs.

## 15. Google Docs Export Setup

1. In Google Cloud Console, enable the **Google Docs API** and **Google Drive API**.
2. Create an **OAuth 2.0 Client ID** (Desktop App) and download the JSON to `credentials/google_oauth_client.json`.
3. Run the export module:

```powershell
uv run python export_docs.py
```

If credentials are missing, `export_docs.py` skips gracefully, writes setup instructions to `outputs/export_report.json`, and does not block the core pipeline.

## 16. Token and Cost Tracking

- Each agent records provider-reported token usage (`CrewOutput.token_usage`) via `tools/usage_tracker.py` into `outputs/usage_report.json`.
- Estimated costs are computed from `pricing_config.json` (kept separate from agent prompts).
- If provider usage metadata is unavailable, `usage_available` is marked `false` with `null` counts—token counts are never fabricated or estimated from runtime.
- `run_pipeline.py` logs a warning if estimated cost exceeds `PIPELINE_BUDGET_USD` (or `budget_limit_usd` in `pricing_config.json`).

## 17. Output File Descriptions

| File | Description |
| :--- | :--- |
| `outputs/research_evidence.json` | Structured research questions, competitors, and cited evidence records |
| `outputs/analysis_report.json` | Competitor comparison, pricing matrix, SWOT, 4P/7P, and opportunities |
| `outputs/gtm_strategy.json` | ICPs, positioning, messaging, channels, launch plan, KPIs, and risks |
| `outputs/final_market_research_report.md` | Consolidated 16-section Markdown GTM report |
| `outputs/quality_report.json` | URL coverage, HTTP reachability, and evidence ID validation metrics |
| `outputs/usage_report.json` | Per-agent and total token usage, estimated cost, and budget status |
| `outputs/scenario_test_report.json` | Multi-scenario golden validation and repeat-run consistency metrics |
| `outputs/export_report.json` | Google Docs export status, document URL, and optional PDF path |

## 18. Known Limitations

- **LLM Nondeterminism:** Repeated live runs may vary in phrasing, optional opportunities, and search result ordering even at `temperature=0.2`.
- **URL Reachability vs. Claim Support:** Automated HTTP 200 checks confirm a URL is reachable, not that the page text supports the specific claim.
- **Secondary Pricing:** Competitor pricing from secondary sources is marked `unverified` unless confirmed on an official primary pricing page.
- **n8n Phase:** The n8n workflow implementation and CrewAI vs. n8n comparison are tracked as separate upcoming capstone phases.

## 19. Troubleshooting

- **`GEMINI_API_KEY is missing` / `SERPAPI_API_KEY is missing`:** Ensure `.env` exists in `C:\Projects\market-research-agent` with valid keys.
- **Stale output error in `run_pipeline.py`:** An agent failed before writing a fresh output file; check `logs/pipeline.log` and `outputs/*_raw.txt`.
- **CrewAI `PermissionError` on `secret.key` in restricted sandboxes:** Run `uv run pytest -v` in your normal Windows PowerShell session where `%LOCALAPPDATA%\crewai` is writable.

## 20. Evaluation Methodology

1. **Structural & Citation Validation:** `tests/validate_research.py`, `tests/validate_analysis.py`, `tests/validate_strategy.py`, and `quality_evaluation.py` verify required schemas, URL reachability, and `evidence_id` integrity.
2. **Scenario & Reproducibility Testing:** `tools/scenario_evaluator.py` evaluates 3 fixed briefs against controlled outputs and measures normalized factual consistency (target: ≥ 80%).
