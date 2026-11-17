"""YouTube MCP Server: Search videos and fetch video links for OmniAgent."""

from __future__ import annotations
import urllib.parse
import urllib.request
import re
from mcp.server.fastmcp import FastMCP

# Initialize the YouTube MCP Server
mcp = FastMCP("youtube-tools")


@mcp.tool()
def search_youtube_videos(query: str, max_results: int = 3) -> str:
    """Search YouTube for videos matching a given query and return titles and links.
    
    Args:
        query: The search term or topic (e.g. 'Python tutorial for beginners', 'Latest AI news').
        max_results: Number of video results to return (default is 3, maximum is 10).
    """
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        # User-Agent header so YouTube returns proper HTML
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Extract video IDs
        raw_ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
        video_ids = list(dict.fromkeys(raw_ids))[: max(1, min(max_results, 10))]

        if not video_ids:
            # Fallback search URL
            return f"Found search page for '{query}': {url}"

        results = [f"Found {len(video_ids)} YouTube videos for '{query}':"]
        for idx, vid in enumerate(video_ids, 1):
            results.append(f"{idx}. https://www.youtube.com/watch?v={vid}")

        return "\n".join(results)
    except Exception as e:
        encoded = urllib.parse.quote_plus(query)
        return (
            f"YouTube search link for '{query}': "
            f"https://www.youtube.com/results?search_query={encoded} (Direct query failed: {e})"
        )


@mcp.tool()
def get_youtube_video_link(query: str) -> str:
    """Quickly get the best matching single YouTube video link for a topic.
    
    Args:
        query: Topic or video title to find.
    """
    return search_youtube_videos(query, max_results=1)


if __name__ == "__main__":
    mcp.run()
