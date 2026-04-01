import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

DEVTO_API_KEY = os.getenv("DEVTO_API_KEY")
HASHNODE_TOKEN = os.getenv("HASHNODE_TOKEN")
HASHNODE_PUBLICATION_ID = os.getenv("HASHNODE_PUBLICATION_ID")

def publish_to_devto(title: str, markdown_content: str, tags: list = ["ai", "automation"]) -> str:
    """Publishes to Dev.to via REST API."""
    if not DEVTO_API_KEY:
        return None
        
    logging.info("Agent: Deploying to Dev.to...")
    url = "https://dev.to/api/articles"
    headers = {"api-key": DEVTO_API_KEY, "Content-Type": "application/json"}
    payload = {
        "article": {
            "title": title,
            "body_markdown": markdown_content,
            "published": False, # Draft mode for safety
            "tags": tags
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json().get("url") if response.status_code == 201 else None
    except Exception as e:
        logging.error(f"Dev.to Error: {e}")
        return None

def publish_to_hashnode(title: str, markdown_content: str) -> str:
    """Uses Hashnode GQL 2.0 - LOUD DEBUG EDITION"""
    if not HASHNODE_TOKEN or not HASHNODE_PUBLICATION_ID:
        logging.error("Missing HASHNODE_TOKEN or PUBLICATION_ID in .env")
        return None

    logging.info(f"Agent: Deploying to Hashnode via GraphQL (Pub ID: {HASHNODE_PUBLICATION_ID})...")
    url = "https://gql.hashnode.com"
    headers = {
        "Authorization": HASHNODE_TOKEN,
        "Content-Type": "application/json"
    }
    
    query = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post {
          url
        }
      }
    }
    """
    variables = {
        "input": {
            "publicationId": HASHNODE_PUBLICATION_ID,
            "title": title,
            "contentMarkdown": markdown_content
        }
    }

    try:
        response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
        
        # --- THE MAGIC DEBUG LINES ---
        logging.info(f"Hashnode HTTP Status: {response.status_code}")
        logging.info(f"Hashnode Raw Response: {response.text}")
        # -----------------------------

        res_data = response.json()
        
        if "errors" in res_data:
            logging.error(f"Hashnode API explicitly rejected the post: {res_data['errors']}")
            return None
            
        return res_data["data"]["publishPost"]["post"]["url"]
        
    except Exception as e:
        logging.error(f"Hashnode Request Failed (Python Crash): {e}")
        return None

def deploy_to_all_platforms(keyword: str, markdown_content: str):
    """Orchestrates simultaneous deployment to free, developer-friendly APIs."""
    title = f"Deep Dive: {keyword.title()} - Trends & Automation"
    urls = {}
    
    dev_url = publish_to_devto(title, markdown_content)
    if dev_url: urls["Dev.to"] = dev_url
        
    hash_url = publish_to_hashnode(title, markdown_content)
    if hash_url: urls["Hashnode"] = hash_url
        
    return urls