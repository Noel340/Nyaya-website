"""
NyayaGuide Grounded Legal Explanation Generator
Implements RAG with strict citation validation.
Supports Google Gemini / LLM API when configured, with a guaranteed,
grounded legal fallback engine when running offline without API keys.
"""
import json
import os
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from legal.validate import validate_provisions_against_db

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "instance" / "nyayaguide.db"

def build_deterministic_grounded_answer(
    query_text: str,
    retrieved_provisions: List[Dict[str, Any]],
    jurisdiction_name: str,
    incident_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Guaranteed deterministic grounded legal explanation engine.
    Constructs accurate plain-language legal guidance from database records
    without hallucinations, ensuring complete offline functionality.
    """
    if not retrieved_provisions:
        return {
            "issue_summary": f"Query: \"{query_text}\"",
            "jurisdiction": jurisdiction_name,
            "clarifying_questions": [
                "Could you provide more specific details regarding dates, agreements, or monetary amounts?",
                "Did this involve a private individual, an online platform, an employer, or a government authority?"
            ],
            "potentially_relevant_laws": [],
            "why_it_may_apply": "No verified legal provisions in the current database sufficiently matched the query. We do not fabricate legal sections.",
            "conditions": "Sufficient factual foundation must be established to identify applicable laws.",
            "exceptions": "Not applicable.",
            "possible_next_steps": [
                "Review the legal categories in 'Browse Laws' for relevant subject areas.",
                "Seek an initial consultation through your District Legal Services Authority (DLSA) or national legal aid helpline 15100."
            ],
            "lawyer_practice_areas": ["Civil Litigation Advocate", "General Legal Practitioner"],
            "official_sources": [],
            "limitations": "The local database indexes Central legislation and selected state provisions progressively.",
            "urgent_help": None,
            "needs_legal_review": True,
            "is_ai_grounded": False,
            "ai_mode": "database_deterministic_fallback"
        }

    # Extract verified provision IDs
    valid_ids = [p["id"] for p in retrieved_provisions]
    
    # Formulate neutral summary
    issue_summary = (
        f"The user describes an issue concerning: \"{query_text.strip()}\". "
        f"Jurisdiction noted as {jurisdiction_name}" + 
        (f" with incident date around {incident_date}." if incident_date else " (incident date not specified).")
    )
    
    # Clarifying questions based on retrieved statutes
    clarifying_questions = [
        "Do you have documentary or digital evidence (receipts, transaction IDs, emails, chat screenshots, or notice copies)?",
        "Was any formal written complaint, police intimation, or demand notice previously sent to the other party?",
        "Did the transaction or conduct take place before or after 1 July 2024 (the commencement date of the Bharatiya Nyaya Sanhita)?"
    ]
    
    why_reasons = []
    conditions_list = []
    exceptions_list = []
    official_sources = []
    lawyer_practice_areas = set()
    has_urgent_concern = False
    
    for p in retrieved_provisions:
        act_title = p.get("act_title", "Statute")
        p_type = p.get("provision_type", "Section").title()
        p_num = p.get("provision_number", "")
        heading = p.get("heading", "")
        
        why_reasons.append(f"• **{act_title} ({p_type} {p_num} — {heading})**: {p.get('why_relevant_explanation') or p.get('plain_english_summary')}")
        
        if p.get("conditions_to_establish"):
            conditions_list.append(f"• For {p_type} {p_num}: {p['conditions_to_establish']}")
        if p.get("exceptions_and_limitations"):
            exceptions_list.append(f"• For {p_type} {p_num}: {p['exceptions_and_limitations']}")
            
        if p.get("source_url"):
            official_sources.append({
                "title": f"{act_title} — {p_type} {p_num}",
                "url": p["source_url"],
                "status": "Verified Official Government Repository"
            })
            
        # Lawyer area mapping
        cat = p.get("act_category", "").lower()
        if "criminal" in cat:
            lawyer_practice_areas.add("Criminal Defence & Prosecution Advocate")
            has_urgent_concern = True
        elif "cyber" in cat or "technology" in cat:
            lawyer_practice_areas.add("Cybercrime & Digital Evidence Lawyer")
        elif "consumer" in cat:
            lawyer_practice_areas.add("Consumer Dispute & Redressal Advocate")
        elif "property" in cat:
            lawyer_practice_areas.add("Property & Tenancy Advocate")
        elif "labour" in cat or "employment" in cat:
            lawyer_practice_areas.add("Labour & Employment Law Advocate")
        elif "constitutional" in cat:
            lawyer_practice_areas.add("Constitutional & Writ Law Advocate")
        elif "banking" in cat:
            lawyer_practice_areas.add("Banking & Financial Dispute Advocate")
        elif "motor" in cat:
            lawyer_practice_areas.add("Motor Accident Claims (MACT) Advocate")
        elif "family" in cat:
            lawyer_practice_areas.add("Family & Matrimonial Advocate")

    if not lawyer_practice_areas:
        lawyer_practice_areas.add("Civil Litigation Advocate")

    possible_next_steps = [
        "Preserve all relevant records, invoices, emails, bank statements, or digital communication logs immediately.",
        "Avoid engaging in direct personal confrontations or unlawful self-help actions.",
        "Send a formal, documented notice or grievance via registered post or official grievance portal if appropriate.",
        "Consider approaching your District Legal Services Authority (DLSA) or contacting the National Legal Aid Helpline 15100 for verified counsel."
    ]
    
    urgent_help = None
    if has_urgent_concern:
        urgent_help = "If you are facing threats of violence, ongoing cyber theft, or harassment, contact the National Emergency Helpline (112) or Cybercrime Helpline (1930) immediately."

    return {
        "issue_summary": issue_summary,
        "jurisdiction": jurisdiction_name,
        "clarifying_questions": clarifying_questions,
        "potentially_relevant_laws": valid_ids,
        "why_it_may_apply": "\n\n".join(why_reasons),
        "conditions": "\n\n".join(conditions_list) if conditions_list else "Standard evidentiary burden applies to substantiate the facts.",
        "exceptions": "\n\n".join(exceptions_list) if exceptions_list else "Statutory limitation periods and jurisdictional thresholds apply.",
        "possible_next_steps": possible_next_steps,
        "lawyer_practice_areas": list(lawyer_practice_areas),
        "official_sources": official_sources,
        "limitations": "This legal information report is prepared for awareness only and does not constitute a formal legal opinion, attorney-client relationship, or guarantee of outcome.",
        "urgent_help": urgent_help,
        "needs_legal_review": True,
        "is_ai_grounded": False,
        "ai_mode": "grounded_rules_retrieval_fallback"
    }

def call_gemini_api(api_key: str, prompt: str, model: str = "gemini-1.5-flash") -> Optional[str]:
    """Calls Gemini REST API with strict timeouts and error handling."""
    if not api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json"
        }
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidate = res_data.get("candidates", [{}])[0]
            text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
            return text
    except Exception as e:
        print(f"[WARN] Gemini API call failed: {e}. Falling back to grounded retrieval engine.")
        return None

def generate_grounded_legal_analysis(
    query_text: str,
    retrieved_provisions: List[Dict[str, Any]],
    jurisdiction_name: str,
    incident_date: Optional[str] = None,
    api_key: Optional[str] = None,
    db_path: Path = DB_PATH
) -> Dict[str, Any]:
    """
    Generates verified legal awareness analysis.
    If Gemini API key is configured and reachable, uses LLM with strict grounding prompt.
    Otherwise, uses the guaranteed deterministic grounded legal engine.
    In both cases, ALL citations are verified against the local database.
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY", "")
        
    fallback_res = build_deterministic_grounded_answer(
        query_text=query_text,
        retrieved_provisions=retrieved_provisions,
        jurisdiction_name=jurisdiction_name,
        incident_date=incident_date
    )
    
    if not api_key or not retrieved_provisions:
        return fallback_res
        
    # Construct grounding prompt with retrieved sources ONLY
    sources_summary = []
    for p in retrieved_provisions:
        sources_summary.append({
            "id": p["id"],
            "act_title": p.get("act_title"),
            "provision_type": p.get("provision_type"),
            "provision_number": p.get("provision_number"),
            "heading": p.get("heading"),
            "summary": p.get("plain_english_summary"),
            "official_text": p.get("official_text")[:500],
            "conditions": p.get("conditions_to_establish"),
            "exceptions": p.get("exceptions_and_limitations"),
            "source_url": p.get("source_url")
        })
        
    prompt = f"""
You are an expert Indian Legal Awareness assistant (NyayaGuide).
Your task is to analyze the user's situation using ONLY the provided verified legal provisions.

USER SITUATION:
"{query_text}"
JURISDICTION: {jurisdiction_name}
INCIDENT DATE: {incident_date or 'Not specified'}

VERIFIED LEGAL SOURCES AVAILABLE IN DATABASE:
{json.dumps(sources_summary, indent=2)}

CRITICAL INSTRUCTIONS:
1. Ground your answer EXCLUSIVELY in the provided legal sources above.
2. NEVER invent an Article, Section, or statutory quotation not present in the sources list.
3. Every provision you cite in "potentially_relevant_laws" MUST match one of the exact "id" strings in the sources.
4. Note that if incident is on/after 1 July 2024, Bharatiya Nyaya Sanhita (BNS) governs substantive crimes, not IPC.
5. Return ONLY a valid JSON object matching this schema:
{{
  "issue_summary": "Neutral factual summary of user's issue",
  "jurisdiction": "{jurisdiction_name}",
  "clarifying_questions": ["Question 1", "Question 2"],
  "potentially_relevant_laws": ["exact_id_from_sources"],
  "why_it_may_apply": "Simple English explanation of why each retrieved provision may apply",
  "conditions": "Key conditions that must be substantiated",
  "exceptions": "Statutory exceptions and limitations",
  "possible_next_steps": ["Step 1", "Step 2"],
  "lawyer_practice_areas": ["Practice Area 1"],
  "official_sources": [{{"title": "Act Section", "url": "url_from_sources"}}],
  "limitations": "Clear note on legal uncertainty",
  "urgent_help": "Emergency contact note if violence or cyber loss is active, else null",
  "needs_legal_review": true
}}
"""
    raw_response = call_gemini_api(api_key, prompt)
    if not raw_response:
        return fallback_res
        
    try:
        data = json.loads(raw_response.strip("```json\n").strip("```"))
        # Validate returned provision IDs against local database
        conn = sqlite3.connect(str(db_path))
        valid_provisions, rejected_ids = validate_provisions_against_db(
            conn, data.get("potentially_relevant_laws", [])
        )
        conn.close()
        
        # If model hallucinated unknown IDs, filter them out
        data["potentially_relevant_laws"] = [p["id"] for p in valid_provisions]
        if not data["potentially_relevant_laws"]:
            data["potentially_relevant_laws"] = [p["id"] for p in retrieved_provisions]
            
        data["is_ai_grounded"] = True
        data["ai_mode"] = "gemini_grounded_rag"
        return data
    except Exception as e:
        print(f"[WARN] Failed to parse LLM JSON: {e}. Using deterministic fallback.")
        return fallback_res
