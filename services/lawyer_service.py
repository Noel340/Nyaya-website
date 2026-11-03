"""
NyayaGuide Lawyer & Legal Aid Resource Service
Handles lawyer practice area matching and queries verified legal aid databases (NALSA, SLSAs).
"""
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "instance" / "nyayaguide.db"

class LawyerService:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_practice_profiles(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lawyer_profiles ORDER BY practice_area_title")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_legal_aid_resources(
        self,
        jurisdiction_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        query = """
            SELECT r.*, j.name as jurisdiction_name
            FROM legal_aid_resources r
            LEFT JOIN jurisdictions j ON r.jurisdiction_id = j.id
            WHERE 1=1
        """
        params = []
        if jurisdiction_id and jurisdiction_id != "IN-CENTRAL":
            query += " AND (r.jurisdiction_id = ? OR r.jurisdiction_id = 'IN-CENTRAL')"
            params.append(jurisdiction_id)
        if category:
            query += " AND r.category = ?"
            params.append(category)
        query += " ORDER BY r.category, r.title"
        
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
