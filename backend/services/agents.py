import logging
import json
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def generate_seo_blog(keyword: str, serp_data: list, domain: str = "General", api_key: str = None, brand_voice: str = None, previous_links: list = None) -> dict:
    """
    The 'Brain' of the operation.
    Built on the google-genai SDK using the blazing fast Gemini 2.5 Flash model.
    Upgraded to an Enterprise Deep-Read Generator with BYOK, Brand Voice, and Semantic RAG-Lite.
    """
    logging.info(f"Initializing Enterprise AI Pipeline for domain: '{domain}'...")
    
    if not api_key:
        logging.error("API Key was not provided by the Router!")
        raise ValueError("Gemini API Key is required to run the pipeline. Check your Vault Settings.")
        
    try:
        client = genai.Client(api_key=api_key)
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
            config=types.GenerateContentConfig(temperature=0.2)
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

        # --- UPGRADED RAG-LITE INTERNAL LINKING INJECTION ---
        internal_linking_injection = ""
        if previous_links and len(previous_links) > 0:
            # We now inject the SUMMARY of the past article, giving the AI true semantic context!
            links_context = "\n".join([f"- Topic: {link['keyword']} | URL: {link['url']} | Context: {link.get('summary', 'Related article.')}" for link in previous_links])
            internal_linking_injection = f"""
            CRITICAL SEO REQUIREMENT (INTERNAL LINKING):
            Here are some previously published articles from this author, along with what they are about:
            {links_context}
            You MUST naturally weave exactly 1 or 2 of these links into the article text using standard Markdown hyperlink formatting. 
            Use the Context provided to make the transition into the link make logical sense. Do not force it.
            """

        # Step 3: Agent 2 - The Master Copywriter
        logging.info("Agent 2 (Writer) is drafting the content with Live Context...")
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
        
        CRITICAL COMPLETION RULES:
        - Target Length: Around 800 to 1200 words. 
        - NEVER stop generating mid-sentence, mid-paragraph, or mid-table.
        - You MUST complete the article by writing a final "## Final Thoughts" section that ends with a definitive concluding sentence.
        """
        
        blog_response = client.models.generate_content(
            model=model_id,
            contents=writer_prompt,
            config=types.GenerateContentConfig(
                temperature=0.5, 
                max_output_tokens=8192
            )
        )
        final_blog = blog_response.text

        # --- NEW: Step 4: Agent 3 - The RAG-Lite Summarizer ---
        logging.info("Agent 3 (Summarizer) is compressing the draft for future RAG context...")
        summary_prompt = f"""
        Read the following blog post and summarize its core value proposition in exactly 5 concise sentences. 
        This summary will be used to train an AI on what this article is about.
        Do not use introductory phrases, just return the 5 sentences.
        
        BLOG CONTENT:
        {final_blog[:4000]}...
        """
        summary_response = client.models.generate_content(
            model='gemini-2.5-flash-lite', # Using lite for speed and lower cost
            contents=summary_prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        rag_summary = summary_response.text.strip()
        
        logging.info("Blog generation and Semantic RAG compression complete!")
        return {
            "outline": outline,
            "blog_content": final_blog,
            "summary": rag_summary # Passed back to routes.py to save to DB!
        }
        
    except Exception as e:
        logging.error(f"Gemini AI Generation failed: {e}")
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
    

def call_the_muse(user_input: str, api_key: str) -> str:
    """The Muse: Neo-Brutalist Idea Bot using Gemini SDK"""
    if not api_key:
        return "NO KEY, NO SPARK. CHECK YOUR VAULT."
        
    try:
        client = genai.Client(api_key=api_key)
        model_id = 'gemini-2.5-flash-lite'
        
        system_prompt = (
            "You are 'The Muse', a Neo-Brutalist creative strategist. "
            "Your ONLY mission is to spark content ideas, headlines, and outlines. "
            "If the user asks for code, math, or general facts, reply: 'MY SPARK IS FOR STORIES ONLY. ASK FOR AN IDEA.' "
            "Keep responses under 60 words. Use punchy, loud, and authoritative language. "
            "Do not use markdown headers, just raw, powerful text."
        )
        
        response = client.models.generate_content(
            model=model_id,
            contents=f"{system_prompt}\n\nUSER SIGNAL: {user_input}",
            config=types.GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=150
            )
        )
        
        return response.text
        
    except Exception as e:
        logging.error(f"Idea Generation failed: {e}")
        return "THE SPARK HAS FLICKERED. TRY AGAIN."


# --- MEGA UPDATE: THE STUDIO HITL EDITOR ---

def apply_hitl_correction(current_content: str, instruction: str, api_key: str) -> str:
    """
    Agent 5: Human-In-The-Loop Editor. 
    Takes the user's specific text commands and surgically updates the current draft.
    """
    if not api_key:
        raise ValueError("API Key missing for HITL Correction.")
        
    try:
        client = genai.Client(api_key=api_key)
        # Using the heavy Flash model here because editing long markdown requires high reasoning
        model_id = 'gemini-2.5-flash' 
        
        editor_prompt = f"""
        You are an elite Senior Technical Editor.
        Below is a draft of an article currently in progress.
        
        CURRENT DRAFT:
        ---
        {current_content}
        ---
        
        THE INSTRUCTION FROM THE HEAD EDITOR:
        "{instruction}"
        
        YOUR TASK:
        Apply the Head Editor's instruction to the draft perfectly. 
        - If they ask to rewrite a specific section, rewrite ONLY that section and keep the rest intact.
        - If they ask to change the overall tone, rewrite the entire draft to match the new tone.
        - DO NOT add conversational filler (e.g., "Here is the revised draft").
        - Return ONLY the raw, updated Markdown text so it can seamlessly replace the old text in the user's editor.
        """
        
        response = client.models.generate_content(
            model=model_id,
            contents=editor_prompt,
            config=types.GenerateContentConfig(
                temperature=0.4, # Keep it relatively low to prevent wild hallucinated additions
                max_output_tokens=8192
            )
        )
        
        return response.text.strip()
        
    except Exception as e:
        logging.error(f"HITL Correction failed: {e}")
        raise Exception("The Editor Agent failed to process your correction. Please try again.")