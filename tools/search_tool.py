
import json
import os
import serpapi

from dotenv import load_dotenv
from crewai.tools import tool

load_dotenv()


@tool("Web Search Tool")
def search_web(query: str) -> str:
    """Search Google for market research information.

    Args:
        query: A specific search query.

    Returns:
        JSON search results containing titles, URLs, and snippets.
    """

    api_key = os.getenv("SERPAPI_API_KEY")

    if not api_key:
        return json.dumps({
            "error": "SERPAPI_API_KEY is not configured."
        })

    try:
        client = serpapi.Client(
            api_key=api_key,
            timeout=20,
        )

        results = client.search({
            "engine": "google",
            "q": query,
            "gl": "in",
            "hl": "en",
        })

        organic_results = results.get("organic_results", [])

        formatted_results = []

        for result in organic_results[:5]:
            formatted_results.append({
                "title": result.get("title"),
                "url": result.get("link"),
                "snippet": result.get("snippet"),
                "displayed_link": result.get("displayed_link"),
                "date": result.get("date"),
            })

        return json.dumps({
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results,
        }, ensure_ascii=False)

    except Exception as exc:
        return json.dumps({
            "error": f"{type(exc).__name__}: {exc}"
        })
