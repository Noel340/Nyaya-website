"""
NyayaGuide Legal Dataset Export Tool
Generates JSON and CSV exports of verified legal provisions and produces
jurisdiction coverage and source manifests.
CLI: python -m legal.export_dataset [--format json|csv|all] [--outdir data/exports]
"""
import argparse
import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "instance" / "nyayaguide.db"
EXPORT_DIR = BASE_DIR / "data" / "exports"

def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def export_provisions_json(db_path: Path, output_file: Path) -> int:
    """Exports all legal provisions with act and jurisdiction metadata to JSON."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.id, p.provision_type, p.provision_number, p.heading, p.chapter,
            p.plain_english_summary, p.official_text, p.why_relevant_explanation,
            p.conditions_to_establish, p.exceptions_and_limitations,
            p.effective_from, p.effective_until, p.status, p.source_url,
            p.source_document_id, p.verification_status, p.last_verified_at,
            a.short_title as act_title, a.enactment_year, a.category as act_category,
            j.name as jurisdiction_name, j.type as jurisdiction_type
        FROM legal_provisions p
        JOIN legal_acts a ON p.act_id = a.id
        JOIN jurisdictions j ON a.jurisdiction_id = j.id
        ORDER BY a.short_title, p.provision_number
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "export_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_records": len(rows),
                "license": "Indian Legal Public Domain / Open Access Educational Information",
                "notice": "This export reflects verified seed provisions in NyayaGuide. Not a substitute for official gazettes."
            },
            "provisions": rows
        }, f, indent=2, ensure_ascii=False)
        
    return len(rows)

def export_provisions_csv(db_path: Path, output_file: Path) -> int:
    """Exports legal provisions to CSV."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.id, a.short_title as act_title, p.provision_type, p.provision_number,
            p.heading, p.plain_english_summary, p.status, p.effective_from,
            p.verification_status, p.source_url, j.name as jurisdiction
        FROM legal_provisions p
        JOIN legal_acts a ON p.act_id = a.id
        JOIN jurisdictions j ON a.jurisdiction_id = j.id
        ORDER BY a.short_title, p.provision_number
    """)
    rows = cursor.fetchall()
    col_names = [d[0] for d in cursor.description]
    conn.close()
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(col_names)
        for r in rows:
            writer.writerow(list(r))
            
    return len(rows)

def generate_coverage_report(db_path: Path) -> Dict[str, Any]:
    """Generates a truthful audit of current legal indexing status across all jurisdictions."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Jurisdiction stats
    cursor.execute("""
        SELECT 
            j.id, j.name, j.type, j.coverage_status,
            COUNT(DISTINCT a.id) as acts_count,
            COUNT(DISTINCT p.id) as provisions_count
        FROM jurisdictions j
        LEFT JOIN legal_acts a ON a.jurisdiction_id = j.id
        LEFT JOIN legal_provisions p ON p.act_id = a.id
        GROUP BY j.id
        ORDER BY j.type, j.name
    """)
    jurisdictions = [dict(r) for r in cursor.fetchall()]
    
    # Acts by category
    cursor.execute("""
        SELECT category, COUNT(id) as count
        FROM legal_acts
        GROUP BY category
    """)
    act_categories = [dict(r) for r in cursor.fetchall()]
    
    # Status breakdown
    cursor.execute("""
        SELECT status, COUNT(id) as count
        FROM legal_provisions
        GROUP BY status
    """)
    provision_statuses = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    indexed_count = sum(1 for j in jurisdictions if j["provisions_count"] > 0)
    total_jurisdictions = len(jurisdictions)
    
    return {
        "report_generated_at": datetime.now().isoformat(),
        "total_jurisdictions": total_jurisdictions,
        "jurisdictions_with_seed_data": indexed_count,
        "coverage_percentage": round((indexed_count / max(1, total_jurisdictions)) * 100, 1),
        "disclaimer": "NyayaGuide indexes Central statutes and key State provisions progressively. Coverage is partial and continuously updated.",
        "jurisdictions": jurisdictions,
        "act_categories": act_categories,
        "provision_statuses": provision_statuses
    }

def run_export_cli():
    parser = argparse.ArgumentParser(description="Export NyayaGuide verified legal dataset.")
    parser.add_argument("--format", choices=["json", "csv", "all"], default="all", help="Output format")
    parser.add_argument("--outdir", default=str(EXPORT_DIR), help="Output directory path")
    args = parser.parse_args()
    
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    if args.format in ("json", "all"):
        json_path = outdir / "nyayaguide_provisions.json"
        cnt = export_provisions_json(DB_PATH, json_path)
        print(f"[OK] Exported {cnt} provisions to: {json_path}")
        
    if args.format in ("csv", "all"):
        csv_path = outdir / "nyayaguide_provisions.csv"
        cnt = export_provisions_csv(DB_PATH, csv_path)
        print(f"[OK] Exported {cnt} provisions to: {csv_path}")
        
    # Generate coverage report
    report_path = outdir / "coverage_report.json"
    cov = generate_coverage_report(DB_PATH)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(cov, f, indent=2)
    print(f"[OK] Coverage report written to: {report_path}")

if __name__ == "__main__":
    run_export_cli()
