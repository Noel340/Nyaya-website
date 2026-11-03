"""
NyayaGuide Legal Source Synchronization
Maintains inventory of official source URLs, checks verification status,
and generates source manifests compliant with government open data policies.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from legal.validate import is_trusted_official_url

def sync_legal_sources_inventory(db_path: Path) -> List[Dict[str, Any]]:
    """Audits all legal source URLs recorded in database and validates domain integrity."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, base_url, official_portal, is_verified, last_checked_at FROM legal_sources")
    sources = [dict(row) for row in cursor.fetchall()]
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated = []
    
    for s in sources:
        url = s.get("official_portal") or s.get("base_url")
        trusted = is_trusted_official_url(url)
        s["is_trusted_domain"] = trusted
        s["last_audit"] = timestamp
        
        cursor.execute(
            "UPDATE legal_sources SET is_verified = ?, last_checked_at = ? WHERE id = ?",
            (1 if trusted else 0, timestamp, s["id"])
        )
        updated.append(s)
        
    conn.commit()
    conn.close()
    return updated

def get_source_manifest(db_path: Path) -> Dict[str, Any]:
    """Produces public manifest detailing sources, URLs, and verification dates."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.name, s.official_portal, s.description, s.licensing_info, 
               s.is_verified, s.last_checked_at,
               COUNT(p.id) as provisions_count
        FROM legal_sources s
        LEFT JOIN legal_acts a ON a.official_source_url LIKE s.base_url || '%'
        LEFT JOIN legal_provisions p ON p.act_id = a.id
        GROUP BY s.id
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return {
        "manifest_version": "1.0.0",
        "generated_at": datetime.now().isoformat(),
        "publisher": "NyayaGuide Indian Legal Awareness Project",
        "policy": "Respects official robots.txt and does not bypass technical access controls.",
        "sources": rows
    }
