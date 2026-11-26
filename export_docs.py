import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
DEFAULT_REPORT_PATH = OUTPUT_DIR / "final_market_research_report.md"
DEFAULT_EXPORT_REPORT_PATH = OUTPUT_DIR / "export_report.json"

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

SETUP_INSTRUCTIONS = (
    "To enable Google Docs export: (1) Create an OAuth 2.0 Desktop Client ID in "
    "Google Cloud Console with Google Docs API and Google Drive API enabled, "
    "(2) download the client secrets JSON to credentials/google_oauth_client.json "
    "(or set GOOGLE_OAUTH_CLIENT_SECRETS_FILE in .env), and (3) run "
    "`uv run python export_docs.py` to complete the OAuth consent flow."
)


def resolve_credential_paths() -> tuple[Path, Path]:
    """Resolve OAuth client secrets and token cache paths outside source code."""
    client_secrets = Path(
        os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS_FILE")
        or (BASE_DIR / "credentials" / "google_oauth_client.json")
    )
    token_file = Path(
        os.getenv("GOOGLE_OAUTH_TOKEN_FILE")
        or (BASE_DIR / "credentials" / "google_token.json")
    )
    return client_secrets, token_file


def parse_markdown_blocks(markdown_text: str) -> list[dict[str, Any]]:
    """Parse Markdown into structured blocks (headings, bullets, tables, paragraphs)."""
    blocks: list[dict[str, Any]] = []
    lines = markdown_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            blocks.append({"type": "heading", "level": level, "text": heading_match.group(2).strip()})
            i += 1
            continue

        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1]):
            table_rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                row_line = lines[i].strip()
                if not re.match(r"^\|[\s:\-|]+\|$", row_line):
                    cells = [c.strip() for c in row_line.strip("|").split("|")]
                    table_rows.append(cells)
                i += 1
            if table_rows:
                blocks.append({"type": "table", "rows": table_rows})
            continue

        bullet_match = re.match(r"^\s*[-*]\s+(.*)$", line)
        if bullet_match:
            blocks.append({"type": "bullet", "text": bullet_match.group(1).strip()})
            i += 1
            continue

        blocks.append({"type": "paragraph", "text": line.strip()})
        i += 1

    return blocks


def build_google_docs_requests(markdown_text: str) -> list[dict[str, Any]]:
    """Convert Markdown blocks into Google Docs batchUpdate requests."""
    blocks = parse_markdown_blocks(markdown_text)
    requests: list[dict[str, Any]] = []
    cursor = 1

    heading_styles = {
        1: "HEADING_1",
        2: "HEADING_2",
        3: "HEADING_3",
    }

    for block in blocks:
        btype = block["type"]
        if btype == "table":
            # Render table rows as structured tab-separated lines for reliable API insertion
            lines = [" | ".join(row) for row in block["rows"]]
            text = "\n".join(lines) + "\n\n"
            requests.append({"insertText": {"location": {"index": cursor}, "text": text}})
            cursor += len(text)
            continue

        text = block["text"] + "\n"
        start_idx = cursor
        end_idx = cursor + len(text)
        requests.append({"insertText": {"location": {"index": start_idx}, "text": text}})

        if btype == "heading":
            style = heading_styles.get(block["level"], "HEADING_3")
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": start_idx, "endIndex": end_idx},
                    "paragraphStyle": {"namedStyleType": style},
                    "fields": "namedStyleType",
                }
            })
        elif btype == "bullet":
            requests.append({
                "createParagraphBullets": {
                    "range": {"startIndex": start_idx, "endIndex": end_idx},
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            })

        cursor = end_idx

    return requests


def _write_export_report(
    payload: dict[str, Any],
    export_report_path: Path | None = None,
) -> dict[str, Any]:
    path = export_report_path or DEFAULT_EXPORT_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def export_markdown_to_google_docs(
    report_path: Path | None = None,
    export_report_path: Path | None = None,
    title: str = "Market Research and Go-to-Market Plan",
    export_pdf: bool = False,
) -> dict[str, Any]:
    """Export the final Markdown report to Google Docs using OAuth credentials.

    Gracefully skips if OAuth credentials or Google API packages are unavailable.
    """
    src_path = report_path or DEFAULT_REPORT_PATH
    if not src_path.exists():
        return _write_export_report(
            {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "status": "failed_missing_source_report",
                "source_report": str(src_path),
                "document_id": None,
                "document_url": None,
                "pdf_path": None,
                "message": f"Markdown report not found: {src_path}",
            },
            export_report_path,
        )

    client_secrets, token_file = resolve_credential_paths()
    if not client_secrets.exists() and not token_file.exists():
        return _write_export_report(
            {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "status": "skipped_missing_credentials",
                "source_report": str(src_path),
                "document_id": None,
                "document_url": None,
                "pdf_path": None,
                "message": f"Google OAuth credentials not found at {client_secrets}. {SETUP_INSTRUCTIONS}",
            },
            export_report_path,
        )

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        return _write_export_report(
            {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "status": "skipped_missing_dependencies",
                "source_report": str(src_path),
                "document_id": None,
                "document_url": None,
                "pdf_path": None,
                "message": f"Google API packages not installed ({exc}). Run `uv add google-api-python-client google-auth-oauthlib`.",
            },
            export_report_path,
        )

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    docs_service = build("docs", "v1", credentials=creds)
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    markdown_text = src_path.read_text(encoding="utf-8")
    requests = build_google_docs_requests(markdown_text)
    if requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()

    pdf_output_path = None
    if export_pdf:
        drive_service = build("drive", "v3", credentials=creds)
        pdf_bytes = drive_service.files().export_media(
            fileId=doc_id,
            mimeType="application/pdf",
        ).execute()
        pdf_path = OUTPUT_DIR / "final_market_research_report.pdf"
        pdf_path.write_bytes(pdf_bytes)
        pdf_output_path = str(pdf_path)

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return _write_export_report(
        {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "status": "exported",
            "source_report": str(src_path),
            "document_id": doc_id,
            "document_url": doc_url,
            "pdf_path": pdf_output_path,
            "message": "Successfully exported Markdown report to Google Docs.",
        },
        export_report_path,
    )


if __name__ == "__main__":
    result = export_markdown_to_google_docs()
    print(json.dumps(result, indent=2, ensure_ascii=False))
