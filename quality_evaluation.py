import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

RESEARCH_FILE = OUTPUT_DIR / "research_evidence.json"
ANALYSIS_FILE = OUTPUT_DIR / "analysis_report.json"
STRATEGY_FILE = OUTPUT_DIR / "gtm_strategy.json"
REPORT_FILE = OUTPUT_DIR / "final_market_research_report.md"
QUALITY_REPORT_FILE = OUTPUT_DIR / "quality_report.json"

URL_REGEX = re.compile(
    r"https?://[^\s<>\"']+",
    re.IGNORECASE,
)

URL_FIELD_NAMES = {
    "url",
    "source_url",
    "source",
    "pricing_source",
    "official_website",
    "website",
    "link",
    "href",
    "source_link",
    "citation_url",
}


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(path: Path) -> dict:
    """Load and validate a JSON file."""

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_list(data, possible_keys: list[str]) -> list:
    """Find a list using the provided keys."""

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in possible_keys:
            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


# ============================================================
# EVIDENCE ID VALIDATION
# ============================================================

def extract_evidence_ids(data) -> set[str]:
    """Recursively extract evidence IDs from nested JSON."""

    evidence_ids = set()

    if isinstance(data, dict):
        for key, value in data.items():

            normalized_key = key.lower()

            if normalized_key in {
                "evidence_id",
                "evidence_ids",
                "source_evidence_id",
            }:

                if isinstance(value, str):
                    evidence_ids.add(value.strip())

                elif isinstance(value, list):
                    evidence_ids.update(
                        item.strip()
                        for item in value
                        if isinstance(item, str) and item.strip()
                    )

            else:
                evidence_ids.update(extract_evidence_ids(value))

    elif isinstance(data, list):
        for item in data:
            evidence_ids.update(extract_evidence_ids(item))

    return evidence_ids


# ============================================================
# URL EXTRACTION AND VALIDATION
# ============================================================

def is_valid_http_url(value: str) -> bool:
    """Check whether a value is a syntactically valid HTTP(S) URL."""

    if not isinstance(value, str):
        return False

    try:
        parsed = urlparse(value.strip())

        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.netloc)
            and "." in parsed.netloc
            and " " not in parsed.netloc
        )

    except (ValueError, TypeError):
        return False


def clean_url(url: str) -> str:
    """Remove common trailing punctuation from extracted URLs."""

    return url.rstrip(".,;:!?)\u005d}")


def extract_urls(data) -> list[str]:
    """
    Recursively extract HTTP(S) URLs from JSON.

    This does not depend exclusively on a particular JSON field name.
    It also finds URLs embedded in strings.
    """

    found = []

    if isinstance(data, dict):

        for key, value in data.items():

            # Explicitly recognized URL fields
            if key.lower() in URL_FIELD_NAMES:

                if isinstance(value, str):
                    candidates = URL_REGEX.findall(value)

                    for candidate in candidates:
                        url = clean_url(candidate)

                        if is_valid_http_url(url):
                            found.append(url)

                elif isinstance(value, list):
                    found.extend(extract_urls(value))

                elif isinstance(value, dict):
                    found.extend(extract_urls(value))

            else:
                found.extend(extract_urls(value))

    elif isinstance(data, list):

        for item in data:
            found.extend(extract_urls(item))

    elif isinstance(data, str):

        # Also find URLs embedded in answer text or other strings.
        candidates = URL_REGEX.findall(data)

        for candidate in candidates:
            url = clean_url(candidate)

            if is_valid_http_url(url):
                found.append(url)

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(found))


def get_record_urls(record: dict) -> list[str]:
    """Return the URLs found inside an individual evidence record."""

    return extract_urls(record)


# ============================================================
# URL REACHABILITY CHECKS
# ============================================================

async def check_url(
    client: httpx.AsyncClient,
    url: str,
) -> dict:
    """
    Check whether a URL responds to an HTTP request.

    A reachable URL does not guarantee that its content is accurate
    or supports the claim made in the research.
    """

    if not is_valid_http_url(url):
        return {
            "url": url,
            "reachable": False,
            "status_code": None,
            "error": "Invalid HTTP(S) URL",
        }

    try:
        # HEAD avoids downloading the entire page.
        response = await client.head(url)

        # Some websites block HEAD requests.
        if response.status_code in {403, 405, 501}:
            response = await client.get(
                url,
                headers={"Range": "bytes=0-1023"},
            )

        reachable = response.status_code < 400

        return {
            "url": url,
            "reachable": reachable,
            "status_code": response.status_code,
            "error": None if reachable else "HTTP error response",
        }

    except httpx.TimeoutException:
        return {
            "url": url,
            "reachable": False,
            "status_code": None,
            "error": "Request timed out",
        }

    except httpx.RequestError as error:
        return {
            "url": url,
            "reachable": False,
            "status_code": None,
            "error": type(error).__name__,
        }

    except Exception as error:
        return {
            "url": url,
            "reachable": False,
            "status_code": None,
            "error": type(error).__name__,
        }


async def evaluate_urls(urls: list[str]) -> list[dict]:
    """Check URLs concurrently."""

    timeout = httpx.Timeout(
        10.0,
        connect=5.0,
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        max_redirects=10,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; MarketResearchQualityChecker/1.0)"
            )
        },
    ) as client:

        results = await asyncio.gather(
            *[
                check_url(client, url)
                for url in urls
            ],
            return_exceptions=True,
        )

    normalized_results = []

    for url, result in zip(urls, results):

        if isinstance(result, Exception):

            normalized_results.append({
                "url": url,
                "reachable": False,
                "status_code": None,
                "error": type(result).__name__,
            })

        else:
            normalized_results.append(result)

    return normalized_results


# ============================================================
# MAIN QUALITY EVALUATION
# ============================================================

async def main():

    print("\nLoading project outputs...")

    research = load_json(RESEARCH_FILE)
    analysis = load_json(ANALYSIS_FILE)
    strategy = load_json(STRATEGY_FILE)

    if not REPORT_FILE.exists():
        raise FileNotFoundError(
            f"Missing final report: {REPORT_FILE}"
        )

    report = REPORT_FILE.read_text(encoding="utf-8")

    # --------------------------------------------------------
    # 1. Extract research records
    # --------------------------------------------------------

    evidence = find_list(
        research,
        [
            "evidence",
            "evidence_records",
            "sources",
            "results",
        ],
    )

    questions = find_list(
        research,
        [
            "research_questions",
            "questions",
        ],
    )

    competitors = find_list(
        research,
        ["competitors"],
    )

    # --------------------------------------------------------
    # 2. Evidence IDs and per-record URLs
    # --------------------------------------------------------

    evidence_ids = []
    evidence_records_with_urls = 0
    evidence_records_without_urls = []

    for index, record in enumerate(evidence, start=1):

        if not isinstance(record, dict):
            continue

        evidence_id = (
            record.get("evidence_id")
            or record.get("id")
        )

        if evidence_id:
            evidence_ids.append(str(evidence_id))

        record_urls = get_record_urls(record)

        if record_urls:
            evidence_records_with_urls += 1
        else:
            evidence_records_without_urls.append(
                str(evidence_id or f"record_{index}")
            )

    unique_ids = set(evidence_ids)

    duplicate_count = (
        len(evidence_ids) - len(unique_ids)
    )

    # --------------------------------------------------------
    # 3. Collect URLs from the complete research JSON
    # --------------------------------------------------------

    research_urls = extract_urls(research)

    # Also collect URLs from analysis and strategy outputs.
    analysis_urls = extract_urls(analysis)
    strategy_urls = extract_urls(strategy)

    all_urls = list(
        dict.fromkeys(
            research_urls
            + analysis_urls
            + strategy_urls
        )
    )

    print(f"Evidence records found: {len(evidence)}")
    print(f"Competitors found: {len(competitors)}")
    print(f"Research questions found: {len(questions)}")
    print(f"Unique URLs found across JSON files: {len(all_urls)}")

    # --------------------------------------------------------
    # 4. Check URL reachability
    # --------------------------------------------------------

    print("\nChecking URL reachability...")

    url_results = await evaluate_urls(all_urls)

    reachable_count = sum(
        1
        for item in url_results
        if item["reachable"]
    )

    unreachable_count = (
        len(url_results) - reachable_count
    )

    print("\nURL REACHABILITY")
    print("=" * 55)

    print(f"Unique URLs checked: {len(url_results)}")
    print(f"Reachable URLs: {reachable_count}")
    print(f"Unreachable or blocked URLs: {unreachable_count}")

    for item in url_results:

        if not item["reachable"]:

            print(
                f"  FAILED: {item['url']}\n"
                f"    Status: {item['status_code']}\n"
                f"    Error: {item['error']}"
            )

    # --------------------------------------------------------
    # 5. Validate evidence references
    # --------------------------------------------------------

    analysis_ids = extract_evidence_ids(analysis)
    strategy_ids = extract_evidence_ids(strategy)

    invalid_analysis_ids = (
        analysis_ids - unique_ids
    )

    invalid_strategy_ids = (
        strategy_ids - unique_ids
    )

    # --------------------------------------------------------
    # 6. Validate report headings
    # --------------------------------------------------------

    required_headings = [
        "Executive Summary",
        "Market Research Findings",
        "Competitor Landscape",
        "Competitive Pricing Analysis",
        "SWOT Analysis",
        "Ideal Customer Profiles",
        "Channel Strategy",
        "Launch Plan",
        "Risks and Mitigations",
        "Limitations and Items Requiring Verification",
    ]

    missing_headings = [
        heading
        for heading in required_headings
        if not re.search(
            rf"^#+\s*.*{re.escape(heading)}",
            report,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    ]

    # --------------------------------------------------------
    # 7. Print summary
    # --------------------------------------------------------

    print("\nQUALITY EVALUATION")
    print("=" * 55)

    print(f"Evidence records found: {len(evidence)}")
    print(
        "Evidence records containing HTTP(S) URLs: "
        f"{evidence_records_with_urls}"
    )

    print(f"Unique evidence IDs: {len(unique_ids)}")
    print(f"Duplicate evidence IDs: {duplicate_count}")

    print(
        f"Analysis evidence references: {len(analysis_ids)}"
    )

    print(
        "Invalid analysis evidence IDs: "
        f"{len(invalid_analysis_ids)}"
    )

    print(
        f"Strategy evidence references: {len(strategy_ids)}"
    )

    print(
        "Invalid strategy evidence IDs: "
        f"{len(invalid_strategy_ids)}"
    )

    print(
        f"Missing final report headings: {len(missing_headings)}"
    )

    if evidence_records_without_urls:

        print("\nEvidence records without detected URLs:")

        for evidence_id in evidence_records_without_urls:
            print(f"  - {evidence_id}")

    if invalid_analysis_ids:
        print(
            "\nInvalid analysis evidence IDs:",
            sorted(invalid_analysis_ids),
        )

    if invalid_strategy_ids:
        print(
            "\nInvalid strategy evidence IDs:",
            sorted(invalid_strategy_ids),
        )

    if missing_headings:

        print("\nMissing report headings:")

        for heading in missing_headings:
            print(f"  - {heading}")

    # --------------------------------------------------------
    # 8. Calculate basic quality indicators
    # --------------------------------------------------------

    evidence_url_coverage = (
        evidence_records_with_urls / len(evidence) * 100
        if evidence
        else 0
    )

    url_reachability_rate = (
        reachable_count / len(url_results) * 100
        if url_results
        else 0
    )

    # --------------------------------------------------------
    # 9. Save machine-readable quality report
    # --------------------------------------------------------

    quality_report = {
        "evaluated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "input_files": {
            "research": str(RESEARCH_FILE),
            "analysis": str(ANALYSIS_FILE),
            "strategy": str(STRATEGY_FILE),
            "final_report": str(REPORT_FILE),
        },

        "research_metrics": {
            "research_questions": len(questions),
            "competitors": len(competitors),
            "evidence_records": len(evidence),
            "evidence_records_with_urls": (
                evidence_records_with_urls
            ),
            "evidence_records_without_urls": (
                evidence_records_without_urls
            ),
            "evidence_url_coverage_percent": round(
                evidence_url_coverage,
                2,
            ),
        },

        "evidence_id_validation": {
            "unique_evidence_ids": len(unique_ids),
            "duplicate_evidence_ids": duplicate_count,
            "analysis_evidence_reference_count": len(
                analysis_ids
            ),
            "invalid_analysis_evidence_ids": sorted(
                invalid_analysis_ids
            ),
            "strategy_evidence_reference_count": len(
                strategy_ids
            ),
            "invalid_strategy_evidence_ids": sorted(
                invalid_strategy_ids
            ),
        },

        "url_checks": {
            "total": len(url_results),
            "reachable": reachable_count,
            "unreachable_or_blocked": unreachable_count,
            "reachability_percent": round(
                url_reachability_rate,
                2,
            ),
            "results": url_results,
        },

        "report_validation": {
            "missing_headings": missing_headings,
            "missing_heading_count": len(missing_headings),
        },

        "limitations": [
            (
                "URL reachability does not prove that a source "
                "supports the associated claim."
            ),
            (
                "Some websites may block automated requests, "
                "so an unreachable result is not definitive "
                "proof that a URL is broken."
            ),
            (
                "Evidence ID validation checks references, "
                "not factual accuracy."
            ),
            (
                "URL coverage depends on the structure and "
                "contents of the research JSON."
            ),
            (
                "Source authority, source recency, claim support, "
                "and factual consistency require additional checks."
            ),
        ],
    }

    QUALITY_REPORT_FILE.write_text(
        json.dumps(
            quality_report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nQUALITY REPORT")
    print("=" * 55)

    print(
        f"Evidence URL coverage: "
        f"{evidence_url_coverage:.2f}%"
    )

    print(
        f"URL reachability rate: "
        f"{url_reachability_rate:.2f}%"
    )

    print(
        f"Quality report saved to:\n"
        f"{QUALITY_REPORT_FILE}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())