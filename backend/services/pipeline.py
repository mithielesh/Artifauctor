import os
import time
import json
import logging
from typing import List
from pydantic import BaseModel, Field
from tavily import TavilyClient
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

USE_MOCK_DATA = False   # Set to True if you want to test routing without burning API tokens
SLEEP_TIME = 15         # Seconds to wait between agents to avoid 429 Rate Limits

# --- 1. SCHEMAS (The Brain & Structured Outputs) ---

class ArticleState(BaseModel):
    keyword: str
    domain: str = "General"
    raw_research_data: str = ""  
    current_draft: str = ""
    
    # Granular Feedback Channels
    hallucination_errors: List[str] = []
    seo_errors: List[str] = []
    tone_errors: List[str] = []
    
    # Meta Tracking
    loop_count: int = 0
    final_seo_score: int = 0
    status: str = "Initializing"

class FactCheckSchema(BaseModel):
    hallucination_errors: list[str] = Field(description="List of claims in the draft that contradict or are missing from the research. Empty if perfectly accurate.")

class JudgeSchema(BaseModel):
    seo_score: int = Field(description="Score from 0 to 100 based on keyword density and headings.")
    seo_errors: list[str] = Field(description="Specific instructions to fix SEO. Empty if score is > 85.")
    tone_errors: list[str] = Field(description="Specific instructions to fix robotic or clunky tone. Empty if natural.")

# --- 2. NODE 1: THE RESEARCHER ---
def run_researcher(state: ArticleState) -> ArticleState:
    state.status = "Agent 1: Synthesizing Research..."
    logging.info(f"[{state.status}] Keyword: {state.keyword}")
    
    if USE_MOCK_DATA:
        state.raw_research_data = "MOCK BRIEF: Agentic AI will dominate by 2026. Key tools include LangGraph and MCP."
        state.status = "Research Synthesized (MOCK)"
        return state

    try:
        tavily_key = os.getenv("TAVILY_API_KEY")
        tavily_client = TavilyClient(api_key=tavily_key)
        raw_response = tavily_client.search(query=state.keyword, search_depth="advanced", max_results=4)
        raw_context = "\n".join([f"URL: {res['url']}\nSnippet: {res['content']}" for res in raw_response.get("results", [])])
        
        gemini_key = os.getenv("GEMINI_API_KEY")
        ai_client = genai.Client(api_key=gemini_key)
        
        prompt = f"Synthesize this raw web data into a clean, highly concentrated 'Research Brief':\n{raw_context}"
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        
        state.raw_research_data = response.text.strip()
        state.status = "Research Synthesized"
        
    except Exception as e:
        logging.error(f"Researcher Failed: {e}")
        state.status = "Failed: Research Error"
        
    return state

# --- 3. NODE 2: THE DRAFTER ---
def run_drafter(state: ArticleState) -> ArticleState:
    state.status = f"Agent 2: Drafting content (Loop {state.loop_count})..."
    logging.info(state.status)
    
    if USE_MOCK_DATA:
        state.current_draft = f"# {state.keyword}\nAgentic AI is the future. It is very fast."
        state.status = "Drafting Complete (MOCK)"
        return state

    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=gemini_key)
        
        feedback_context = ""
        if state.loop_count > 0:
            feedback_context = "CRITICAL: You are rewriting an existing draft because it failed quality checks.\n"
            if state.seo_errors: feedback_context += f"- SEO Fixes: {' '.join(state.seo_errors)}\n"
            if state.tone_errors: feedback_context += f"- Tone Fixes: {' '.join(state.tone_errors)}\n"
            if state.hallucination_errors: feedback_context += f"- Fact Fixes: {' '.join(state.hallucination_errors)}\n"
            feedback_context += f"\nCURRENT DRAFT TO FIX:\n{state.current_draft}\n\n"
            
        prompt = f"""
        You are an elite Technical Writer. Target Keyword: '{state.keyword}'
        {feedback_context}
        Write/rewrite a highly structured Deep-Dive article based ONLY on this research:
        {state.raw_research_data}
        Requirements: H1 Title, Markdown, paragraphs under 4 sentences. NO conversational filler.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.4) 
        )
        
        state.current_draft = response.text.strip()
        state.status = "Drafting Complete"
        
    except Exception as e:
        logging.error(f"Drafter Failed: {e}")
        state.status = "Failed: Drafting Error"
        
    return state

# --- 4. NODE 3: THE FACT-CHECKER ---
def run_fact_checker(state: ArticleState) -> ArticleState:
    state.status = "Agent 3: Fact-Checking against Research..."
    logging.info(state.status)
    
    if USE_MOCK_DATA: return state

    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=gemini_key)
        
        prompt = f"""
        You are a strict Fact-Checker. 
        If the DRAFT includes statistics or claims not present in the RESEARCH BRIEF, it is a hallucination.
        RESEARCH BRIEF: {state.raw_research_data}
        DRAFT: {state.current_draft}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=FactCheckSchema
            )
        )
        
        result = json.loads(response.text)
        state.hallucination_errors = result.get("hallucination_errors", [])
        
        if state.hallucination_errors:
            logging.warning(f"Fact-Checker found {len(state.hallucination_errors)} errors.")
        else:
            logging.info("Fact-Checker: PASSED.")
            
    except Exception as e:
        logging.error(f"Fact-Checker Failed: {e}")
        
    return state

# --- 5. NODE 4: THE JUDGE ---
def run_judge(state: ArticleState) -> ArticleState:
    state.status = "Agent 4: Judging SEO and Tone..."
    logging.info(state.status)
    
    if USE_MOCK_DATA:
        state.final_seo_score = 90
        return state

    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=gemini_key)
        
        prompt = f"""
        You are the Final Editor. Grade this draft for the keyword: '{state.keyword}'.
        1. SEO: Are there clear headings? Is the keyword used naturally?
        2. Tone: Does it sound robotic?
        DRAFT: {state.current_draft}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=JudgeSchema
            )
        )
        
        result = json.loads(response.text)
        state.final_seo_score = result.get("seo_score", 0)
        state.seo_errors = result.get("seo_errors", [])
        state.tone_errors = result.get("tone_errors", [])
        
        logging.info(f"Judge Score: {state.final_seo_score}/100")
        
    except Exception as e:
        logging.error(f"Judge Failed: {e}")
        
    return state

# --- 6. THE ORCHESTRATOR LOOP (Testing Sandbox) ---
if __name__ == "__main__":
    print("\n=== STARTING V3.5 AGENTIC GRAPH TEST ===")
    
    # 1. Initialize State
    current_state = ArticleState(keyword="The future of Agentic AI in web development", domain="Technology")
    
    # 2. Run Node 1
    current_state = run_researcher(current_state)
    logging.info(f"Sleeping for {SLEEP_TIME} seconds to respect API limits...")
    time.sleep(SLEEP_TIME)
    
    # 3. The Multi-Agent Assembly Line
    MAX_LOOPS = 3
    
    while current_state.loop_count < MAX_LOOPS:
        print(f"\n--- STARTING PIPELINE LOOP {current_state.loop_count + 1} ---")
        
        current_state = run_drafter(current_state)
        logging.info(f"Sleeping for {SLEEP_TIME} seconds...")
        time.sleep(SLEEP_TIME)
        
        current_state = run_fact_checker(current_state)
        logging.info(f"Sleeping for {SLEEP_TIME} seconds...")
        time.sleep(SLEEP_TIME)
        
        current_state = run_judge(current_state)
        
        # 4. Check Exit Conditions
        has_errors = any([current_state.hallucination_errors, current_state.seo_errors, current_state.tone_errors])
        
        if not has_errors and current_state.final_seo_score >= 85:
            current_state.status = "Completed Successfully"
            logging.info("🎉 Article passed all checks!")
            break
        else:
            logging.warning("Article failed checks. Sending back to Drafter...")
            current_state.loop_count += 1
            logging.info(f"Sleeping for {SLEEP_TIME} seconds before rewrite...")
            time.sleep(SLEEP_TIME) 
            
    if current_state.loop_count >= MAX_LOOPS:
        current_state.status = "Failed: Max Loops Reached"
        logging.error("Pipeline aborted to prevent infinite loop.")
        
    print(f"\n=== FINAL PIPELINE STATUS: {current_state.status} ===")
    print(f"Final SEO Score: {current_state.final_seo_score}")
    print("\n--- FINAL DRAFT PREVIEW ---")
    print(f"{current_state.current_draft[:500]}...")