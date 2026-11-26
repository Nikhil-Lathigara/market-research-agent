import os
import subprocess
import sys
import time
import json
from datetime import datetime
from pathlib import Path

from tools.usage_tracker import DEFAULT_USAGE_REPORT_PATH, init_usage_report


# --------------------------------------------------
# 1. Project configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
LOG_DIR = BASE_DIR / "logs"

LOG_FILE = LOG_DIR / "pipeline.log"

MAX_STAGE_ATTEMPTS = int(os.getenv("MAX_STAGE_ATTEMPTS", "2"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "2"))

NON_RETRYABLE_ERROR_MARKERS = (
    "GEMINI_API_KEY is missing",
    "GEMINI_MODEL is missing",
    "SERPAPI_API_KEY is missing",
)

PIPELINE_STAGES = [
    {
        "name": "Research Agent",
        "script": "main.py",
        "output": "research_evidence.json",
    },
    {
        "name": "Analyst Agent",
        "script": "analyst.py",
        "output": "analysis_report.json",
    },
    {
        "name": "Strategy Agent",
        "script": "strategy.py",
        "output": "gtm_strategy.json",
    },
    {
        "name": "Head Planner Agent",
        "script": "head_planner.py",
        "output": "final_market_research_report.md",
    },
]


def validate_stage_output(stage: dict, started_at: float) -> None:
    output_path = OUTPUT_DIR / stage["output"]

    if not output_path.exists():
        raise FileNotFoundError(
            f"Expected output not found: {output_path}"
        )

    if output_path.stat().st_mtime < started_at:
        raise RuntimeError(
            f"{stage['name']} did not produce a fresh output: "
            f"{output_path}"
        )

    if output_path.stat().st_size == 0:
        raise ValueError(
            f"{stage['name']} produced an empty output: {output_path}"
        )

    if output_path.suffix.lower() == ".json":
        try:
            with output_path.open("r", encoding="utf-8") as file:
                json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"{stage['name']} produced invalid JSON: {error}"
            ) from error

    log(f"Output validation passed: {output_path}")

# --------------------------------------------------
# 2. Logging
# --------------------------------------------------

def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"

    print(formatted_message)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(formatted_message + "\n")


def is_permanent_config_error(error: Exception) -> bool:
    """Return True for permanent configuration/setup errors that should not be retried."""
    if isinstance(error, (FileNotFoundError, PermissionError)):
        return True
    message = str(error)
    return any(marker in message for marker in NON_RETRYABLE_ERROR_MARKERS)


# --------------------------------------------------
# 3. Execute one pipeline stage
# --------------------------------------------------

def run_stage(
    stage: dict,
    max_attempts: int = MAX_STAGE_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY,
) -> float:
    name = stage["name"]
    script_path = BASE_DIR / stage["script"]
    expected_output = OUTPUT_DIR / stage["output"]

    if not script_path.exists():
        raise FileNotFoundError(
            f"Script not found for {name}: {script_path}"
        )

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    stage_start = time.perf_counter()
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        log(f"Starting {name} (attempt {attempt}/{max_attempts}): {stage['script']}")
        started_at = time.time()

        try:
            stage_env = os.environ.copy()
            stage_env.setdefault("PYTHONUTF8", "1")
            stage_env.setdefault("PYTHONIOENCODING", "utf-8")

            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=BASE_DIR,
                env=stage_env,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"{name} failed with exit code {result.returncode}"
                )

            validate_stage_output(stage, started_at)

            duration = time.perf_counter() - stage_start
            log(f"{name} completed on attempt {attempt}/{max_attempts} in {duration:.2f} seconds.")
            log(f"Output verified: {expected_output}")
            return duration

        except Exception as error:
            last_error = error
            log(f"{name} attempt {attempt}/{max_attempts} failed: {error}")

            if is_permanent_config_error(error):
                log(f"{name} encountered a permanent configuration error; skipping retries.")
                raise

            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                log(f"Retrying {name} in {delay:.1f} seconds (exponential backoff)...")
                time.sleep(delay)

    assert last_error is not None
    raise RuntimeError(
        f"{name} failed after {max_attempts} attempt(s): {last_error}"
    ) from last_error


# --------------------------------------------------
# 4. Run the complete pipeline
# --------------------------------------------------

def main() -> int:
    pipeline_start = time.perf_counter()
    stage_durations = {}
    exit_status = 1

    log("=" * 60)
    log("MARKET RESEARCH AND GTM PIPELINE STARTED")
    log(f"Retry configuration: max_attempts={MAX_STAGE_ATTEMPTS}, base_delay={RETRY_BASE_DELAY}s")
    log("=" * 60)

    init_usage_report()

    try:
        for stage in PIPELINE_STAGES:
            duration = run_stage(stage)
            stage_durations[stage["name"]] = duration

        total_duration = time.perf_counter() - pipeline_start
        exit_status = 0

        log("=" * 60)
        log("PIPELINE COMPLETED SUCCESSFULLY")
        log("=" * 60)

        log("STAGE EXECUTION SUMMARY")

        for stage_name, duration in stage_durations.items():
            log(f"{stage_name}: {duration:.2f} seconds")

        if DEFAULT_USAGE_REPORT_PATH.exists():
            try:
                usage_data = json.loads(DEFAULT_USAGE_REPORT_PATH.read_text(encoding="utf-8"))
                totals = usage_data.get("totals", {})
                log(
                    f"Token usage: total={totals.get('total_tokens', 0)}, "
                    f"prompt={totals.get('prompt_tokens', 0)}, "
                    f"completion={totals.get('completion_tokens', 0)}, "
                    f"estimated_cost_usd=${totals.get('estimated_cost_usd', 0.0):.6f}"
                )
                if usage_data.get("budget_exceeded"):
                    log(
                        f"WARNING: Estimated pipeline cost (${totals.get('estimated_cost_usd', 0.0):.6f}) "
                        f"exceeded budget limit (${usage_data.get('budget_limit_usd', 0.0):.6f})."
                    )
            except json.JSONDecodeError:
                log("WARNING: Could not parse usage_report.json for summary.")

        log(f"Total pipeline duration: {total_duration:.2f} seconds")
        log(f"Final exit status: {exit_status}")

        log(
            "Final report: "
            f"{OUTPUT_DIR / 'final_market_research_report.md'}"
        )
        return exit_status

    except Exception as error:
        total_duration = time.perf_counter() - pipeline_start
        exit_status = 1

        log(f"PIPELINE FAILED: {error}")
        log(f"Elapsed time before failure: {total_duration:.2f} seconds")
        log(f"Final exit status: {exit_status}")

        raise


if __name__ == "__main__":
    sys.exit(main())