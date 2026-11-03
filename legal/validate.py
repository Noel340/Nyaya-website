"""
NyayaGuide Validation Service
Ensures strict verification of citations, prevents AI hallucinations,
validates provision IDs against the database, and checks source URLs.
"""
import re
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

# Trusted government and statutory domains
TRUSTED_LEGAL_DOMAINS = {
    "indiacode.nic.in",
    "legislative.gov.in",
    "nalsa.gov.in",
    "cybercrime.gov.in",
    "consumerhelpline.gov.in",
    "ecourts.gov.in",
    "main.sci.gov.in",
    "barcouncilofindia.org",
    "egazette.gov.in",
    "ncw.nic.in"
}

def is_trusted_official_url(url: str) -> bool:
    """Verifies that a source URL originates from an official, trusted government or statutory portal."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Check domain or known subdomains (.gov.in, .nic.in, etc.)
        if domain in TRUSTED_LEGAL_DOMAINS:
            return True
        if domain.endswith(".gov.in") or domain.endswith(".nic.in"):
            return True
        return False
    except Exception:
        return False

def validate_provisions_against_db(db_conn: sqlite3.Connection, provision_ids: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validates a list of provision IDs against the local database.
    Returns (valid_provisions, rejected_ids).
    Crucial anti-hallucination shield for LLM output.
    """
    if not provision_ids:
        return [], []
    
    placeholders = ",".join(["?"] * len(provision_ids))
    query = f"""
        SELECT 
            p.id, p.act_id, a.short_title as act_title, p.provision_type, 
            p.provision_number, p.heading, p.plain_english_summary, 
            p.official_text, p.why_relevant_explanation, p.conditions_to_establish, 
            p.exceptions_and_limitations, p.effective_from, p.effective_until, 
            p.status, p.source_url, p.verification_status, a.category, a.jurisdiction_id
        FROM legal_provisions p
        JOIN legal_acts a ON p.act_id = a.id
        WHERE p.id IN ({placeholders})
    """
    
    cursor = db_conn.cursor()
    cursor.execute(query, provision_ids)
    rows = cursor.fetchall()
    
    col_names = [description[0] for description in cursor.description]
    found_map = {}
    for r in rows:
        item = dict(zip(col_names, r))
        # Ensure source URL is validated
        item["is_official_source"] = is_trusted_official_url(item.get("source_url", ""))
        found_map[item["id"]] = item
        
    valid_provisions = []
    rejected_ids = []
    
    for pid in provision_ids:
        if pid in found_map:
            valid_provisions.append(found_map[pid])
        else:
            rejected_ids.append(pid)
            
    return valid_provisions, rejected_ids

def validate_legal_claim(claim_text: str, source_text: str) -> bool:
    """Checks if a factual assertion is supported by source text."""
    if not claim_text or not source_text:
        return False
    # Simple lexical overlap heuristic for MVP verification
    claim_words = set(re.findall(r"\w{4,}", claim_text.lower()))
    source_words = set(re.findall(r"\w{4,}", source_text.lower()))
    if not claim_words:
        return True
    overlap = len(claim_words.intersection(source_words)) / len(claim_words)
    return overlap >= 0.25
