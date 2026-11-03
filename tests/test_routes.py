"""
NyayaGuide Route Integration Tests
Tests HTTP endpoints, homepage loading, form submissions, and JSON APIs.
"""
import pytest
from app import create_app
from legal.init_db import init_database
from legal.ingest import run_ingestion

@pytest.fixture
def client(tmp_path):
    test_db = tmp_path / "test_nyayaguide.db"
    init_database(test_db)
    run_ingestion(test_db)
    
    app = create_app("testing")
    app.config["DATABASE_PATH"] = test_db
    app.config["TESTING"] = True
    
    with app.test_client() as client:
        yield client

def test_homepage_loads(client):
    """Test that homepage returns 200 and displays key brand text."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Nyaya" in html
    assert "Know Your Rights" in html
    assert "Speak Your Situation" in html
    assert "Find Sections" in html

def test_find_sections_get_and_post(client):
    """Test search workflow via POST and GET."""
    # POST with valid situation
    post_res = client.post("/find-sections", data={
        "situation_text": "An online seller took my money but did not deliver the product.",
        "jurisdiction": "IN-CENTRAL",
        "category": "auto"
    }, follow_redirects=True)
    assert post_res.status_code == 200
    post_html = post_res.data.decode("utf-8")
    assert "Legal Awareness Assessment" in post_html
    assert "Potentially Applicable Provisions" in post_html

    # Short input validation redirect
    short_res = client.post("/find-sections", data={
        "situation_text": "hi",
        "jurisdiction": "IN-CENTRAL"
    }, follow_redirects=True)
    assert short_res.status_code == 200
    assert "Please describe your situation" in short_res.data.decode("utf-8")

def test_browse_laws_route(client):
    """Test law catalog route and category filtering."""
    res = client.get("/browse-laws")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "The Constitution of India" in html
    assert "Bharatiya Nyaya Sanhita" in html

def test_law_detail_route(client):
    """Test individual Act detail route."""
    res = client.get("/law/act_constitution")
    assert res.status_code == 200
    assert "The Constitution of India" in res.data.decode("utf-8")

def test_law_detail_404(client):
    """Test nonexistent law returns 404."""
    res = client.get("/law/act_nonexistent_999")
    assert res.status_code == 404

def test_legal_resources_route(client):
    """Test legal aid directory."""
    res = client.get("/legal-resources")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "National Legal Services Authority" in html
    assert "15100" in html

def test_download_data_route(client):
    """Test data download dashboard and JSON/CSV endpoints."""
    res = client.get("/download-data")
    assert res.status_code == 200
    assert "Truthful Jurisdiction Coverage Dashboard" in res.data.decode("utf-8")

    # Test JSON download
    json_res = client.get("/download-dataset/json")
    assert json_res.status_code == 200
    assert json_res.mimetype == "application/json"

    # Test CSV download
    csv_res = client.get("/download-dataset/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.mimetype

def test_health_check(client):
    """Test /health endpoint."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"

def test_api_search_endpoint(client):
    """Test /api/search JSON endpoint."""
    res = client.post("/api/search", json={
        "query": "rental deposit not refunded by landlord",
        "jurisdiction": "IN-CENTRAL"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "explanation" in data
    assert "provisions" in data
