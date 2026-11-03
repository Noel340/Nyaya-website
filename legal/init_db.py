"""
NyayaGuide Database Initialization & Schema Definition
Supports SQLite with FTS5 virtual tables and adheres to relational standards
for easy migration to PostgreSQL.
"""
import sqlite3
import os
from pathlib import Path

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- 1. Legal Sources Inventory
CREATE TABLE IF NOT EXISTS legal_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    official_portal TEXT NOT NULL,
    description TEXT,
    licensing_info TEXT,
    is_verified INTEGER DEFAULT 1,
    last_checked_at TEXT
);

-- 2. Jurisdictions (Central, 28 States, 8 Union Territories)
CREATE TABLE IF NOT EXISTS jurisdictions (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('central', 'state', 'union_territory')),
    official_portal_url TEXT,
    coverage_status TEXT NOT NULL CHECK(coverage_status IN ('indexed_seed', 'partially_indexed', 'planned', 'monitoring')),
    notes TEXT
);

-- 3. Legal Acts
CREATE TABLE IF NOT EXISTS legal_acts (
    id TEXT PRIMARY KEY,
    short_title TEXT NOT NULL,
    long_title TEXT,
    act_number TEXT,
    enactment_year INTEGER,
    enactment_date TEXT,
    commencement_date TEXT,
    jurisdiction_id TEXT NOT NULL REFERENCES jurisdictions(id),
    category TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('in_force', 'repealed', 'historical', 'partially_in_force')),
    repealed_by_act_id TEXT,
    transition_notes TEXT,
    official_source_url TEXT NOT NULL,
    verification_status TEXT NOT NULL CHECK(verification_status IN ('verified', 'provisional', 'under_review'))
);

-- 4. Legal Provisions (Articles, Sections, Rules)
CREATE TABLE IF NOT EXISTS legal_provisions (
    id TEXT PRIMARY KEY,
    act_id TEXT NOT NULL REFERENCES legal_acts(id) ON DELETE CASCADE,
    provision_type TEXT NOT NULL CHECK(provision_type IN ('article', 'section', 'schedule', 'rule', 'order', 'preamble')),
    provision_number TEXT NOT NULL,
    heading TEXT NOT NULL,
    chapter TEXT,
    official_text TEXT NOT NULL,
    plain_english_summary TEXT NOT NULL,
    why_relevant_explanation TEXT,
    conditions_to_establish TEXT,
    exceptions_and_limitations TEXT,
    effective_from TEXT,
    effective_until TEXT,
    status TEXT NOT NULL CHECK(status IN ('current', 'repealed', 'amended', 'historical')),
    source_url TEXT NOT NULL,
    source_document_id TEXT,
    verification_status TEXT NOT NULL CHECK(verification_status IN ('verified', 'provisional', 'under_review')),
    last_verified_at TEXT
);

-- 5. Amendments
CREATE TABLE IF NOT EXISTS amendments (
    id TEXT PRIMARY KEY,
    act_id TEXT NOT NULL REFERENCES legal_acts(id) ON DELETE CASCADE,
    amendment_title TEXT NOT NULL,
    amendment_number TEXT,
    gazette_notification_no TEXT,
    enactment_date TEXT,
    commencement_date TEXT,
    summary TEXT,
    official_url TEXT
);

-- 6. Provision Versions (Temporal & Transition Tracking)
CREATE TABLE IF NOT EXISTS provision_versions (
    id TEXT PRIMARY KEY,
    provision_id TEXT NOT NULL REFERENCES legal_provisions(id) ON DELETE CASCADE,
    version_label TEXT NOT NULL,
    effective_from TEXT,
    effective_until TEXT,
    text_snapshot TEXT NOT NULL,
    reason_for_change TEXT
);

-- 7. Legal Topics / Categories
CREATE TABLE IF NOT EXISTS legal_topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    keywords TEXT
);

-- 8. Provision - Topic Junction
CREATE TABLE IF NOT EXISTS provision_topics (
    provision_id TEXT NOT NULL REFERENCES legal_provisions(id) ON DELETE CASCADE,
    topic_id TEXT NOT NULL REFERENCES legal_topics(id) ON DELETE CASCADE,
    PRIMARY KEY (provision_id, topic_id)
);

-- 9. Provision Relations (e.g., BNS 318 successor of IPC 420)
CREATE TABLE IF NOT EXISTS provision_relations (
    id TEXT PRIMARY KEY,
    source_provision_id TEXT NOT NULL REFERENCES legal_provisions(id) ON DELETE CASCADE,
    target_provision_id TEXT NOT NULL REFERENCES legal_provisions(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK(relation_type IN ('successor_of', 'predecessor_to', 'repeals', 'read_with', 'overrides')),
    notes TEXT
);

-- 10. Lawyer Practice Area Profiles
CREATE TABLE IF NOT EXISTS lawyer_profiles (
    id TEXT PRIMARY KEY,
    practice_area_code TEXT NOT NULL UNIQUE,
    practice_area_title TEXT NOT NULL,
    description TEXT NOT NULL,
    when_needed_criteria TEXT NOT NULL,
    bar_council_guidance TEXT NOT NULL
);

-- 11. Official Legal Aid & Grievance Resources
CREATE TABLE IF NOT EXISTS legal_aid_resources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('national_aid', 'state_aid', 'district_aid', 'cyber_helpline', 'consumer_helpline', 'emergency', 'bar_council')),
    jurisdiction_id TEXT REFERENCES jurisdictions(id),
    helpline_number TEXT,
    official_portal TEXT NOT NULL,
    description TEXT NOT NULL,
    eligibility_criteria TEXT,
    is_verified INTEGER DEFAULT 1,
    last_verified_at TEXT
);

-- 12. Ingestion Runs (Audit Log)
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id TEXT PRIMARY KEY,
    run_date TEXT NOT NULL,
    source_id TEXT REFERENCES legal_sources(id),
    records_imported INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    records_duplicate INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    report_json TEXT
);

-- 13. Data Review Records
CREATE TABLE IF NOT EXISTS review_records (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    review_reason TEXT NOT NULL,
    flagged_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected'))
);

-- Indexes for high-frequency queries
CREATE INDEX IF NOT EXISTS idx_provisions_act ON legal_provisions(act_id);
CREATE INDEX IF NOT EXISTS idx_provisions_type_num ON legal_provisions(provision_type, provision_number);
CREATE INDEX IF NOT EXISTS idx_provisions_status ON legal_provisions(status);
CREATE INDEX IF NOT EXISTS idx_acts_jurisdiction ON legal_acts(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_acts_category ON legal_acts(category);
CREATE INDEX IF NOT EXISTS idx_acts_status ON legal_acts(status);
CREATE INDEX IF NOT EXISTS idx_legal_aid_category ON legal_aid_resources(category);
CREATE INDEX IF NOT EXISTS idx_legal_aid_jurisdiction ON legal_aid_resources(jurisdiction_id);

-- FTS5 Full-Text Search Virtual Table
CREATE VIRTUAL TABLE IF NOT EXISTS legal_provisions_fts USING fts5(
    provision_id UNINDEXED,
    act_title,
    provision_number,
    heading,
    official_text,
    plain_english_summary,
    keywords,
    tokenize = 'porter unicode61'
);
"""

def init_database(db_path: Path = None):
    """Initializes the database schema and sets up tables and FTS5 index."""
    if db_path is None:
        db_path = Path(__file__).resolve().parent.parent / "instance" / "nyayaguide.db"
    
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA_SQL)
        conn.commit()
        print(f"[OK] Database initialized successfully at: {db_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
