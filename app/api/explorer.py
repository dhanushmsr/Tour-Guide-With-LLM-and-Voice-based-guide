import os
import json
from flask import Blueprint, request, render_template, jsonify

# Replace APIRouter with Flask Blueprint
explorer_bp = Blueprint('explorer', __name__, url_prefix='/explorer')

# Path to the Inkwake Digital Archives
DATA_PATH = "app/data/sites_info.json"

@explorer_bp.route("/")
def explorer_home():
    """
    Renders the Heritage Circuits explorer. 
    Supports dynamic filtering by Dynasty and backend-ready search queries.
    """
    # In Flask, URL query parameters are accessed via request.args
    dynasty = request.args.get("dynasty")
    search = request.args.get("search")

    all_sites = []
    categories = []
    active_filter = dynasty if dynasty else "All"

    try:
        # 1. Load the Heritage Scrolls (JSON Database)
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                all_sites = json.load(f)
        
        # 2. Extract Unique Dynasties for the Filter Navigation
        # Using sorted(set()) ensures buttons are alphabetical and unique
        categories = sorted(list(set(
            site.get("category") for site in all_sites if site.get("category")
        )))

        # 3. Apply Dynasty Filter Logic
        if dynasty and dynasty != "All":
            filtered_sites = [
                s for s in all_sites 
                if s.get("category", "").lower() == dynasty.lower()
            ]
        else:
            filtered_sites = all_sites

        # 4. Optional: Backend Search Integration
        # While the frontend has instant search, this handles direct URL queries
        if search:
            query = search.lower()
            filtered_sites = [
                s for s in filtered_sites 
                if query in s.get("name", "").lower() or 
                   query in s.get("district", "").lower()
            ]

    except Exception as e:
        print(f"Digital Archive Access Error: {e}")
        filtered_sites = []
        categories = ["Chola", "Pandya", "Pallava", "Nayak"] # Fallback placeholders

    # 5. Execute Template Rendering
    return render_template(
        "explorer.html",
        request=request,
        sites=filtered_sites,
        categories=categories,
        active_filter=active_filter,
        search_query=search
    )

@explorer_bp.route("/api/sites")
def get_sites_json():
    """Helper API endpoint for dynamic map updates or external integrations."""
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify([])