"""
NyayaGuide Legal Text Normalization & Sanitization
Standardizes citations, removes noise, normalizes legal phrasing,
and prevents query syntax injection for FTS5 full-text search.
"""
import re
import unicodedata
from datetime import datetime
from typing import Optional, Tuple

# Common Indian legal abbreviations mapping
LEGAL_ABBREVIATIONS = {
    r"\bsec\b\.?": "section",
    r"\bsecs\b\.?": "sections",
    r"\bart\b\.?": "article",
    r"\barts\b\.?": "articles",
    r"\bcl\b\.?": "clause",
    r"\bcls\b\.?": "clauses",
    r"\bpara\b\.?": "paragraph",
    r"\bsub-sec\b\.?": "sub-section",
    r"\bu/s\b": "under section",
    r"\br/w\b": "read with",
    r"\bbns\b": "bharatiya nyaya sanhita",
    r"\bbnss\b": "bharatiya nagarik suraksha sanhita",
    r"\bbsa\b": "bharatiya sakshya adhiniyam",
    r"\bipc\b": "indian penal code",
    r"\bcrpc\b": "code of criminal procedure",
    r"\bcpa\b": "consumer protection act",
    r"\bit act\b": "information technology act",
}

def clean_text(text: str) -> str:
    """Removes unusual characters, normalizes unicode, and collapses whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    # Replace non-standard spaces and linebreaks
    text = re.sub(r"[\r\t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()

def sanitize_fts_query(query: str) -> str:
    """
    Sanitizes user query for safe execution in SQLite FTS5 MATCH clause.
    Prevents syntax errors from lone quotes, boolean operators, asterisks, etc.
    """
    if not query:
        return ""
    
    # Strip FTS control characters that break queries if malformed
    clean = re.sub(r'[^\w\s\-\'"]', " ", query)
    tokens = clean.split()
    
    # Filter out empty or pure punctuation tokens
    safe_tokens = []
    for token in tokens:
        token = token.strip('-"*\'')
        if token and len(token) > 1 and token.lower() not in {"and", "or", "not", "near"}:
            safe_tokens.append(f'"{token}"')
    
    if not safe_tokens:
        # Fallback to simple alphanumeric words
        words = re.findall(r"\w+", query)
        safe_tokens = [f'"{w}"' for w in words if len(w) > 1]
        
    return " OR ".join(safe_tokens)

def parse_incident_date(date_str: Optional[str]) -> Tuple[Optional[datetime], bool]:
    """
    Parses incident date string.
    Returns (datetime_obj, is_post_bns_transition).
    BNS transition milestone is 2024-07-01.
    """
    if not date_str:
        # Defaults to current era (post-transition)
        return None, True
    
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %Y", "%B %Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            is_post_bns = dt >= datetime(2024, 7, 1)
            return dt, is_post_bns
        except ValueError:
            continue
            
    return None, True

def extract_cited_sections(text: str) -> list:
    """Finds referenced section/article numbers from text like 'Section 420' or 'Article 21'."""
    pattern = r"\b(section|sec|article|art)\s*([0-9]+[A-Za-z]*(?:\([0-9a-z]+\))*)"
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    results = []
    for kind, num in matches:
        k = "article" if kind.lower().startswith("art") else "section"
        results.append({"type": k, "number": num})
    return results
