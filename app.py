"""
NyayaGuide — AI-Powered Indian Legal Awareness Platform
Flask Application & Route Handlers
"""
import os
from pathlib import Path
from flask import (
    Flask, render_template, request, jsonify, redirect, 
    url_for, flash, send_file, abort
)
from config import config_by_name, BASE_DIR
from legal.init_db import init_database
from legal.export_dataset import (
    export_provisions_json, export_provisions_csv, generate_coverage_report
)
from services.legal_service import LegalService
from services.lawyer_service import LawyerService
from services.ai_service import AIService

def create_app(config_name: str = "default") -> Flask:
    """Flask Application Factory."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))
    
    # Ensure database exists and is initialized
    db_path = Path(app.config["DATABASE_PATH"])
    if not db_path.exists():
        init_database(db_path)
        # Run seed ingestion automatically if DB was just initialized
        try:
            from legal.ingest import run_ingestion
            run_ingestion(db_path)
        except Exception as e:
            app.logger.warning(f"Seed ingestion during app startup notice: {e}")
            
    # Initialize Services
    legal_service = LegalService(db_path=db_path)
    lawyer_service = LawyerService(db_path=db_path)
    ai_service = AIService(api_key=app.config.get("GEMINI_API_KEY"))

    # -------------------------------------------------------------
    # WEB ROUTES
    # -------------------------------------------------------------

    @app.route("/")
    def index():
        """Homepage: Hero, Situation input panel, voice controls, categories, examples."""
        jurisdictions = legal_service.get_all_jurisdictions()
        topics = legal_service.get_all_topics()
        return render_template(
            "index.html",
            jurisdictions=jurisdictions,
            topics=topics
        )

    @app.route("/find-sections", methods=["GET", "POST"])
    def find_sections():
        """Core Search & Grounded Analysis Workflow."""
        if request.method == "POST":
            query_text = request.form.get("situation_text", "").strip()
            jurisdiction_id = request.form.get("jurisdiction", "IN-CENTRAL")
            category_id = request.form.get("category", "auto")
            incident_date = request.form.get("incident_date", "").strip() or None
        else:
            query_text = request.args.get("q", "").strip()
            jurisdiction_id = request.args.get("jurisdiction", "IN-CENTRAL")
            category_id = request.args.get("category", "auto")
            incident_date = request.args.get("incident_date", "").strip() or None

        if not query_text or len(query_text) < 4:
            flash("Please describe your situation in at least a few words to identify relevant sections.", "warning")
            return redirect(url_for("index"))

        result = legal_service.process_situation_query(
            query_text=query_text,
            jurisdiction_id=jurisdiction_id,
            topic_id=category_id if category_id != "auto" else None,
            incident_date=incident_date,
            api_key=app.config.get("GEMINI_API_KEY")
        )

        # Get relevant legal aid resources for this jurisdiction
        legal_aid_list = lawyer_service.get_legal_aid_resources(jurisdiction_id=jurisdiction_id)

        return render_template(
            "results.html",
            query_text=query_text,
            incident_date=incident_date,
            explanation=result["explanation"],
            provisions=result["provisions"],
            legal_aid_list=legal_aid_list[:4]
        )

    @app.route("/browse-laws")
    def browse_laws():
        """Central & State Legislation catalog."""
        category = request.args.get("category", "").strip() or None
        jurisdiction = request.args.get("jurisdiction", "").strip() or None
        
        acts = legal_service.get_acts(jurisdiction_id=jurisdiction, category=category)
        jurisdictions = legal_service.get_all_jurisdictions()
        
        # Get unique categories
        all_acts = legal_service.get_acts()
        categories = sorted(list({a["category"] for a in all_acts if a.get("category")}))

        return render_template(
            "browse_laws.html",
            acts=acts,
            jurisdictions=jurisdictions,
            categories=categories,
            selected_category=category,
            selected_jurisdiction=jurisdiction
        )

    @app.route("/law/<law_id>")
    def law_detail(law_id: str):
        """Dedicated view of an Act and its sections."""
        act = legal_service.get_act_by_id(law_id)
        if not act:
            abort(404)
        return render_template("law_detail.html", act=act)

    @app.route("/legal-resources")
    def legal_resources():
        """Official Legal Aid (NALSA, SLSAs, Helplines) Directory."""
        jurisdiction = request.args.get("jurisdiction", "").strip() or None
        category = request.args.get("category", "").strip() or None
        
        resources = lawyer_service.get_legal_aid_resources(jurisdiction_id=jurisdiction, category=category)
        jurisdictions = legal_service.get_all_jurisdictions()
        
        return render_template(
            "legal_resources.html",
            resources=resources,
            jurisdictions=jurisdictions,
            selected_jurisdiction=jurisdiction,
            selected_category=category
        )

    @app.route("/download-data")
    def download_data():
        """Legal Dataset Download page with coverage statistics."""
        coverage = generate_coverage_report(db_path)
        return render_template("download_data.html", coverage=coverage)

    @app.route("/download-dataset/<format>")
    def export_dataset_file(format: str):
        """Direct download endpoint for machine-readable JSON or CSV dataset."""
        export_dir = BASE_DIR / "data" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "json":
            out_file = export_dir / "nyayaguide_provisions.json"
            export_provisions_json(db_path, out_file)
            return send_file(
                out_file, 
                as_attachment=True, 
                download_name="nyayaguide_verified_provisions.json",
                mimetype="application/json"
            )
        elif format.lower() == "csv":
            out_file = export_dir / "nyayaguide_provisions.csv"
            export_provisions_csv(db_path, out_file)
            return send_file(
                out_file, 
                as_attachment=True, 
                download_name="nyayaguide_verified_provisions.csv",
                mimetype="text/csv"
            )
        else:
            abort(400)

    @app.route("/download-results")
    def download_results():
        """Download or print report redirect."""
        return redirect(url_for("find_sections", **request.args))

    @app.route("/about")
    def about():
        """About NyayaGuide, Mission, Methodology, Anti-hallucination Ethics."""
        return render_template("about.html")

    @app.route("/disclaimer")
    def disclaimer():
        """Full Legal Disclaimer & Citizen Safety Advice."""
        return render_template("disclaimer.html")

    # -------------------------------------------------------------
    # JSON APIs
    # -------------------------------------------------------------

    @app.route("/api/search", methods=["GET", "POST"])
    def api_search():
        """JSON Search API endpoint."""
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            query = data.get("query", "").strip()
            jurisdiction = data.get("jurisdiction", "IN-CENTRAL")
            topic = data.get("topic")
            incident_date = data.get("incident_date")
        else:
            query = request.args.get("query", "").strip()
            jurisdiction = request.args.get("jurisdiction", "IN-CENTRAL")
            topic = request.args.get("topic")
            incident_date = request.args.get("incident_date")

        if not query:
            return jsonify({"error": "Query string is required"}), 400

        res = legal_service.process_situation_query(
            query_text=query,
            jurisdiction_id=jurisdiction,
            topic_id=topic,
            incident_date=incident_date,
            api_key=app.config.get("GEMINI_API_KEY")
        )
        return jsonify(res)

    @app.route("/api/ask", methods=["POST"])
    def api_ask():
        """AI Grounded Explanation API endpoint."""
        data = request.get_json(silent=True) or {}
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"error": "Query string is required"}), 400

        jurisdiction = data.get("jurisdiction", "IN-CENTRAL")
        topic = data.get("topic")
        incident_date = data.get("incident_date")

        res = legal_service.process_situation_query(
            query_text=query,
            jurisdiction_id=jurisdiction,
            topic_id=topic,
            incident_date=incident_date,
            api_key=app.config.get("GEMINI_API_KEY")
        )
        return jsonify({
            "explanation": res["explanation"],
            "provisions_count": len(res["provisions"])
        })

    @app.route("/health")
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "service": "NyayaGuide Indian Legal Awareness Platform",
            "database": str(db_path.name),
            "database_exists": db_path.exists(),
            "ai_configured": bool(app.config.get("GEMINI_API_KEY"))
        })

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    return app

if __name__ == "__main__":
    app = create_app("development")
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting NyayaGuide on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)
