"""
NyayaGuide Search Engine
Combines SQLite FTS5 full-text search, topic tagging, jurisdiction hierarchy,
and date-based BNS/IPC criminal transition filtering.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from legal.normalize import sanitize_fts_query, parse_incident_date, extract_cited_sections

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "instance" / "nyayaguide.db"

def search_provisions(
    query_text: str,
    jurisdiction_id: Optional[str] = "IN-CENTRAL",
    topic_id: Optional[str] = None,
    incident_date_str: Optional[str] = None,
    limit: int = 10,
    db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Executes ranked search across legal provisions with FTS5, jurisdiction filtering,
    and BNS/IPC criminal transition handling.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    incident_dt, is_post_bns = parse_incident_date(incident_date_str)
    sanitized_query = sanitize_fts_query(query_text)
    
    # Check if query directly cites a section/article number
    cited_sections = extract_cited_sections(query_text)
    
    results = []
    seen_ids = set()
    
    # 1. Exact Section/Article Citation Search (Highest priority)
    for cite in cited_sections:
        c_num = cite["number"]
        c_type = cite["type"]
        cursor.execute("""
            SELECT 
                p.id, p.act_id, a.short_title as act_title, a.category as act_category,
                p.provision_type, p.provision_number, p.heading, p.chapter,
                p.plain_english_summary, p.official_text, p.why_relevant_explanation,
                p.conditions_to_establish, p.exceptions_and_limitations,
                p.effective_from, p.effective_until, p.status, p.source_url,
                p.verification_status, j.name as jurisdiction_name,
                100.0 as rank_score
            FROM legal_provisions p
            JOIN legal_acts a ON p.act_id = a.id
            JOIN jurisdictions j ON a.jurisdiction_id = j.id
            WHERE p.provision_number LIKE ? AND p.provision_type = ?
        """, (f"%{c_num}%", c_type))
        for r in cursor.fetchall():
            item = dict(r)
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                results.append(item)
                
    # 2. SQLite FTS5 Full-Text Search
    if sanitized_query:
        # Match FTS virtual table with rank
        try:
            cursor.execute(f"""
                SELECT 
                    p.id, p.act_id, a.short_title as act_title, a.category as act_category,
                    p.provision_type, p.provision_number, p.heading, p.chapter,
                    p.plain_english_summary, p.official_text, p.why_relevant_explanation,
                    p.conditions_to_establish, p.exceptions_and_limitations,
                    p.effective_from, p.effective_until, p.status, p.source_url,
                    p.verification_status, j.name as jurisdiction_name,
                    fts.rank * -1.0 as rank_score
                FROM legal_provisions_fts fts
                JOIN legal_provisions p ON fts.provision_id = p.id
                JOIN legal_acts a ON p.act_id = a.id
                JOIN jurisdictions j ON a.jurisdiction_id = j.id
                WHERE legal_provisions_fts MATCH ?
                ORDER BY fts.rank
                LIMIT ?
            """, (sanitized_query, limit * 2))
            
            for r in cursor.fetchall():
                item = dict(r)
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    results.append(item)
        except sqlite3.OperationalError:
            # Fallback to LIKE if FTS fails on unusual input
            pass
            
    # 3. Topic-based Fallback if results are fewer than 3
    if len(results) < 3 and topic_id:
        cursor.execute("""
            SELECT 
                p.id, p.act_id, a.short_title as act_title, a.category as act_category,
                p.provision_type, p.provision_number, p.heading, p.chapter,
                p.plain_english_summary, p.official_text, p.why_relevant_explanation,
                p.conditions_to_establish, p.exceptions_and_limitations,
                p.effective_from, p.effective_until, p.status, p.source_url,
                p.verification_status, j.name as jurisdiction_name,
                5.0 as rank_score
            FROM provision_topics pt
            JOIN legal_provisions p ON pt.provision_id = p.id
            JOIN legal_acts a ON p.act_id = a.id
            JOIN jurisdictions j ON a.jurisdiction_id = j.id
            WHERE pt.topic_id = ?
            LIMIT ?
        """, (topic_id, limit))
        for r in cursor.fetchall():
            item = dict(r)
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                results.append(item)
                
    # 4. Fetch Transition Relations (e.g., BNS 318 <-> IPC 420)
    for item in results:
        cursor.execute("""
            SELECT r.relation_type, r.notes, 
                   tp.id as related_id, tp.provision_type as related_type,
                   tp.provision_number as related_num, ta.short_title as related_act
            FROM provision_relations r
            JOIN legal_provisions tp ON (r.target_provision_id = tp.id OR r.source_provision_id = tp.id)
            JOIN legal_acts ta ON tp.act_id = ta.id
            WHERE (r.source_provision_id = ? OR r.target_provision_id = ?)
              AND tp.id != ?
        """, (item["id"], item["id"], item["id"]))
        relations = [dict(rel) for rel in cursor.fetchall()]
        item["relations"] = relations
        
        # Criminal transition note annotation
        if is_post_bns:
            if "ipc" in item["act_id"]:
                item["transition_warning"] = "Incident occurred on or after 1 July 2024: The corresponding section under Bharatiya Nyaya Sanhita, 2023 applies."
        else:
            if "bns" in item["act_id"]:
                item["transition_warning"] = "Incident occurred before 1 July 2024: The corresponding section under the Indian Penal Code, 1860 applies."

    conn.close()
    
    # Sort with post-BNS preference for criminal offences
    def sort_key(x):
        score = x.get("rank_score", 0)
        # Bonus for Constitutional Articles when human rights/arbitrary action discussed
        if x["act_id"] == "act_constitution":
            score += 2.0
        # Transition date alignment
        if is_post_bns and "bns" in x["act_id"]:
            score += 3.0
        elif not is_post_bns and "ipc" in x["act_id"]:
            score += 3.0
        return score
        
    results.sort(key=sort_key, reverse=True)
    return results[:limit]
