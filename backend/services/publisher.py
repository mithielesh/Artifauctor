# backend/services/publisher.py
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def publish_to_devto(title: str, markdown_content: str, api_key: str, tags: list = None) -> str:
    """Publishes to Dev.to via REST API using the user's secure DB key."""
    if tags is None:
        tags = ["ai", "automation"]
        
    if not api_key:
        logging.error("Agent: Dev.to API key missing.")
        return None
        
    logging.info("Agent: Deploying to Dev.to...")
    url = "https://dev.to/api/articles"
    
    # We now inject the user's specific key directly into the headers
    headers = {"api-key": api_key, "Content-Type": "application/json"}
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
        if response.status_code == 201:
            return response.json().get("url")
        else:
            logging.error(f"Dev.to API explicitly rejected the post. Status: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Dev.to Error: {e}")
        return None

def publish_to_hashnode(title: str, markdown_content: str, token: str, pub_id: str) -> str:
    """Uses Hashnode GQL 2.0 with the user's personal Token and Publication ID"""
    
    if not token or not pub_id:
        logging.error("Agent: Missing Hashnode Token or Publication ID")
        return None

    logging.info(f"Agent: Deploying to Hashnode via GraphQL (Pub ID: {pub_id})...")
    url = "https://gql.hashnode.com"
    
    # We now inject the user's specific token directly into the headers
    headers = {
        "Authorization": token,
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
            "publicationId": pub_id,
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