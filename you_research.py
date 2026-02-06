"""Call You.com search and build a research summary per file."""
from typing import Any

from config import YOU_API_KEY


def research_and_summarize(file_content_preview: str, filename: str, you_api_key: str | None = None) -> dict[str, Any]:
    """
    Use You.com search to research the topic of the file content, then return
    a summary dict with query used, snippets, and a short summary.
    """
    api_key = you_api_key or YOU_API_KEY
    if not api_key:
        return {
            "filename": filename,
            "summary": "You.com API key not set. Set YOU_API_KEY to enable research.",
            "query": "",
            "snippets": [],
            "error": "missing_api_key",
        }
    # Build search query from first 300 chars of content
    query_text = (file_content_preview or "").strip()[:300].replace("\n", " ")
    if not query_text:
        query_text = filename
    query = f"Research and summarize: {query_text}"
    try:
        from youdotcom import You
        with You(api_key) as you:
            results = you.search.unified(query=query, count=5)
        snippets = []
        if results and getattr(results, "results", None):
            web = getattr(results.results, "web", None) or []
            for item in web:
                title = getattr(item, "title", "") or ""
                desc = getattr(item, "description", "") or ""
                snips = getattr(item, "snippets", None) or []
                url = getattr(item, "url", "") or ""
                snippets.append({"title": title, "description": desc, "snippets": snips[:2], "url": url})
        # Build a short summary from first snippet set
        summary_parts = []
        for s in snippets[:3]:
            if s.get("description"):
                summary_parts.append(s["description"][:200])
            for snip in s.get("snippets", [])[:1]:
                if snip:
                    summary_parts.append(str(snip)[:200])
        summary = " ".join(summary_parts)[:600] if summary_parts else "No web results found for this file."
        return {
            "filename": filename,
            "summary": summary,
            "query": query,
            "snippets": snippets,
            "error": None,
        }
    except Exception as e:
        return {
            "filename": filename,
            "summary": f"Research failed: {str(e)}",
            "query": query,
            "snippets": [],
            "error": str(e),
        }
