import os
import json
import uuid
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

from flask import Blueprint, request, render_template, redirect, url_for, jsonify

# Import the Review model along with the others
from app.database import SessionLocal, Booking, PromoCode, Review 

# Replace APIRouter with Flask Blueprint
bookings_bp = Blueprint('bookings', __name__, url_prefix='/bookings')

DATA_PATH = "app/data/sites_info.json"

# --- AUTOMATED EMAIL ENGINE ---
def send_booking_email(receiver_email: str, traveler_name: str, booking_ref: str, site_name: str):
    sender_email = os.getenv("EMAIL_USER", "your_email@gmail.com") 
    password = os.getenv("EMAIL_PASS", "your_app_password_here") 
    
    if sender_email == "your_email@gmail.com":
        print(f"⚠️ Email skipped: SMTP credentials not configured. Intended for {receiver_email}")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Booking Confirmed: {site_name}"
    message["From"] = sender_email
    message["To"] = receiver_email

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; padding: 20px;">
        <div style="background: #f97316; padding: 20px; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0;">Inkwake Heritage</h1>
        </div>
        <div style="padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 10px 10px;">
            <h2>Vanakkam {traveler_name},</h2>
            <p>Your premium heritage journey to <b>{site_name}</b> has been successfully secured.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin: 0; color: #f97316;">Booking Reference: {booking_ref}</h3>
                <p style="margin: 5px 0 0 0;">Status: <b>PAID</b></p>
            </div>
            <p>You can view your detailed itinerary and download your Digital QR Ticket by logging into our Traveler Portal using your registered mobile number.</p>
            <br>
            <p>Safe Travels,<br><b>The Inkwake Curation Team</b></p>
        </div>
      </body>
    </html>
    """
    message.attach(MIMEText(html_content, "html"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            print(f"📧 Success: Ticket emailed to {receiver_email}")
    except Exception as e:
        print(f"⚠️ Email Failed: {e}")


def send_review_request_email(receiver_email: str, traveler_name: str, booking_ref: str, site_name: str):
    """Automatically emails the traveler asking for a 5-star review after their trip."""
    sender_email = os.getenv("EMAIL_USER", "your_email@gmail.com") 
    password = os.getenv("EMAIL_PASS", "your_app_password_here") 
    
    if sender_email == "your_email@gmail.com":
        print(f"⚠️ Review Email skipped: SMTP credentials not configured. Intended for {receiver_email}")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = f"How was your trip to {site_name}?"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Link to the review form
    review_link = f"http://127.0.0.1:8000/bookings/leave-review/{booking_ref}"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; padding: 20px;">
        <div style="background: #0f172a; padding: 20px; border-radius: 10px; text-align: center;">
            <h1 style="color: #f97316; margin: 0;">Welcome Back, {traveler_name}!</h1>
            <p style="color: white; margin-top: 10px;">We hope you had an unforgettable time at <b>{site_name}</b>.</p>
            <br>
            <a href="{review_link}" style="background: #f97316; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">Rate Your Experience</a>
            <br><br>
            <p style="color: #94a3b8; font-size: 12px;">Your feedback helps us preserve heritage and guide future travelers.</p>
        </div>
      </body>
    </html>
    """
    message.attach(MIMEText(html_content, "html"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            print(f"⭐ Review Request emailed to {receiver_email}")
    except Exception as e:
        print(f"⚠️ Review Email Failed: {e}")


# --- PROMO CODE VALIDATION API ---
@bookings_bp.route("/validate-promo/<code>")
def validate_promo(code):
    db = SessionLocal()
    promo = db.query(PromoCode).filter(PromoCode.code == code.upper(), PromoCode.is_active == True).first()
    db.close()
    if promo:
        return jsonify({"valid": True, "discount": promo.discount_percentage})
    return jsonify({"valid": False, "discount": 0})


@bookings_bp.route("/checkout/<site_id>")
def checkout_page(site_id):
    site = None
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            sites = json.load(f)
            site = next((s for s in sites if s.get("id") == site_id), None)
            
    if not site:
        return redirect('/explorer')
        
    db = SessionLocal()
    active_promos = db.query(PromoCode).filter(PromoCode.is_active == True).all()
    db.close()
        
    return render_template("checkout.html", request=request, site=site, promo_codes=active_promos)

@bookings_bp.route("/process-payment", methods=["POST"])
def process_payment():
    # Extract form data in Flask
    site_id = request.form.get("site_id")
    site_name = request.form.get("site_name")
    traveler_name = request.form.get("traveler_name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    travel_date = request.form.get("travel_date")
    trip_days = int(request.form.get("trip_days", 1))
    travelers_count = int(request.form.get("travelers_count", 1))
    travelers_json = request.form.get("travelers_json", "[]")
    price_per_person = float(request.form.get("price_per_person", 0.0))
    card_number = request.form.get("card_number", "")
    promo_code = request.form.get("promo_code")

    total_amount = int(travelers_count * price_per_person)
    
    db = SessionLocal()
    if promo_code:
        promo = db.query(PromoCode).filter(PromoCode.code == promo_code.upper(), PromoCode.is_active == True).first()
        if promo:
            discount_amount = total_amount * (promo.discount_percentage / 100)
            total_amount = int(total_amount - discount_amount)

    booking_ref = f"TN-{str(uuid.uuid4().hex[:6]).upper()}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if card_number.endswith("0000"):
        db.close()
        return render_template("payment_failed.html", request=request, site_id=site_id)

    try:
        new_booking = Booking(
            booking_ref=booking_ref, site_id=site_id, site_name=site_name,
            traveler_name=traveler_name, phone=phone, email=email,
            travel_date=travel_date, trip_days=trip_days,
            travelers_count=travelers_count, travelers_details=travelers_json,
            total_amount=total_amount, payment_status="Paid",
            timestamp=timestamp
        )
        db.add(new_booking)
        db.commit()
        
        # Start Background Task using Threading for Flask
        threading.Thread(
            target=send_booking_email, 
            args=(email, traveler_name, booking_ref, site_name)
        ).start()
        
    except Exception as e:
        db.rollback()
        print(f"Booking Save Error: {e}")
    finally:
        db.close()

    return redirect(url_for('bookings.invoice_page', booking_ref=booking_ref))


@bookings_bp.route("/invoice/<booking_ref>")
def invoice_page(booking_ref):
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.booking_ref == booking_ref).first()
    db.close()
    
    if not booking:
        return redirect('/explorer')
        
    booking.parsed_travelers = json.loads(booking.travelers_details) if getattr(booking, 'travelers_details', None) else []
    
    # Calculate End Date & Dynamic Countdown
    today = datetime.now().date()
    try:
        t_date = datetime.strptime(booking.travel_date, "%Y-%m-%d").date()
        end_date = t_date + timedelta(days=booking.trip_days)
        booking.end_date = end_date.strftime("%Y-%m-%d")
        
        if today < t_date:
            days_left = (t_date - today).days
            booking.days_metric = "Starts Tomorrow" if days_left == 1 else f"{days_left} Days to Start"
        elif t_date <= today <= end_date:
            booking.days_metric = "Ongoing Trip"
        else:
            booking.days_metric = "Trip Concluded (Expired)"
    except:
        booking.end_date = "N/A"
        booking.days_metric = "--"
        
    return render_template("invoice.html", request=request, booking=booking)


@bookings_bp.route("/verify/<booking_ref>")
def verify_ticket(booking_ref):
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.booking_ref == booking_ref).first()
    db.close()
    
    if not booking:
        return redirect('/explorer')
        
    booking.parsed_travelers = json.loads(booking.travelers_details) if getattr(booking, 'travelers_details', None) else []
    
    # Calculate End Date, Current Validity Status, and Countdown
    today = datetime.now().date()
    try:
        t_date = datetime.strptime(booking.travel_date, "%Y-%m-%d").date()
        end_date = t_date + timedelta(days=booking.trip_days)
        booking.end_date = end_date.strftime("%Y-%m-%d")
        
        # Security logic: Is the ticket active, upcoming, or expired?
        if booking.payment_status == "Archived" or today > end_date:
            booking.validity_status = "Expired"
            booking.days_metric = "Trip Concluded (Expired)"
        elif today < t_date:
            booking.validity_status = "Upcoming"
            days_left = (t_date - today).days
            booking.days_metric = "Starts Tomorrow" if days_left == 1 else f"{days_left} Days to Start"
        else:
            booking.validity_status = "Active"
            booking.days_metric = "Ongoing Trip"
            
    except:
        booking.end_date = "N/A"
        booking.validity_status = "Unknown"
        booking.days_metric = "--"
        
    return render_template("ticket_verify.html", request=request, booking=booking)


@bookings_bp.route("/portal")
def traveler_portal():
    # Fetch query parameter in Flask
    phone = request.args.get("phone")
    bookings = []
    searched = False
    
    if phone:
        searched = True
        db = SessionLocal()
        bookings = db.query(Booking).filter(Booking.phone == phone).order_by(Booking.id.desc()).all()
        db.close()
        
        today = datetime.now().date()
        for b in bookings:
            b.parsed_travelers = json.loads(b.travelers_details) if getattr(b, 'travelers_details', None) else []
            
            try:
                t_date = datetime.strptime(b.travel_date, "%Y-%m-%d").date()
                end_date = t_date + timedelta(days=b.trip_days)
                b.end_date = end_date.strftime("%Y-%m-%d")
                
                if today < t_date:
                    b.trip_status = "Upcoming"
                    days_left = (t_date - today).days
                    b.days_metric = "Starts Tomorrow" if days_left == 1 else f"{days_left} Days to Start"
                elif t_date <= today <= end_date:
                    b.trip_status = "Active"
                    rem = (end_date - today).days
                    b.days_metric = f"{rem} Days Remaining" if rem > 0 else "Ends Today"
                else:
                    b.trip_status = "Completed"
                    b.days_metric = "Trip Concluded (Expired)"
            except Exception:
                b.trip_status = "Unknown"
                b.days_metric = "--"
                b.end_date = "N/A"
        
    return render_template("traveler_portal.html", request=request, phone=phone, bookings=bookings, searched=searched)

# --- NEW REVIEW ROUTES ---

@bookings_bp.route("/leave-review/<booking_ref>")
def leave_review_page(booking_ref):
    """Renders the 5-star rating form for the traveler."""
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.booking_ref == booking_ref).first()
    # Check if they already reviewed
    existing_review = db.query(Review).filter(Review.booking_ref == booking_ref).first()
    db.close()
    
    if not booking or existing_review:
        return redirect('/explorer') 
        
    return render_template("review_form.html", request=request, booking=booking)

@bookings_bp.route("/submit-review", methods=["POST"])
def submit_review():
    """Saves the submitted review to the database."""
    booking_ref = request.form.get("booking_ref")
    site_id = request.form.get("site_id")
    traveler_name = request.form.get("traveler_name")
    rating = int(request.form.get("rating", 5))
    comment = request.form.get("comment")
    
    db = SessionLocal()
    try:
        new_review = Review(
            booking_ref=booking_ref, site_id=site_id,
            traveler_name=traveler_name, rating=rating,
            comment=comment, timestamp=datetime.now().strftime("%Y-%m-%d")
        )
        db.add(new_review)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Review Save Error: {e}")
    finally:
        db.close()
        
    return redirect('/explorer')