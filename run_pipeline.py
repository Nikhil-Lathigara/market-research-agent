import subprocess
import sys
import time
import json
from datetime import datetime
from pathlib import Path


# --------------------------------------------------
# 1. Project configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
LOG_DIR = BASE_DIR / "logs"

LOG_FILE = LOG_DIR / "pipeline.log"

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


# --------------------------------------------------
# 3. Execute one pipeline stage
# --------------------------------------------------

def run_stage(stage: dict) -> float:
    name = stage["name"]
    script_path = BASE_DIR / stage["script"]
    expected_output = OUTPUT_DIR / stage["output"]

    if not script_path.exists():
        raise FileNotFoundError(
            f"Script not found for {name}: {script_path}"
        )

    log(f"Starting {name}: {stage['script']}")

    start_time = time.perf_counter()

    # Execute the script using the current Python environment.
    started_at = time.time()

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=BASE_DIR,
        check=False,
    )

    duration = time.perf_counter() - start_time

    if result.returncode != 0:
        raise RuntimeError(
            f"{name} failed with exit code {result.returncode}"
        )
    
    validate_stage_output(stage, started_at)

    if not expected_output.exists():
        raise FileNotFoundError(
            f"{name} finished, but its expected output was not found: "
            f"{expected_output}"
        )

    log(f"{name} completed in {duration:.2f} seconds.")
    log(f"Output verified: {expected_output}")

    return duration


# --------------------------------------------------
# 4. Run the complete pipeline
# --------------------------------------------------

def main() -> None:
    pipeline_start = time.perf_counter()
    stage_durations = {}

    log("=" * 60)
    log("MARKET RESEARCH AND GTM PIPELINE STARTED")
    log("=" * 60)

    try:
        for stage in PIPELINE_STAGES:
            duration = run_stage(stage)
            stage_durations[stage["name"]] = duration

        total_duration = time.perf_counter() - pipeline_start

        log("=" * 60)
        log("PIPELINE COMPLETED SUCCESSFULLY")
        log("=" * 60)

        log("STAGE EXECUTION SUMMARY")

        for stage_name, duration in stage_durations.items():
            log(f"{stage_name}: {duration:.2f} seconds")

        log(f"Total pipeline duration: {total_duration:.2f} seconds")

        log(
            "Final report: "
            f"{OUTPUT_DIR / 'final_market_research_report.md'}"
        )

    except Exception as error:
        total_duration = time.perf_counter() - pipeline_start

        log(f"PIPELINE FAILED: {error}")
        log(f"Elapsed time before failure: {total_duration:.2f} seconds")

        raise


if __name__ == "__main__":
    main()