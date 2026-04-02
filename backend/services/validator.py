import logging
import math
from sentence_transformers import SentenceTransformer, util
import textstat

logger = logging.getLogger(__name__)

# Load the ML Model ONCE when the module initializes (Lightweight: ~80MB)
logger.info("Loading ML Semantic Model (all-MiniLM-L6-v2)...")
try:
    similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logger.error(f"Failed to load ML model: {e}")
    similarity_model = None

def calculate_seo_score(content: str, keyword: str, domain: str) -> int:
    """Hybrid SEO Scoring: Semantic ML + Keyword Density"""
    if not similarity_model or not content:
        return 50 # Fallback score
        
    try:
        # 1. THE ML CHECK (Semantic Relevance)
        # Does the content actually mean the same thing as the keyword?
        target_embedding = similarity_model.encode(f"{keyword} in the {domain} industry")
        content_embedding = similarity_model.encode(content[:1000]) # Check first 1000 chars to save memory
        
        # Returns a tensor, get the float value
        cosine_score = util.cos_sim(target_embedding, content_embedding).item()
        semantic_score = max(0, min(100, int(cosine_score * 100)))

        # 2. THE HEURISTIC CHECK (Density)
        keyword_count = content.lower().count(keyword.lower())
        density_score = min(100, (keyword_count / 3) * 100) # Expect at least 3 mentions

        # Hybrid Weighting: 70% Meaning, 30% Exact Match
        final_score = int((semantic_score * 0.7) + (density_score * 0.3))
        
        # Boost score slightly if domain is mentioned
        if domain.lower() in content.lower():
            final_score = min(100, final_score + 5)
            
        return final_score

    except Exception as e:
        logger.error(f"SEO ML Scoring Error: {e}")
        return 50


def calculate_humanness_score(content: str) -> dict:
    """Heuristic Proxy for AI Detection (Burstiness & Readability)"""
    if not content:
        return {"naturalness": 0, "readability": "Unknown"}

    try:
        # 1. Readability Level
        flesch_score = textstat.flesch_reading_ease(content)
        if flesch_score > 70:
            readability_level = "Easy (Conversational)"
        elif flesch_score > 50:
            readability_level = "Standard (Professional)"
        else:
            readability_level = "Hard (Academic/Technical)"

        # 2. Burstiness (Sentence Length Variance)
        # AI tends to write sentences of exact similar lengths. Humans vary them.
        sentences = content.replace('!', '.').replace('?', '.').split('.')
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        
        if len(sentences) < 3:
            return {"naturalness": 50, "readability": readability_level}

        lengths = [len(s.split()) for s in sentences]
        avg_length = sum(lengths) / len(lengths)
        
        # Calculate Standard Deviation (Variance)
        variance = sum((x - avg_length) ** 2 for x in lengths) / len(lengths)
        std_dev = math.sqrt(variance)

        # Baseline: If std_dev is > 8, it's very "bursty" (Human-like)
        naturalness = min(100, int((std_dev / 8.0) * 100))
        
        # Penalize if it's too repetitive (AI loves transition words like "Moreover", "Furthermore")
        ai_tells = ["furthermore", "moreover", "in conclusion", "delve", "testament"]
        lower_content = content.lower()
        for tell in ai_tells:
            if lower_content.count(tell) > 1:
                naturalness -= 5

        return {
            "naturalness": max(0, naturalness), # Ensure it doesn't drop below 0
            "readability": readability_level
        }

    except Exception as e:
        logger.error(f"Humanness Scoring Error: {e}")
        return {"naturalness": 50, "readability": "Error"}