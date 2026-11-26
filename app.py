import json
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
LOG_FILE = BASE_DIR / "logs" / "pipeline.log"

DEFAULT_BRIEF = (
    "Research AI-powered interview preparation platforms for software "
    "developers in India. Investigate Hello Interview, CoPrep AI, "
    "Final Round AI, and AceInterview (MockAI)."
)

STAGE_FILES = [
    ("1. Research Agent", OUTPUT_DIR / "research_evidence.json"),
    ("2. Analyst Agent", OUTPUT_DIR / "analysis_report.json"),
    ("3. Strategy Agent", OUTPUT_DIR / "gtm_strategy.json"),
    ("4. Head Planner Agent", OUTPUT_DIR / "final_market_research_report.md"),
]


def load_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def main() -> None:
    st.set_page_config(
        page_title="Market Research & GTM Agent",
        page_icon="📊",
        layout="wide",
    )

    st.title("Multi-Agent Market Research & GTM Planner (CrewAI)")
    st.caption(
        "Reuses the 4-agent CrewAI pipeline (Research → Analyst → Strategy → Head Planner) "
        "with MCP/SerpAPI tools, retries, and token/cost tracking."
    )

    with st.sidebar:
        st.header("Pipeline Controls")
        brief = st.text_area(
            "Market Research Brief",
            value=DEFAULT_BRIEF,
            height=180,
        )
        run_clicked = st.button("Run Full Pipeline", type="primary", width="stretch")

        st.divider()
        st.subheader("Stage Outputs")
        for label, path in STAGE_FILES:
            status_icon = "✅" if path.exists() else "⏳"
            st.write(f"{status_icon} {label}")

    if run_clicked:
        if not brief.strip():
            st.error("Please enter a market research brief before running the pipeline.")
        else:
            env = os.environ.copy()
            env["MARKET_BRIEF_OVERRIDE"] = brief.strip()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUNBUFFERED"] = "1"

            st.info("Running CrewAI pipeline via `run_pipeline.py`...")
            progress_bar = st.progress(0, text="Starting pipeline...")
            log_placeholder = st.empty()

            try:
                process = subprocess.Popen(
                    [sys.executable, str(BASE_DIR / "run_pipeline.py")],
                    cwd=str(BASE_DIR),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                collected_lines = []
                completed_stages = 0
                assert process.stdout is not None
                for line in process.stdout:
                    collected_lines.append(line.rstrip())
                    if "Output verified:" in line:
                        completed_stages = min(completed_stages + 1, 4)
                        progress_bar.progress(
                            int((completed_stages / 4) * 100),
                            text=f"Completed {completed_stages}/4 stages...",
                        )
                    log_placeholder.code("\n".join(collected_lines[-25:]), language="text")

                return_code = process.wait()
                if return_code == 0:
                    progress_bar.progress(100, text="Pipeline completed successfully!")
                    st.success("Pipeline finished successfully.")
                else:
                    st.error(f"Pipeline failed with exit code {return_code}. Check logs/pipeline.log for details.")
            except Exception as exc:
                st.error(f"Error launching pipeline: {exc}")

    # Display Metrics & Token Usage
    usage_data = load_json_safe(OUTPUT_DIR / "usage_report.json")
    if usage_data:
        st.subheader("Token Usage & Cost Summary")
        totals = usage_data.get("totals", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Tokens", f"{totals.get('total_tokens', 0):,}")
        c2.metric("Prompt Tokens", f"{totals.get('prompt_tokens', 0):,}")
        c3.metric("Completion Tokens", f"{totals.get('completion_tokens', 0):,}")
        c4.metric("Est. Cost (USD)", f"${totals.get('estimated_cost_usd', 0.0):.6f}")

        if usage_data.get("budget_exceeded"):
            st.warning(
                f"Estimated cost exceeded configured budget limit "
                f"(${usage_data.get('budget_limit_usd', 0.0):.4f})."
            )

        agents = usage_data.get("agents", {})
        if agents:
            st.dataframe(list(agents.values()), width="stretch")

    # Display Final Report & Output Files
    tab_report, tab_files, tab_logs = st.tabs(["Final Report", "Generated Output Files", "Pipeline Logs"])

    with tab_report:
        report_path = OUTPUT_DIR / "final_market_research_report.md"
        if report_path.exists():
            report_text = report_path.read_text(encoding="utf-8")
            st.download_button(
                "Download Final Report (.md)",
                data=report_text,
                file_name="final_market_research_report.md",
                mime="text/markdown",
            )
            st.markdown(report_text)
        else:
            st.info("No final report found yet. Run the pipeline to generate one.")

    with tab_files:
        output_files = sorted(OUTPUT_DIR.glob("*")) if OUTPUT_DIR.exists() else []
        if not output_files:
            st.info("No output files found in outputs/.")
        else:
            selected_name = st.selectbox("Select an output file", [f.name for f in output_files])
            selected_path = OUTPUT_DIR / selected_name
            content = selected_path.read_text(encoding="utf-8", errors="replace")
            st.download_button(
                f"Download {selected_name}",
                data=content,
                file_name=selected_name,
            )
            if selected_path.suffix == ".json":
                st.json(load_json_safe(selected_path) or {})
            else:
                st.text(content)

    with tab_logs:
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            st.code("\n".join(lines[-80:]), language="text")
        else:
            st.info("No pipeline logs found yet.")


if __name__ == "__main__":
    main()
