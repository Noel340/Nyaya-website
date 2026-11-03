"""
NyayaGuide Data Validation & Transition Tests
Tests criminal transition logic (BNS 2023 vs IPC 1860) and dataset exports.
"""
import pytest
from datetime import datetime
from legal.normalize import parse_incident_date
from legal.search import search_provisions
from legal.export_dataset import export_provisions_json, export_provisions_csv, generate_coverage_report
from legal.init_db import init_database
from legal.ingest import run_ingestion

@pytest.fixture(scope="module")
def setup_db(tmp_path_factory):
    fn = tmp_path_factory.mktemp("db") / "test_data.db"
    init_database(fn)
    run_ingestion(fn)
    return fn

def test_bns_transition_date_parser():
    """Test incident date parsing across the 1 July 2024 milestone."""
    # Pre-BNS (IPC era)
    dt_old, is_post_bns_old = parse_incident_date("2024-05-15")
    assert dt_old == datetime(2024, 5, 15)
    assert is_post_bns_old is False

    # Exact transition day (1 July 2024)
    dt_day1, is_post_bns_day1 = parse_incident_date("2024-07-01")
    assert is_post_bns_day1 is True

    # Post-BNS
    dt_new, is_post_bns_new = parse_incident_date("2025-01-10")
    assert is_post_bns_new is True

    # None / Unspecified date defaults to current era
    _, is_post_default = parse_incident_date(None)
    assert is_post_default is True

def test_bns_criminal_transition_search(setup_db):
    """Test that post-July 2024 query highlights BNS 318 while pre-July query highlights IPC 420."""
    # Post-BNS search
    results_post = search_provisions(
        query_text="cheating and financial fraud",
        incident_date_str="2025-02-01",
        db_path=setup_db
    )
    bns_item = next((r for r in results_post if r["id"] == "prov_bns_sec318"), None)
    assert bns_item is not None

    # Pre-BNS search
    results_pre = search_provisions(
        query_text="cheating and financial fraud",
        incident_date_str="2023-11-20",
        db_path=setup_db
    )
    ipc_item = next((r for r in results_pre if r["id"] == "prov_ipc_sec420"), None)
    assert ipc_item is not None

def test_dataset_export_integrity(setup_db, tmp_path):
    """Test exporting provisions to JSON & CSV and verify content."""
    json_path = tmp_path / "provisions.json"
    csv_path = tmp_path / "provisions.csv"

    cnt_json = export_provisions_json(setup_db, json_path)
    cnt_csv = export_provisions_csv(setup_db, csv_path)

    assert cnt_json > 0
    assert cnt_json == cnt_csv
    assert json_path.exists()
    assert csv_path.exists()

    cov = generate_coverage_report(setup_db)
    assert cov["total_jurisdictions"] >= 37
    assert cov["jurisdictions_with_seed_data"] > 0
