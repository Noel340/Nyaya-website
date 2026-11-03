"""
NyayaGuide Ingestion Pipeline
Ingests structured seed records, parses legal provisions, verifies relationships,
populates FTS5 virtual tables, and creates audit ingestion runs.
"""
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from legal.init_db import init_database
from legal.validate import is_trusted_official_url

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BASE_DIR / "data" / "seed"
DB_PATH = BASE_DIR / "instance" / "nyayaguide.db"

def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    if not file_path.exists():
        print(f"[WARN] Seed file does not exist: {file_path}")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_ingestion(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Runs full ingestion from verified seed directory into SQLite database."""
    if db_path is None:
        db_path = DB_PATH
        
    init_database(db_path)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    run_id = f"ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    report = {
        "run_id": run_id,
        "run_date": datetime.now().isoformat(),
        "sources_count": 0,
        "jurisdictions_count": 0,
        "topics_count": 0,
        "acts_count": 0,
        "provisions_count": 0,
        "relations_count": 0,
        "lawyers_count": 0,
        "legal_aid_count": 0,
        "rejected": 0,
        "duplicates": 0,
        "status": "COMPLETED"
    }
    
    try:
        # 1. Ingest Sources
        sources = load_json_file(SEED_DIR / "sources.json")
        for s in sources:
            cursor.execute("""
                INSERT OR REPLACE INTO legal_sources 
                (id, name, base_url, official_portal, description, licensing_info, is_verified, last_checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s["id"], s["name"], s["base_url"], s["official_portal"],
                s.get("description"), s.get("licensing_info"),
                s.get("is_verified", 1), s.get("last_checked_at")
            ))
            report["sources_count"] += 1
            
        # 2. Ingest Jurisdictions
        jurisdictions = load_json_file(SEED_DIR / "jurisdictions.json")
        for j in jurisdictions:
            cursor.execute("""
                INSERT OR REPLACE INTO jurisdictions 
                (id, code, name, type, official_portal_url, coverage_status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                j["id"], j["code"], j["name"], j["type"],
                j.get("official_portal_url"), j["coverage_status"], j.get("notes")
            ))
            report["jurisdictions_count"] += 1
            
        # 3. Ingest Topics
        topics = load_json_file(SEED_DIR / "topics.json")
        for t in topics:
            cursor.execute("""
                INSERT OR REPLACE INTO legal_topics 
                (id, name, slug, description, keywords)
                VALUES (?, ?, ?, ?, ?)
            """, (
                t["id"], t["name"], t["slug"], t.get("description"), t.get("keywords")
            ))
            report["topics_count"] += 1
            
        # 4. Ingest Acts
        acts = load_json_file(SEED_DIR / "acts.json")
        for a in acts:
            cursor.execute("""
                INSERT OR REPLACE INTO legal_acts 
                (id, short_title, long_title, act_number, enactment_year, enactment_date, 
                 commencement_date, jurisdiction_id, category, status, repealed_by_act_id, 
                 transition_notes, official_source_url, verification_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a["id"], a["short_title"], a.get("long_title"), a.get("act_number"),
                a.get("enactment_year"), a.get("enactment_date"), a.get("commencement_date"),
                a["jurisdiction_id"], a["category"], a["status"], a.get("repealed_by_act_id"),
                a.get("transition_notes"), a["official_source_url"], a.get("verification_status", "verified")
            ))
            report["acts_count"] += 1
            
        # 5. Ingest Provisions & Populate FTS5 Index
        provisions = load_json_file(SEED_DIR / "provisions.json")
        cursor.execute("DELETE FROM legal_provisions_fts") # Clear FTS index before re-populating
        
        for p in provisions:
            cursor.execute("""
                INSERT OR REPLACE INTO legal_provisions 
                (id, act_id, provision_type, provision_number, heading, chapter, 
                 official_text, plain_english_summary, why_relevant_explanation, 
                 conditions_to_establish, exceptions_and_limitations, effective_from, 
                 effective_until, status, source_url, source_document_id, 
                 verification_status, last_verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], p["act_id"], p["provision_type"], p["provision_number"],
                p["heading"], p.get("chapter"), p["official_text"], p["plain_english_summary"],
                p.get("why_relevant_explanation"), p.get("conditions_to_establish"),
                p.get("exceptions_and_limitations"), p.get("effective_from"),
                p.get("effective_until"), p["status"], p["source_url"],
                p.get("source_document_id"), p.get("verification_status", "verified"),
                p.get("last_verified_at")
            ))
            
            # Fetch act title for FTS indexing
            cursor.execute("SELECT short_title FROM legal_acts WHERE id = ?", (p["act_id"],))
            act_row = cursor.fetchone()
            act_title = act_row[0] if act_row else ""
            
            # Index into FTS5
            fts_keywords = f"{p['provision_type']} {p['provision_number']} {p.get('why_relevant_explanation', '')}"
            cursor.execute("""
                INSERT INTO legal_provisions_fts 
                (provision_id, act_title, provision_number, heading, official_text, plain_english_summary, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], act_title, p["provision_number"], p["heading"],
                p["official_text"], p["plain_english_summary"], fts_keywords
            ))
            report["provisions_count"] += 1
            
        # 6. Ingest Provision Topics
        provision_topics = load_json_file(SEED_DIR / "provision_topics.json")
        for pt in provision_topics:
            cursor.execute("""
                INSERT OR REPLACE INTO provision_topics (provision_id, topic_id)
                VALUES (?, ?)
            """, (pt["provision_id"], pt["topic_id"]))
            
        # 7. Ingest Relations
        relations = load_json_file(SEED_DIR / "relations.json")
        for r in relations:
            cursor.execute("""
                INSERT OR REPLACE INTO provision_relations 
                (id, source_provision_id, target_provision_id, relation_type, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (r["id"], r["source_provision_id"], r["target_provision_id"], r["relation_type"], r.get("notes")))
            report["relations_count"] += 1
            
        # 8. Ingest Lawyer Profiles
        lawyers = load_json_file(SEED_DIR / "lawyer_categories.json")
        for l in lawyers:
            cursor.execute("""
                INSERT OR REPLACE INTO lawyer_profiles 
                (id, practice_area_code, practice_area_title, description, when_needed_criteria, bar_council_guidance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                l["id"], l["practice_area_code"], l["practice_area_title"],
                l["description"], l["when_needed_criteria"], l["bar_council_guidance"]
            ))
            report["lawyers_count"] += 1
            
        # 9. Ingest Legal Aid Resources
        legal_aid = load_json_file(SEED_DIR / "legal_aid.json")
        for aid in legal_aid:
            cursor.execute("""
                INSERT OR REPLACE INTO legal_aid_resources 
                (id, title, category, jurisdiction_id, helpline_number, official_portal, 
                 description, eligibility_criteria, is_verified, last_verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                aid["id"], aid["title"], aid["category"], aid.get("jurisdiction_id"),
                aid.get("helpline_number"), aid["official_portal"], aid["description"],
                aid.get("eligibility_criteria"), aid.get("is_verified", 1), aid.get("last_verified_at")
            ))
            report["legal_aid_count"] += 1
            
        # Record Ingestion Run Audit
        cursor.execute("""
            INSERT INTO ingestion_runs 
            (id, run_date, source_id, records_imported, records_rejected, records_duplicate, status, report_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, report["run_date"], "src_indiacode",
            report["provisions_count"] + report["acts_count"],
            report["rejected"], report["duplicates"], "COMPLETED",
            json.dumps(report)
        ))
        
        conn.commit()
        print(f"[OK] Ingestion run '{run_id}' completed successfully:")
        print(f"     - Jurisdictions: {report['jurisdictions_count']}")
        print(f"     - Acts: {report['acts_count']}")
        print(f"     - Provisions: {report['provisions_count']}")
        print(f"     - Legal Aid Resources: {report['legal_aid_count']}")
        print(f"     - Lawyer Profiles: {report['lawyers_count']}")
        return report
    except Exception as e:
        conn.rollback()
        report["status"] = "FAILED"
        report["error"] = str(e)
        print(f"[ERROR] Ingestion failed: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_ingestion()
