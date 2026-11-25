import os
import serpapi

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("SERPAPI_API_KEY")

if not api_key:
    raise ValueError(
        "SERPAPI_API_KEY is missing from your .env file"
    )

client = serpapi.Client(
    api_key=api_key,
    timeout=20,
)

query = (
    "AI interview preparation platforms "
    "for software developers in India"
)

results = client.search({
    "engine": "google",
    "q": query,
    "gl": "in",
    "hl": "en",
})

organic_results = results.get("organic_results", [])

for index, result in enumerate(organic_results[:5], start=1):
    print(f"\nResult {index}")
    print("Title:", result.get("title"))
    print("URL:", result.get("link"))
    print("Snippet:", result.get("snippet"))