"""
NyayaGuide Legal Retrieval Service (RAG Pre-processing)
Orchestrates topic detection, legal search, citation extraction,
and packages retrieved provisions for grounded explanation.
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from legal.search import search_provisions
from legal.validate import validate_provisions_against_db

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "instance" / "nyayaguide.db"

# Keyword to Topic heuristics for auto-detection
TOPIC_KEYWORD_MAP = {
    "topic_cybercrime": ["scam", "fraud", "hacked", "phishing", "otp", "cyber", "online fraud", "upi scam", "telegram scam", "digital arrest", "fake call", "crypto"],
    "topic_consumer": ["seller", "delivery", "delivered", "ordered", "amazon", "flipkart", "refund", "defective", "warranty", "replacement", "damaged product", "fake product"],
    "topic_employment": ["salary", "employer", "company", "boss", "terminated", "fired", "resigned", "notice period", "severance", "pf", "gratuity", "unpaid wages"],
    "topic_privacy": ["photograph", "photos", "photo", "morphed", "stalking", "harassment", "whatsapp", "instagram", "leaked", "defamation", "blackmail", "camera", "private video"],
    "topic_property": ["rent", "landlord", "tenant", "deposit", "lease", "eviction", "flat", "security deposit", "brokerage", "house owner", "tenancy"],
    "topic_banking": ["cheque", "check", "bounce", "bounced", "bank", "atm", "unauthorized transaction", "recovery agent", "loan emi", "credit card"],
    "topic_road_accidents": ["accident", "car crash", "hit and run", "vehicle", "bike hit", "injured on road", "driver", "mact", "third party insurance"],
    "topic_family": ["maintenance", "domestic violence", "husband", "wife", "divorce", "in-laws", "cruelty", "dowry", "child custody", "alimony"],
    "topic_constitutional": ["police custody", "arrested without warrant", "protest", "censorship", "discrimination", "caste", "fundamental right", "illegal detention", "writ"],
    "topic_education": ["school", "college", "university", "ragging", "certificates withheld", "fee refund", "exam cancellation", "degree"],
}

def detect_topic(query_text: str) -> Optional[str]:
    """Infers the most appropriate legal topic from situation keywords."""
    query_lower = query_text.lower()
    best_topic = None
    best_matches = 0
    
    for topic_id, keywords in TOPIC_KEYWORD_MAP.items():
        matches = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", query_lower))
        if matches > best_matches:
            best_matches = matches
            best_topic = topic_id
            
    return best_topic if best_matches > 0 else "topic_other"

def retrieve_grounding_context(
    query_text: str,
    jurisdiction_id: str = "IN-CENTRAL",
    topic_id: Optional[str] = None,
    incident_date: Optional[str] = None,
    limit: int = 6
) -> Dict[str, Any]:
    """
    Retrieves grounded legal context from local database.
    Returns provisions, detected topics, and jurisdiction context.
    """
    if not topic_id or topic_id == "auto":
        topic_id = detect_topic(query_text)
        
    provisions = search_provisions(
        query_text=query_text,
        jurisdiction_id=jurisdiction_id,
        topic_id=topic_id,
        incident_date_str=incident_date,
        limit=limit
    )
    
    return {
        "query": query_text,
        "jurisdiction_id": jurisdiction_id,
        "topic_id": topic_id,
        "incident_date": incident_date,
        "retrieved_provisions": provisions,
        "provisions_count": len(provisions)
    }
