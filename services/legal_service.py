"""
NyayaGuide Legal Service
High-level service interface for routes and controllers.
Manages database transactions, query pipelines, and provision retrieval.
"""
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from legal.retrieval import retrieve_grounding_context
from legal.answer import generate_grounded_legal_analysis

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "instance" / "nyayaguide.db"

class LegalService:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_jurisdictions(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, code, name, type, coverage_status FROM jurisdictions ORDER BY type, name")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_all_topics(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, slug, description FROM legal_topics ORDER BY name")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_acts(self, jurisdiction_id: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        query = """
            SELECT a.id, a.short_title, a.long_title, a.act_number, a.enactment_year, 
                   a.commencement_date, a.category, a.status, a.official_source_url, 
                   j.name as jurisdiction_name,
                   COUNT(p.id) as provisions_count
            FROM legal_acts a
            JOIN jurisdictions j ON a.jurisdiction_id = j.id
            LEFT JOIN legal_provisions p ON p.act_id = a.id
            WHERE 1=1
        """
        params = []
        if jurisdiction_id:
            query += " AND (a.jurisdiction_id = ? OR a.jurisdiction_id = 'IN-CENTRAL')"
            params.append(jurisdiction_id)
        if category:
            query += " AND a.category = ?"
            params.append(category)
        query += " GROUP BY a.id ORDER BY a.short_title"
        
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_act_by_id(self, act_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, j.name as jurisdiction_name
            FROM legal_acts a
            JOIN jurisdictions j ON a.jurisdiction_id = j.id
            WHERE a.id = ?
        """, (act_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        act = dict(row)
        
        # Get provisions for this Act
        cursor.execute("""
            SELECT id, provision_type, provision_number, heading, chapter, 
                   plain_english_summary, status, source_url
            FROM legal_provisions
            WHERE act_id = ?
            ORDER BY provision_number
        """, (act_id,))
        act["provisions"] = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return act

    def get_provision_by_id(self, provision_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, a.short_title as act_title, a.category as act_category, j.name as jurisdiction_name
            FROM legal_provisions p
            JOIN legal_acts a ON p.act_id = a.id
            JOIN jurisdictions j ON a.jurisdiction_id = j.id
            WHERE p.id = ?
        """, (provision_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        provision = dict(row)
        
        # Fetch related provisions
        cursor.execute("""
            SELECT r.relation_type, r.notes, tp.id, tp.provision_number, tp.heading, ta.short_title as act_title
            FROM provision_relations r
            JOIN legal_provisions tp ON (r.target_provision_id = tp.id OR r.source_provision_id = tp.id)
            JOIN legal_acts ta ON tp.act_id = ta.id
            WHERE (r.source_provision_id = ? OR r.target_provision_id = ?)
              AND tp.id != ?
        """, (provision_id, provision_id, provision_id))
        provision["relations"] = [dict(r) for r in cursor.fetchall()]
        
        conn.close()
        return provision

    def process_situation_query(
        self,
        query_text: str,
        jurisdiction_id: str = "IN-CENTRAL",
        topic_id: Optional[str] = None,
        incident_date: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Complete workflow: retrieval + ranking + grounded legal analysis."""
        retrieval_ctx = retrieve_grounding_context(
            query_text=query_text,
            jurisdiction_id=jurisdiction_id,
            topic_id=topic_id,
            incident_date=incident_date,
            limit=8
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM jurisdictions WHERE id = ?", (jurisdiction_id,))
        j_row = cursor.fetchone()
        jurisdiction_name = j_row["name"] if j_row else "All India / Central"
        conn.close()
        
        explanation = generate_grounded_legal_analysis(
            query_text=query_text,
            retrieved_provisions=retrieval_ctx["retrieved_provisions"],
            jurisdiction_name=jurisdiction_name,
            incident_date=incident_date,
            api_key=api_key,
            db_path=self.db_path
        )
        
        return {
            "retrieval": retrieval_ctx,
            "explanation": explanation,
            "provisions": retrieval_ctx["retrieved_provisions"]
        }
