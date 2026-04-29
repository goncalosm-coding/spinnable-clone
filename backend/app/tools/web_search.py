from langchain.tools import tool
from ddgs import DDGS

@tool
def web_search(query: str) -> str:
    """Search the web for up-to-date information on a topic."""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            if not results:
                return "No results found."
            return "\n\n".join([
                f"Title: {r['title']}\nURL: {r['href']}\nSummary: {r['body']}"
                for r in results
            ])
    except Exception as e:
        return f"Search failed: {str(e)}"