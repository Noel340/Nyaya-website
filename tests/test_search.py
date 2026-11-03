"""
NyayaGuide Search & Retrieval Unit Tests
Tests FTS5 full-text matching, exact section lookups, and ranking.
"""
import pytest
from pathlib import Path
from legal.init_db import init_database
from legal.ingest import run_ingestion
from legal.search import search_provisions
from legal.retrieval import retrieve_grounding_context, detect_topic

@pytest.fixture(scope="module")
def setup_db(tmp_path_factory):
    fn = tmp_path_factory.mktemp("db") / "test_search.db"
    init_database(fn)
    run_ingestion(fn)
    return fn

def test_fts5_consumer_fraud_search(setup_db):
    """Test FTS5 search on consumer fraud query."""
    results = search_provisions(
        query_text="online seller took money but did not deliver product",
        db_path=setup_db
    )
    assert len(results) > 0
    # Should surface CPA Section 2(47) / BNS Section 318
    act_ids = [r["act_id"] for r in results]
    assert ("act_cpa_2019" in act_ids) or ("act_bns_2023" in act_ids)

def test_direct_citation_lookup(setup_db):
    """Test searching with explicit section citation e.g. 'Article 21' or 'Section 138'."""
    results_art21 = search_provisions("I want to know about Article 21", db_path=setup_db)
    assert any(r["provision_number"] == "21" and r["act_id"] == "act_constitution" for r in results_art21)

    results_sec138 = search_provisions("cheque bounced under Section 138", db_path=setup_db)
    assert any(r["provision_number"] == "138" and r["act_id"] == "act_ni_1881" for r in results_sec138)

def test_topic_detection_heuristics():
    """Test auto-topic detection on common situation text."""
    assert detect_topic("Someone created a fake profile with my morphed photo on Instagram") == "topic_privacy"
    assert detect_topic("I got an OTP phishing call and money was deducted from bank") == "topic_cybercrime"
    assert detect_topic("Landlord refuses to return my rental security deposit") == "topic_property"
    assert detect_topic("My employer has not paid my salary for two months") == "topic_employment"

def test_grounding_context_retrieval(setup_db):
    """Test complete grounding retrieval context."""
    ctx = retrieve_grounding_context(
        query_text="unpaid salary and sudden termination by employer",
        jurisdiction_id="IN-CENTRAL"
    )
    assert ctx["provisions_count"] > 0
    assert any("cow" in p["id"] or "constitution" in p["id"] for p in ctx["retrieved_provisions"])
