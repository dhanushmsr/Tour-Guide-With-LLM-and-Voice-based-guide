import os
import json
import csv
import io
import time
import threading
from datetime import datetime

from flask import Blueprint, request, render_template, redirect, url_for, make_response, abort, Response, jsonify

# Import custom database functions, Booking, PromoCode AND the new email function!
from app.database import get_all_enquiries, delete_enquiry, SessionLocal, Booking, PromoCode
from app.api.bookings import send_review_request_email

# Replace APIRouter with Flask Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Configuration Constants
DATA_PATH = "app/data/sites_info.json"
USER_PATH = "app/data/users_info.json"
UPLOAD_DIR = "static/images"
ADMIN_PWD = os.getenv("ADMIN_PASSWORD", "admin123")

# Initialization Protocol
os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

if not os.path.exists(USER_PATH):
    with open(USER_PATH, "w", encoding="utf-8") as f:
        json.dump([], f)

# --- Security Protocol ---
def check_auth():
    """Verifies the transient session cookie in Flask."""
    user_session = request.cookies.get("admin_session")
    if user_session != "authenticated":
        abort(401)
    return True

# --- Authentication ---
@admin_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PWD:
            # Create redirect response and set the auth cookie
            resp = make_response(redirect(url_for('admin.admin_dashboard')))
            resp.set_cookie(key="admin_session", value="authenticated", httponly=True, samesite="Lax")
            return resp
        return redirect(url_for('admin.login_page', error="InvalidPassword"))
    
    # GET request returns the login template
    return render_template("admin_login.html")

@admin_bp.route("/logout")
def logout():
    resp = make_response(redirect(url_for('admin.login_page')))
    # Delete the cookie by expiring it immediately
    resp.set_cookie("admin_session", "", expires=0)
    return resp

# --- Dashboard & Management ---
@admin_bp.route("/dashboard")
def admin_dashboard():
    try:
        check_auth()
    except Exception:
        return redirect(url_for('admin.login_page'))
        
    sites = []
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            try: sites = json.load(f)
            except: sites = []

    registered_users = []
    if os.path.exists(USER_PATH):
        with open(USER_PATH, "r", encoding="utf-8") as f:
            try: registered_users = json.load(f)
            except: registered_users = []

    enquiries = get_all_enquiries()
    
    # --- FETCH BOOKINGS, DYNAMIC COUNTDOWN & PROMO CODES ---
    db = SessionLocal()
    today = datetime.now().date()
    
    try:
        bookings = db.query(Booking).order_by(Booking.id.desc()).all()
        for b in bookings:
            # 1. Parse the JSON text back into a Python list
            b.parsed_travelers = json.loads(b.travelers_details) if getattr(b, 'travelers_details', None) else []
            
            # 2. DYNAMIC COUNTDOWN CALCULATION
            try:
                start_date = datetime.strptime(b.travel_date, "%Y-%m-%d").date()
                delta = (start_date - today).days
                
                if delta > 0:
                    b.days_to_start = f"{delta} DAYS TO START"
                elif delta == 0:
                    b.days_to_start = "STARTS TODAY"
                else:
                    b.days_to_start = "TRIP ACTIVE / EXPIRED"
            except Exception:
                b.days_to_start = "DATE ERROR"
            
        # 3. Fetch Promo Codes
        promo_codes = db.query(PromoCode).order_by(PromoCode.id.desc()).all()
        
    except Exception as e:
        print(f"Error fetching DB records: {e}")
        bookings = []
        promo_codes = []
    finally:
        db.close()
                
    return render_template(
        "admin_panel.html", 
        sites=sites, 
        registered_users=registered_users,
        enquiries=enquiries,
        bookings=bookings,
        promo_codes=promo_codes
    )

# --- Inbox / Enquiry Actions ---

@admin_bp.route("/users")
def view_all_users():
    """Renders a dedicated page to view all registered user profiles."""
    check_auth()
    
    registered_users = []
    if os.path.exists(USER_PATH):
        with open(USER_PATH, "r", encoding="utf-8") as f:
            try: 
                registered_users = json.load(f)
            except: 
                registered_users = []
                
    # Reverse the list so the newest users show up at the top
    registered_users.reverse()
                
    return render_template("admin_users.html", users=registered_users)

@admin_bp.route("/resolve-enquiry/<int:id>", methods=["POST"])
def resolve_enquiry(id):
    check_auth()
    try:
        delete_enquiry(id)
    except Exception as e:
        print(f"❌ Failed to resolve enquiry {id}: {e}")
    return redirect(url_for('admin.admin_dashboard'))

# --- Identity Vault Actions ---

@admin_bp.route("/log-user", methods=["POST"])
def log_user():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    try:
        users = []
        if os.path.exists(USER_PATH):
            with open(USER_PATH, "r", encoding="utf-8") as f:
                try: users = json.load(f)
                except: users = []
        
        users.append({
            "name": name, 
            "email": email, 
            "phone": phone, 
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
            
        with open(USER_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@admin_bp.route("/delete-user/<username>", methods=["POST"])
def delete_user(username):
    check_auth()
    if os.path.exists(USER_PATH):
        with open(USER_PATH, "r", encoding="utf-8") as f:
            users = json.load(f)
        users = [u for u in users if u.get("name") != username]
        with open(USER_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route("/clear-all-users", methods=["POST"])
def clear_all_users():
    check_auth()
    with open(USER_PATH, "w", encoding="utf-8") as f:
        json.dump([], f)
    return redirect(url_for('admin.admin_dashboard'))

# --- Heritage Vault Actions (CRUD) ---

@admin_bp.route("/add")
def add_site_page():
    check_auth()
    return render_template("admin_add_site.html", edit_mode=False)

@admin_bp.route("/edit/<site_id>")
def edit_site_page(site_id):
    check_auth()
    site_to_edit = None
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            sites = json.load(f)
            site_to_edit = next((s for s in sites if s.get("id") == site_id), None)
    
    if not site_to_edit:
        return redirect(url_for('admin.admin_dashboard', error="NotFound"))

    return render_template("admin_add_site.html", site=site_to_edit, edit_mode=True)

@admin_bp.route("/add-site", methods=["POST"])
def add_site():
    check_auth()
    
    # Extract forms in Flask
    name = request.form.get("name")
    category = request.form.get("category")
    district = request.form.get("district")
    history_text = request.form.get("history_text")
    culture = request.form.get("culture")
    lat = float(request.form.get("lat", 0.0))
    lng = float(request.form.get("lng", 0.0))
    original_price = float(request.form.get("original_price", 0.0))
    discounted_price = float(request.form.get("discounted_price", 0.0))
    trip_days = int(request.form.get("trip_days", 1))
    gallery_urls = request.form.get("gallery_urls", "")
    image_url = request.form.get("image_url")
    
    # Extract files in Flask
    image_file = request.files.get("image_file")
    gallery_files = request.files.getlist("gallery_files")
    
    final_image_path = image_url
    if image_file and image_file.filename:
        ext = os.path.splitext(image_file.filename)[1]
        local_filename = f"{name.lower().replace(' ', '_')}_main{ext}"
        filepath = os.path.join(UPLOAD_DIR, local_filename)
        image_file.save(filepath) # Flask save method
        final_image_path = f"/static/images/{local_filename}"

    gallery_paths = [u.strip() for u in gallery_urls.split(",") if u.strip()]
    if gallery_files:
        for index, gf in enumerate(gallery_files):
            if gf.filename:
                ext = os.path.splitext(gf.filename)[1]
                gal_filename = f"{name.lower().replace(' ', '_')}_gal_{int(time.time())}_{index}{ext}"
                gal_filepath = os.path.join(UPLOAD_DIR, gal_filename)
                gf.save(gal_filepath)
                gallery_paths.append(f"/static/images/{gal_filename}")

    sites = []
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            try: sites = json.load(f)
            except: sites = []
    
    sites.append({
        "id": name.lower().replace(" ", "-"), "name": name, "category": category,
        "district": district, "image_url": final_image_path,
        "gallery": gallery_paths,
        "original_price": original_price, "discounted_price": discounted_price, "trip_days": trip_days,
        "history_text": history_text, "culture": culture,
        "coordinates": {"lat": lat, "lng": lng}
    })
    
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(sites, f, indent=4)
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route("/update-site/<old_id>", methods=["POST"])
def update_site(old_id):
    check_auth()
    
    name = request.form.get("name")
    category = request.form.get("category")
    district = request.form.get("district")
    history_text = request.form.get("history_text")
    culture = request.form.get("culture")
    lat = float(request.form.get("lat", 0.0))
    lng = float(request.form.get("lng", 0.0))
    original_price = float(request.form.get("original_price", 0.0))
    discounted_price = float(request.form.get("discounted_price", 0.0))
    trip_days = int(request.form.get("trip_days", 1))
    image_url = request.form.get("image_url")
    existing_gallery = request.form.get("existing_gallery", "")
    gallery_urls = request.form.get("gallery_urls", "")
    
    image_file = request.files.get("image_file")
    gallery_files = request.files.getlist("gallery_files")
    
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            sites = json.load(f)
        
        for s in sites:
            if s["id"] == old_id:
                if image_file and image_file.filename:
                    ext = os.path.splitext(image_file.filename)[1]
                    local_filename = f"{name.lower().replace(' ', '_')}_main{ext}"
                    filepath = os.path.join(UPLOAD_DIR, local_filename)
                    image_file.save(filepath)
                    s["image_url"] = f"/static/images/{local_filename}"
                elif image_url:
                    s["image_url"] = image_url

                current_gallery = [g.strip() for g in existing_gallery.split(",") if g.strip()]
                new_urls = [u.strip() for u in gallery_urls.split(",") if u.strip() and u.strip() not in current_gallery]
                current_gallery.extend(new_urls)

                if gallery_files:
                    for index, gf in enumerate(gallery_files):
                        if gf.filename:
                            ext = os.path.splitext(gf.filename)[1]
                            gal_filename = f"{name.lower().replace(' ', '_')}_upd_{int(time.time())}_{index}{ext}"
                            gal_filepath = os.path.join(UPLOAD_DIR, gal_filename)
                            gf.save(gal_filepath)
                            current_gallery.append(f"/static/images/{gal_filename}")

                s.pop("video_url", None)

                s.update({
                    "name": name, "category": category, "district": district,
                    "history_text": history_text, "culture": culture,
                    "original_price": original_price, "discounted_price": discounted_price, "trip_days": trip_days,
                    "gallery": current_gallery,
                    "coordinates": {"lat": lat, "lng": lng}
                })
        
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(sites, f, indent=4)
            
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route("/delete/<site_id>", methods=["POST"])
def delete_site(site_id):
    check_auth()
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            sites = json.load(f)
        sites = [s for s in sites if s.get("id") != site_id]
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(sites, f, indent=4)
    return redirect(url_for('admin.admin_dashboard'))

# --- Booking Ledger Extras ---

@admin_bp.route("/archive-booking/<int:booking_id>", methods=["POST"])
def archive_booking(booking_id):
    """Manually moves an active trip to History AND asks for a review."""
    check_auth()
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if booking:
            booking.payment_status = "Archived"
            db.commit()
            
            # TRIGGER THE REVIEW EMAIL USING FLASK/PYTHON THREADING!
            threading.Thread(
                target=send_review_request_email, 
                args=(booking.email, booking.traveler_name, booking.booking_ref, booking.site_name)
            ).start()
            
    except Exception as e:
        db.rollback()
        print(f"Archive Error: {e}")
    finally:
        db.close()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route("/export-ledger")
def export_ledger():
    """Generates a downloadable CSV of the entire financial ledger."""
    check_auth()
    db = SessionLocal()
    bookings = db.query(Booking).order_by(Booking.id.desc()).all()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Ref ID', 'Traveler', 'Email', 'Phone', 'Package', 'Travel Date', 'Days', 'Pax', 'Revenue', 'Status', 'Timestamp'])
    
    for b in bookings:
        writer.writerow([b.booking_ref, b.traveler_name, b.email, b.phone, b.site_name, b.travel_date, b.trip_days, b.travelers_count, b.total_amount, b.payment_status, b.timestamp])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Inkwake_Ledger_{time.strftime('%Y%m%d')}.csv"}
    )

# --- PROMO CODE MANAGEMENT (CRUD) ---

@admin_bp.route("/create-promo", methods=["POST"])
def create_promo():
    check_auth()
    code = request.form.get("code")
    discount = int(request.form.get("discount", 0))
    
    db = SessionLocal()
    try:
        new_promo = PromoCode(code=code.upper(), discount_percentage=discount, is_active=True)
        db.add(new_promo)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Promo Error: {e}")
    finally:
        db.close()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route("/update-promo/<int:promo_id>", methods=["POST"])
def update_promo(promo_id):
    """Updates an existing Promo Code."""
    check_auth()
    code = request.form.get("code")
    discount = int(request.form.get("discount", 0))
    is_active = request.form.get("is_active", "false")
    
    db = SessionLocal()
    try:
        promo = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
        if promo:
            promo.code = code.upper()
            promo.discount_percentage = discount
            promo.is_active = True if is_active.lower() == "true" else False
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Update Promo Error: {e}")
    finally:
        db.close()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route("/delete-promo/<int:promo_id>", methods=["POST"])
def delete_promo(promo_id):
    """Permanently deletes a Promo Code."""
    check_auth()
    db = SessionLocal()
    try:
        promo = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
        if promo:
            db.delete(promo)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Delete Promo Error: {e}")
    finally:
        db.close()
    return redirect(url_for('admin.admin_dashboard'))