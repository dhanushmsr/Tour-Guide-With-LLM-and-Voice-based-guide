import os
import json
from dotenv import load_dotenv
from sqlalchemy import func

from flask import Flask, request, render_template, jsonify

# Load Environment Variables
load_dotenv()

# --- NEW: Absolute Path Definition for cPanel ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Import Inkwake Module Suite
from app.database.database import log_security_event, save_enquiry, SessionLocal, Review, init_db
from app.api import explorer, admin, bookings, chatbot

# --- SYNCHRONOUS STARTUP (Bypasses the Lifespan Freeze in cPanel) ---

# 1. Ensure directories exist using absolute paths
directories = [
    os.path.join(BASE_DIR, "static", "audio"), 
    os.path.join(BASE_DIR, "static", "images"), 
    os.path.join(BASE_DIR, "static", "reference_monuments"), 
    os.path.join(BASE_DIR, "app", "data")
]
for folder in directories:
    os.makedirs(folder, exist_ok=True)
    
# 2. Initialize JSON DB files if missing using absolute paths
db_files = {
    os.path.join(BASE_DIR, "app", "data", "sites_info.json"): [],
    os.path.join(BASE_DIR, "app", "data", "users_info.json"): []
}
for path, default_val in db_files.items():
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_val, f)

# 3. Initialize MySQL Database Tables (DISABLED FOR TESTING)
# try:
#     init_db()
#     print("Database tables verified/created successfully.")
# except Exception as e:
#     print(f"Database initialization failed: {e}")

print("Inkwake Heritage Node [v2.6] Online & Secured")

# Create Flask App with explicit static folder path for cPanel stability
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))

# --- Security & Traffic Middleware ---
@app.before_request
def monitor_activity():
    """Logs sensitive node access (Admin/Recognition) to the security vault."""
    # Flask uses request.remote_addr for the client IP
    client_ip = request.remote_addr
    path = request.path
    
    if path.startswith("/admin") or path.startswith("/recognition"):
        log_security_event(client_ip, f"ACCESS_TRIGGER: {request.method} {path}")

# --- Blueprint Integration (Replaces FastAPI Routers) ---
app.register_blueprint(explorer.explorer_bp)
app.register_blueprint(admin.admin_bp)
app.register_blueprint(bookings.bookings_bp) 
app.register_blueprint(chatbot.chatbot_bp) # Chatbot is now active!
# app.register_blueprint(recognition.recognition_bp)

# --- Core Application Routes ---

@app.route("/")
def home():
    return render_template("index.html")
    
@app.route("/about")
def about_page():
    return render_template("about.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/chatbot-ui")
def oracle_interface():
    return render_template("chatbot_page.html")

@app.route("/enquiry")
def enquiry_page():
    return render_template("enquiry_page.html")

@app.route("/submit-enquiry", methods=["POST"])
def handle_enquiry():
    """
    Handles POST data from the Enquiry Page. 
    Returns JSON for the new AJAX frontend to handle success states without reloading.
    """
    name = request.form.get("name")
    email = request.form.get("email")
    subject = request.form.get("subject")
    message = request.form.get("message")
    
    success = save_enquiry(name, email, subject, message)
    if success:
        return jsonify({"status": "success", "message": "Enquiry Archived in Vault"})
    
    return jsonify({"status": "error", "message": "Vault Persistence Failure"}), 500

@app.route("/site/<site_id>")
def monument_details(site_id):
    # Use absolute path
    json_path = os.path.join(BASE_DIR, "app", "data", "sites_info.json")
    site_data = None
    
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            sites = json.load(f)
            site_data = next((s for s in sites if s.get("id") == site_id), None)
    
    if not site_data:
        return render_template("404.html"), 404
        
    # FETCH REVIEWS & CALCULATE AVERAGE RATING
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(Review.site_id == site_id).order_by(Review.id.desc()).all()
        
        if reviews:
            avg_rating = db.query(func.avg(Review.rating)).filter(Review.site_id == site_id).scalar()
            site_data['average_rating'] = round(avg_rating, 1)
            site_data['review_count'] = len(reviews)
        else:
            site_data['average_rating'] = 0.0
            site_data['review_count'] = 0
            
    except Exception as e:
        print(f"Review Fetch Error: {e}")
        reviews = []
        site_data['average_rating'] = 0.0
        site_data['review_count'] = 0
    finally:
        db.close()
        
    return render_template("site_detail.html", site=site_data, reviews=reviews)

@app.route("/legal")
def legal_page():
    return render_template("terms.html")



# --- Custom 404 Sentinel ---
@app.errorhandler(404)
def custom_404_handler(e):
    return render_template("404.html"), 404

# --- Server Launch ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)