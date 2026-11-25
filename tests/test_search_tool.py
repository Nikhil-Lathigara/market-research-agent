
import json
import pytest

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import search_tool

def test_search_returns_formatted_results(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "fake-test-key")

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def search(self, params):
            return {
                "organic_results": [
                    {
                        "title": "Example Platform",
                        "link": "https://example.com",
                        "snippet": "Example search result",
                    }
                ]
            }

    monkeypatch.setattr(search_tool.serpapi, "Client", FakeClient)

    result = json.loads(
        search_tool.search_web.run(query="AI interview preparation")
    )

    assert result["results_count"] == 1
    assert result["results"][0]["title"] == "Example Platform"
    assert result["results"][0]["url"] == "https://example.com"


def test_search_handles_missing_api_key(monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)

    result = json.loads(
        search_tool.search_web.run(query="test query")
    )

    assert "error" in result
    assert "SERPAPI_API_KEY" in result["error"]


def test_search_handles_empty_results(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "fake-test-key")

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def search(self, params):
            return {"organic_results": []}

    monkeypatch.setattr(search_tool.serpapi, "Client", FakeClient)

    result = json.loads(
        search_tool.search_web.run(query="test query")
    )

    assert result["results_count"] == 0
    assert result["results"] == []


def test_search_handles_api_exception(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "fake-test-key")

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def search(self, params):
            raise RuntimeError("Simulated API failure")

    monkeypatch.setattr(search_tool.serpapi, "Client", FakeClient)

    result = json.loads(
        search_tool.search_web.run(query="test query")
    )

    assert "error" in result
    assert "Simulated API failure" in result["error"]
