import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from datetime import datetime

mcp = FastMCP("hn-server")

# Tool hints: tell MCP clients what each tool does, so they know when to ask before running it.
READ_WEB = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

HN_BASE = "https://hacker-news.firebaseio.com/v0"
ALGOLIA = "https://hn.algolia.com/api/v1"

@mcp.tool(annotations=READ_WEB)
def get_top_story(count: int = 10) -> list[dict]:
    """
    Fetch top N stories from Hacker News on the basis of score.
    """
    with httpx.Client() as client:
        response = client.get(f"{HN_BASE}/topstories.json")
        story_ids = response.json()[:count]

        stories=[]
        for story_id in story_ids:
            r = client.get(f"{HN_BASE}/item/{story_id}.json")
            data = r.json()
            stories.append({
                "id": story_id,
                "title": data.get("title"),
                "url": data.get("url"),
                "score": data.get("score"),
                "by": data.get("by"),
                "comments": data.get("descendants", 0)
            })
        return stories
    
@mcp.tool(annotations=READ_WEB)
def get_story_details(story_id: int) -> dict:
    """
    Get full details of a single HN story including comment count and metadata.
    """
    with httpx.Client() as client:
        r = client.get(f"{HN_BASE}/item/{story_id}.json")
        data = r.json()
        return {
            "id": story_id,
            "title": data.get("title"),
            "url": data.get("url"),
            "text": data.get("text"),  
            "score": data.get("score"),
            "by": data.get("by"),
            "time": datetime.fromtimestamp(data.get("time")).isoformat(), 
            "comments": data.get("descendants", 0),
            "type": data.get("type")
        }
    
@mcp.tool(annotations=READ_WEB)
def search_hn(query: str, count: int = 10) -> list[dict]:
    """
    Search Hacker News stories by keyword using Algolia.
    """
    with httpx.Client() as client:
        r = client.get(
            f"{ALGOLIA}/search",
            params={"query": query, "tags": "story", "hitsPerPage": count}
        )
        data = r.json()
        results = []
        for hit in data.get("hits", []):
            results.append({
                "title": hit.get("title"),
                "url": hit.get("url"),
                "author": hit.get("author"),
                "points": hit.get("points"),
                "story_id": hit.get("objectID")
            })
        return results

@mcp.resource("hn://top")
def top_stories_resource() -> str:
    """
    Top 5 HN stories as readable context.
    """
    with httpx.Client() as client:
        response = client.get(f"{HN_BASE}/topstories.json")
        story_ids = response.json()[:5]

        lines = []
        for story_id in story_ids:
            r = client.get(f"{HN_BASE}/item/{story_id}.json")
            data = r.json()
            lines.append(
                f"- {data.get('title')} (score: {data.get('score')}) "
                f"by {data.get('by')} | {data.get('url', 'no url')}"
            )
        return "\n".join(lines)  

@mcp.prompt()
def hn_briefing() -> str:
    """Morning briefing prompt for HN digest."""
    return (
        "You are a tech news assistant. "
        "Fetch the top 5 HN stories and summarize each in one sentence. "
        "Group them by topic if possible."
    )

if __name__ == "__main__":
    mcp.run()