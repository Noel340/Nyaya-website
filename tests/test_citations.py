"""
NyayaGuide Citation & Anti-Hallucination Tests
Verifies that fabricated citations or untrusted domains are strictly rejected.
"""
import sqlite3
import pytest
from pathlib import Path
from legal.init_db import init_database
from legal.ingest import run_ingestion
from legal.validate import is_trusted_official_url, validate_provisions_against_db
from legal.answer import build_deterministic_grounded_answer

@pytest.fixture(scope="module")
def setup_db(tmp_path_factory):
    fn = tmp_path_factory.mktemp("db") / "test_citations.db"
    init_database(fn)
    run_ingestion(fn)
    return fn

def test_trusted_official_domain_checker():
    """Test validation of official government / statutory domains."""
    assert is_trusted_official_url("https://www.indiacode.nic.in/handle/123456789/21808") is True
    assert is_trusted_official_url("https://legislative.gov.in/constitution-of-india/") is True
    assert is_trusted_official_url("https://nalsa.gov.in/services") is True
    assert is_trusted_official_url("https://cybercrime.gov.in/Webform/Crime_AuthoLogin.aspx") is True
    
    # Untrusted / spoofed / arbitrary domains should be rejected
    assert is_trusted_official_url("https://random-lawyer-blog.com/section420") is False
    assert is_trusted_official_url("https://fakegovernment.org/constitution") is False
    assert is_trusted_official_url("") is False

def test_rejection_of_hallucinated_provision_ids(setup_db):
    """Test that nonexistent or hallucinated provision IDs are rejected against DB."""
    conn = sqlite3.connect(str(setup_db))
    test_ids = [
        "prov_const_art21",         # Valid
        "prov_bns_sec318",          # Valid
        "prov_fake_sec9999",        # Fabricated
        "random_invented_act_art1"  # Fabricated
    ]
    valid_provisions, rejected_ids = validate_provisions_against_db(conn, test_ids)
    conn.close()

    assert len(valid_provisions) == 2
    assert "prov_const_art21" in [p["id"] for p in valid_provisions]
    assert "prov_bns_sec318" in [p["id"] for p in valid_provisions]
    assert "prov_fake_sec9999" in rejected_ids
    assert "random_invented_act_art1" in rejected_ids

def test_deterministic_grounded_answer_schema(setup_db):
    """Test that fallback engine outputs the exact required JSON schema with all keys."""
    sample_provisions = [{
        "id": "prov_const_art21",
        "act_id": "act_constitution",
        "act_title": "The Constitution of India",
        "act_category": "Constitutional Law",
        "provision_type": "article",
        "provision_number": "21",
        "heading": "Protection of life and personal liberty",
        "plain_english_summary": "Right to life, dignity and privacy.",
        "why_relevant_explanation": "Protects against unlawful confinement or surveillance.",
        "conditions_to_establish": "Deprivation of liberty without fair law.",
        "exceptions_and_limitations": "Lawful arrest according to statute.",
        "source_url": "https://legislative.gov.in/constitution-of-india/"
    }]

    ans = build_deterministic_grounded_answer(
        query_text="I was detained without explanation by police",
        retrieved_provisions=sample_provisions,
        jurisdiction_name="All India / Central"
    )

    required_keys = [
        "issue_summary", "jurisdiction", "clarifying_questions",
        "potentially_relevant_laws", "why_it_may_apply", "conditions",
        "exceptions", "possible_next_steps", "lawyer_practice_areas",
        "official_sources", "limitations", "needs_legal_review"
    ]

    for key in required_keys:
        assert key in ans, f"Missing required key: {key}"

    assert ans["potentially_relevant_laws"] == ["prov_const_art21"]
    assert "prov_const_art21" in ans["potentially_relevant_laws"]
