import re

def calculate_readability(text: str) -> str:
    """A lightweight heuristic to estimate reading level without heavy external libraries."""
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    
    if not words or not sentences: return "Unknown"
    
    avg_sentence_length = len(words) / len(sentences)
    complex_words = [word for word in words if len(word) > 6]
    complex_ratio = len(complex_words) / len(words)
    
    if avg_sentence_length > 20 and complex_ratio > 0.3:
        return "Advanced / Academic"
    elif avg_sentence_length > 15 and complex_ratio > 0.2:
        return "Professional / College Level"
    else:
        return "Highly Accessible (Grade 8-10)"

def calculate_seo_metrics(keyword: str, text: str, domain: str) -> dict:
    word_count = len(text.split())
    if word_count == 0:
        return {"seo_score": 0, "keyword_density": 0, "naturalness": 0, "snippet_readiness": "Low", "readability": "Unknown"}

    # 1. Keyword Density
    keyword_count = len(re.findall(re.escape(keyword), text, re.IGNORECASE))
    density = (keyword_count / word_count) * 100 if word_count > 0 else 0

    # 2. AI Detection & Naturalness Score
    ai_buzzwords = ['delve', 'testament', 'landscape', 'crucial', 'transformative', 'realm', 'tapestry', 'furthermore', 'beacon', 'moreover']
    buzzword_count = sum(1 for word in ai_buzzwords if word in text.lower())
    naturalness_score = max(0, 100 - (buzzword_count * 8))

    # 3. Snippet Readiness
    has_headers = bool(re.search(r'##+ ', text))
    has_lists = bool(re.search(r'(\*|\-) ', text))
    
    # Domain-Specific Checks
    has_code_blocks = bool(re.search(r'```', text))
    has_tables = bool(re.search(r'\|.*\|', text))
    
    snippet_readiness = "High" if (has_headers and has_lists) else "Medium"

    # 4. Domain-Adjusted SEO Score
    seo_score = 60
    if 0.5 <= density <= 2.5: seo_score += 15
    if has_headers: seo_score += 10
    if has_lists: seo_score += 5
    if has_tables: seo_score += 5
    
    # Domain penalty/bonuses
    if domain.lower() == "technical" and has_code_blocks:
        seo_score += 5
    elif domain.lower() == "technical" and not has_code_blocks:
        seo_score -= 10 # Penalize tech blogs with no code
        
    readability = calculate_readability(text)

    return {
        "seo_score": min(100, seo_score),
        "keyword_density": round(density, 2),
        "naturalness": naturalness_score,
        "snippet_readiness": snippet_readiness,
        "readability_level": readability
    }