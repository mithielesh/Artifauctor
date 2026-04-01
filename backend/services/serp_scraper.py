import os
from tavily import TavilyClient
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# We will move this to a .env file later, but hardcode it here just to test it right now
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def fetch_top_serp_results(keyword: str, max_results: int = 5) -> list:
    """
    The 'Eyes' of the AI Engine.
    Uses Tavily (built for AI agents) to reliably fetch clean SERP data without getting blocked.
    """
    logging.info(f"Using Tavily AI Search for keyword: '{keyword}'")
    
    try:
        # Initialize the client
        client = TavilyClient(api_key=TAVILY_API_KEY)
        
        # We use 'advanced' search depth to get high-quality content snippets for the AI
        response = client.search(query=keyword, search_depth="advanced", max_results=max_results)
        
        competitor_data = []
        for index, result in enumerate(response.get("results", [])):
            competitor_data.append({
                "rank": index + 1,
                "title": result.get("title", ""),
                "link": result.get("url", ""),
                "snippet": result.get("content", "") # High-quality text for our LLM to read
            })
            
        logging.info(f"Successfully retrieved {len(competitor_data)} high-quality snippets.")
        return competitor_data
        
    except Exception as e:
        logging.error(f"Search API failed: {e}")
        return []

# --- Quick Test Block ---
if __name__ == "__main__":
    # The exact keyword required by the hackathon document
    test_keyword = "Blogy AI Automation Tool India"
    print(f"\n--- Testing Robust Tavily Scraper for: '{test_keyword}' ---\n")
    
    data = fetch_top_serp_results(test_keyword, max_results=3)
    
    for item in data:
        print(f"Rank #{item['rank']}: {item['title']}")
        print(f"URL: {item['link']}")
        print(f"Snippet: {item['snippet'][:200]}...\n") # Truncating snippet for clean terminal output