import ipaddress
import os
import socket
from urllib.parse import urljoin, urlparse

import httpx
import serpapi
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("Market Research MCP Server")

USER_AGENT = "MarketResearchBot/1.0"
MAX_PAGE_LENGTH = 12_000
TIMEOUT = 15.0


def check_public_url(url: str) -> tuple[bool, str]:
    """Validate URL format and reject local/private network destinations."""

    try:
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return False, "Only HTTP and HTTPS URLs are allowed."

        if not parsed.hostname:
            return False, "The URL must contain a hostname."

        if parsed.username or parsed.password:
            return False, "URLs containing credentials are not allowed."

        hostname = parsed.hostname

        if hostname.lower() == "localhost":
            return False, "Localhost URLs are not allowed."

        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(
                    hostname,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            }
        except socket.gaierror:
            return False, "The hostname could not be resolved."

        if not addresses:
            return False, "No IP addresses were found for the hostname."

        for address in addresses:
            ip = ipaddress.ip_address(address)

            if not ip.is_global:
                return False, "Private or non-public IP destinations are not allowed."

        return True, "URL format and destination checks passed."

    except (ValueError, UnicodeError):
        return False, "Invalid URL."


@mcp.tool()
def search_web(query: str) -> list[dict[str, str]]:
    """
    Search Google using SerpAPI.

    Returns result titles, URLs, and snippets.
    """

    api_key = os.getenv("SERPAPI_API_KEY")

    if not api_key:
        return [{"error": "SERPAPI_API_KEY is missing from .env"}]

    try:
        client = serpapi.Client(api_key=api_key, timeout=20)

        results = client.search({
            "engine": "google",
            "q": query,
            "gl": "in",
            "hl": "en",
        })

        return [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in results.get("organic_results", [])[:5]
        ]

    except Exception as exc:
        return [{
            "error": f"Search failed: {type(exc).__name__}: {exc}"
        }]


@mcp.tool()
def validate_url(url: str) -> dict[str, str]:
    """
    Check whether a URL is valid, publicly reachable, and returns an HTTP response.

    Redirects are reported rather than followed automatically.
    """

    allowed, message = check_public_url(url)

    if not allowed:
        return {
            "url": url,
            "valid": "false",
            "message": message,
        }

    try:
        with httpx.Client(
            timeout=TIMEOUT,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = client.get(url)

        return {
            "url": url,
            "valid": str(200 <= response.status_code < 300).lower(),
            "status_code": str(response.status_code),
            "content_type": response.headers.get("content-type", ""),
            "message": (
                f"HTTP {response.status_code}. "
                "Redirects are not followed automatically."
                if response.is_redirect
                else "HTTP request completed."
            ),
        }

    except httpx.HTTPError as exc:
        return {
            "url": url,
            "valid": "false",
            "message": f"Request failed: {type(exc).__name__}",
        }


@mcp.tool()
def fetch_webpage(url: str) -> dict[str, str]:
    """
    Fetch a public webpage and extract readable text.

    Returns the page title, final URL, text, and HTTP status.
    Redirects are reported but not followed automatically.
    """

    allowed, message = check_public_url(url)

    if not allowed:
        return {
            "url": url,
            "error": message,
        }

    try:
        with httpx.Client(
            timeout=TIMEOUT,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = client.get(url)

        if response.is_redirect:
            redirect_url = response.headers.get("location", "")

            return {
                "url": url,
                "error": "Redirect detected. Validate the destination before fetching.",
                "redirect_url": urljoin(url, redirect_url),
            }

        response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        if "text/html" not in content_type.lower():
            return {
                "url": url,
                "error": f"Expected HTML, received {content_type or 'unknown content type'}.",
            }

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.get_text(" ", strip=True) if soup.title else ""

        for element in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "noscript",
        ]):
            element.decompose()

        text = soup.get_text(" ", strip=True)

        return {
            "url": url,
            "title": title,
            "status_code": str(response.status_code),
            "text": text[:MAX_PAGE_LENGTH],
            "truncated": str(len(text) > MAX_PAGE_LENGTH).lower(),
        }

    except httpx.HTTPError as exc:
        return {
            "url": url,
            "error": f"Fetch failed: {type(exc).__name__}",
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")