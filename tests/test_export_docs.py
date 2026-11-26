import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import export_docs


def test_build_google_docs_requests_preserves_headings_bullets_and_tables():
    md = (
        "# Main Title\n\n"
        "## Section One\n\n"
        "Intro paragraph.\n\n"
        "- Bullet A\n"
        "- Bullet B\n\n"
        "| Col1 | Col2 |\n"
        "| :--- | :--- |\n"
        "| Val1 | Val2 |\n"
    )
    requests = export_docs.build_google_docs_requests(md)
    assert len(requests) > 0

    styles = [
        r["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"]
        for r in requests
        if "updateParagraphStyle" in r
    ]
    assert "HEADING_1" in styles
    assert "HEADING_2" in styles
    assert any("createParagraphBullets" in r for r in requests)
    assert any("Val1 | Val2" in r["insertText"]["text"] for r in requests if "insertText" in r)


def test_export_skips_gracefully_when_credentials_missing(monkeypatch, tmp_path):
    report_md = tmp_path / "report.md"
    report_md.write_text("# Sample Report\n\nHello.\n", encoding="utf-8")
    export_json = tmp_path / "export_report.json"

    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRETS_FILE", str(tmp_path / "missing_client.json"))
    monkeypatch.setenv("GOOGLE_OAUTH_TOKEN_FILE", str(tmp_path / "missing_token.json"))

    result = export_docs.export_markdown_to_google_docs(
        report_path=report_md,
        export_report_path=export_json,
    )

    assert export_json.exists()
    saved = json.loads(export_json.read_text(encoding="utf-8"))
    assert saved["status"] == "skipped_missing_credentials"
    assert saved["document_url"] is None
    assert "Google OAuth credentials not found" in result["message"]
