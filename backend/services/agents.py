# backend/services/agents.py
import logging
import json
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def generate_seo_blog(keyword: str, serp_data: list, domain: str = "General", api_key: str = None, brand_voice: str = None, previous_links: list = None) -> dict:
    """
    The 'Brain' of the operation.
    Built on the google-genai SDK using the blazing fast Gemini 2.5 Flash model.
    Upgraded to an Enterprise Deep-Read Generator with BYOK, Brand Voice, and Internal Linking.
    """
    logging.info(f"Initializing Enterprise AI Pipeline for domain: '{domain}'...")
    
    # Defensive programming: crash early if the key is missing from the DB payload
    if not api_key:
        logging.error("API Key was not provided by the Router!")
        raise ValueError("Gemini API Key is required to run the pipeline. Check your Vault Settings.")
        
    try:
        # Initialize the new GenAI client dynamically per user request!
        client = genai.Client(api_key=api_key)
        
        # Using the absolute latest high-speed model
        model_id = 'gemini-2.5-flash'
        
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
        
        # --- BRAND VOICE INJECTION (Agent 0) ---
        brand_voice_injection = ""
        if brand_voice:
            brand_voice_injection = f"""
            CRITICAL TONE REQUIREMENT (BRAND VOICE):
            You MUST mimic the exact tone, pacing, and vocabulary of the user's writing sample below. 
            Do not sound generic. Sound exactly like this author:
            "{brand_voice}"
            """

        # --- RAG-LITE INTERNAL LINKING INJECTION ---
        internal_linking_injection = ""
        if previous_links and len(previous_links) > 0:
            links_context = "\n".join([f"- {link['keyword']}: {link['url']}" for link in previous_links])
            internal_linking_injection = f"""
            CRITICAL SEO REQUIREMENT (INTERNAL LINKING):
            Here are some previously published articles from this author:
            {links_context}
            You MUST naturally weave exactly 1 or 2 of these links into the article text using standard Markdown hyperlink formatting. Do not force it, make it contextual.
            """

        # Step 3: Agent 2 - The Master Copywriter
        logging.info("Agent 2 (Writer) is drafting the content with Live Context...")
        
        # NOTE: Added {internal_linking_injection} right below brand_voice_injection
        writer_prompt = f"""
        You are a top-tier Senior Technical Writer specializing in the '{domain}' niche.
        Write a highly structured, authoritative Deep-Dive for the keyword '{keyword}'.
        {brand_voice_injection}
        {internal_linking_injection}
        
        CRITICAL REAL-TIME CONTEXT:
        You MUST base your facts, tools, and assertions on this live search data to ensure your knowledge is 100% up-to-date for 2026. 
        If a certification, framework, or tool is deprecated, you MUST state the modern alternative:
        {serp_data}
        
        Strictly follow this outline:
        {outline}
        
        REQUIRED STRUCTURAL ELEMENTS:
        1. Start with a "TL;DR" summary bulleted list at the top.
        2. Use the PAS Framework in the introduction: Problem, Agitate, Solution.
        3. Include ONE Markdown Table. The table MUST be fully completed with a header row, a separator row (e.g., |---|---|---|), and all data rows.
        4. Include realistic code snippets using ``` blocks if the domain is Technical.
        
        CRITICAL COMPLETION RULES (DO NOT FAIL THESE):
        - Target Length: Around 800 to 1200 words. 
        - YOUR ABSOLUTE HIGHEST PRIORITY IS COMPLETING THE ARTICLE. 
        - NEVER stop generating mid-sentence, mid-paragraph, or mid-table.
        - You MUST complete the article by writing a final "## Final Thoughts" section that ends with a definitive concluding sentence.
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
        # Raising the exception here so routes.py can catch it and send a clean 500 error to the UI
        raise Exception(f"AI Pipeline Failed: {str(e)}")


def generate_socials(article_content: str, api_key: str) -> dict:
    """Agent 4: Takes a finished article and derives viral social media copy."""
    if not api_key:
        return {"twitter": "", "linkedin": ""}
        
    try:
        client = genai.Client(api_key=api_key)
        model_id = 'gemini-2.5-flash-lite'
        
        social_prompt = f"""
        You are an elite Social Media Ghostwriter. 
        The author just published a blog titled: "{article_content[:100]}..."
        
        TASK:
        1. Write a viral X (Twitter) "Announcement" tweet. It must include a powerful hook, a brief value prop, and a placeholder [INSERT LINK HERE]. Use emojis.
        2. Write a professional LinkedIn "Published" post. Focus on the 'Why it matters' for the industry and end with "Read the full deep-dive here: [INSERT LINK HERE]".
        
        Keep them SHORT and PUNCHY. Do not summarize the whole blog.
        
        STRICT JSON FORMAT:
        {{
            "twitter": "Just dropped a new deep-dive on... [INSERT LINK HERE]",
            "linkedin": "I'm excited to share my latest article... [INSERT LINK HERE]"
        }}
        """
        
        response = client.models.generate_content(
            model=model_id,
            contents=social_prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json"
            )
        )
        
        return json.loads(response.text)
        
    except Exception as e:
        logging.error(f"Social Generation failed: {e}")
        return {"twitter": "Failed to generate.", "linkedin": "Failed to generate."}