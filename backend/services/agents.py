import os
from google import genai
from google.genai import types
import logging
from dotenv import load_dotenv

# Load the variables from the .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Securely fetch the key from the environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def generate_seo_blog(keyword: str, serp_data: list, domain: str = "General") -> dict:
    """
    The 'Brain' of the operation.
    Built on the google-genai SDK using the blazing fast Gemini 2.5 Flash model.
    Upgraded to an Enterprise Deep-Read Generator with Domain awareness.
    """
    logging.info(f"Initializing Enterprise AI Pipeline for domain: '{domain}'...")
    
    # Defensive programming: crash early if the key is missing
    if not GEMINI_API_KEY:
        logging.error("GEMINI_API_KEY is missing from the .env file!")
        return {}
        
    try:
        # Initialize the new GenAI client with the secure key
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Using the absolute latest high-speed model
        model_id = 'gemini-2.5-flash-lite'
        
        # Step 1: Format the competitor data for the AI to read
        competitor_context = "\n".join([f"Rank {item['rank']}: {item['snippet']}" for item in serp_data])
        
        # Step 2: Agent 1 - The Deep-Dive Strategist
        logging.info("Agent 1 (Strategist) is analyzing SERP gaps and creating a domain-specific outline...")
        strategist_prompt = f"""
        You are an elite SEO Content Strategist for the '{domain}' industry.
        Analyze these top-ranking snippets for the keyword '{keyword}':
        {competitor_context}
        
        Create a comprehensive, Deep-Read blog outline. 
        STRICT FORMATTING RULES:
        1. Return EXACTLY 5 to 7 bullet points.
        2. DO NOT use any Markdown headers (no # or ##). 
        3. Keep each bullet point under 15 words. Focus only on the core highlights.
        4. Include a section for a "Real-World Case Study" and a "Comparison Table".
        5. Only return the raw bulleted list, no introductory text.
        """
        
        outline_response = client.models.generate_content(
            model=model_id,
            contents=strategist_prompt,
            config=types.GenerateContentConfig(
                temperature=0.2, # Low temperature for logical, structured formatting
            )
        )
        outline = outline_response.text
        
        # Step 3: Agent 2 - The Master Copywriter
        logging.info("Agent 2 (Writer) is drafting the content with Live Context...")
        writer_prompt = f"""
        You are a top-tier Senior Technical Writer specializing in the '{domain}' niche.
        Write a highly structured, authoritative Deep-Dive for the keyword '{keyword}'.
        
        CRITICAL REAL-TIME CONTEXT:
        You MUST base your facts, tools, and assertions on this live search data to ensure your knowledge is 100% up-to-date for 2026. 
        If a certification, framework, or tool is deprecated, you MUST state the modern alternative:
        {serp_data}
        
        TARGET LENGTH: 800 to 1200 words maximum. Do NOT write more than this.
        
        Strictly follow this outline:
        {outline}
        
        REQUIRED STRUCTURAL ELEMENTS:
        1. Start with a "TL;DR" summary bulleted list at the top.
        2. Use the PAS Framework in the introduction: Problem, Agitate, Solution.
        3. Include ONE Markdown Table.
        4. Include realistic code snippets using ``` blocks if the domain is Technical.
        5. THE END-CAP: You MUST end the article with a definitive "## Final Thoughts" section.
        
        CRITICAL MARKDOWN RULES (DO NOT FAIL THESE):
        - For the table, you MUST leave an empty blank line before and after it.
        - The table MUST include a standard Markdown separator row (e.g., |---|---|---|).
        - You MUST complete the "## Final Thoughts" section with a final, concluding sentence. Do not cut off.
        """
        
        blog_response = client.models.generate_content(
            model=model_id,
            contents=writer_prompt,
            config=types.GenerateContentConfig(
                temperature=0.5, # Lowered from 0.7 to reduce rambling and hallucinations
                max_output_tokens=8192
            )
        )
        final_blog = blog_response.text
        
        logging.info("Blog generation complete!")
        return {
            "outline": outline,
            "blog_content": final_blog
        }
        
    except Exception as e:
        logging.error(f"Gemini AI Generation failed: {e}")
        return {}