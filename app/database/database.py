import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, desc, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# --- NEW: Absolute Path Definition for cPanel ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Fetch the database URL from Environment Variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix Render's "postgres://" prefix for SQLAlchemy compatibility (if you ever use Postgres)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Local Development Fallback: If no cloud DB is provided, use local SQLite
if not DATABASE_URL:
    sqlite_path = os.path.join(BASE_DIR, "app", "data", "security.db")
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    # SQLite requires check_same_thread=False for web frameworks (like Flask)
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # MySQL Engine
    engine = create_engine(DATABASE_URL)

# 2. Database Engine & Session Configuration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Declarative Database Vault Schemas ---
class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_ref = Column(String(20), unique=True, nullable=False)
    site_id = Column(String(100), nullable=False)
    site_name = Column(String(100), nullable=False)
    traveler_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)
    travel_date = Column(String(50), nullable=False)
    trip_days = Column(Integer, default=1, nullable=False) # Tracks duration
    travelers_count = Column(Integer, nullable=False)
    travelers_details = Column(Text, nullable=True) # Stores JSON of all passengers
    total_amount = Column(Integer, nullable=False)
    payment_status = Column(String(50), default='Pending', nullable=False)
    timestamp = Column(String(50), nullable=False)

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False) # e.g., SUMMER20
    discount_percentage = Column(Integer, nullable=False)  # e.g., 20 (for 20%)
    is_active = Column(Boolean, default=True)

class Location(Base):
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)  # e.g., Kerala, Tamil Nadu, Karnataka
    description = Column(Text, nullable=False)
    highlights = Column(Text, nullable=False)      # Comma-separated or JSON list of key spots
    best_time_to_visit = Column(String(100))

class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_ref = Column(String(50), unique=True, nullable=False)
    site_id = Column(String(100), nullable=False)
    traveler_name = Column(String(100), nullable=False)
    rating = Column(Integer, nullable=False) # 1 to 5 stars
    comment = Column(Text, nullable=True)
    timestamp = Column(String(50))

class Package(Base):
    __tablename__ = 'packages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    duration_days = Column(Integer, nullable=False)
    price_usd = Column(Integer, nullable=False)   # Target pricing for US clients
    description = Column(Text, nullable=False)
    itinerary_summary = Column(Text, nullable=False) # Overview of day-by-day plan

class SecurityLog(Base):
    __tablename__ = 'security_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(50), nullable=False)
    action = Column(Text, nullable=False)
    timestamp = Column(String(50), nullable=False)

class RegisteredUser(Base):
    __tablename__ = 'registered_users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    timestamp = Column(String(50), nullable=False)

class Enquiry(Base):
    __tablename__ = 'enquiries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(50), default='Unread', nullable=False)
    timestamp = Column(String(50), nullable=False)


# --- Core Database Bridge Operations ---

def init_db():
    """Initializes the database and maps all table structures automatically."""
    # Ensure local directory exists if falling back to local SQLite
    if "sqlite" in DATABASE_URL:
        os.makedirs(os.path.join(BASE_DIR, "app", "data"), exist_ok=True)
        
    # metadata.create_all safely creates tables only if they do not exist
    Base.metadata.create_all(bind=engine)

def log_security_event(ip_address, action):
    """Bridge for main.py to record security protocols inside the cloud database."""
    db = SessionLocal()
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = SecurityLog(ip=ip_address, action=action, timestamp=timestamp)
        db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Security Archive Error: {e}")
    finally:
        db.close()

def save_enquiry(name, email, subject, message):
    """Bridge for the Curator Enquiry route to securely persist traveler messages."""
    db = SessionLocal()
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        enquiry_entry = Enquiry(
            name=name,
            email=email,
            subject=subject,
            message=message,
            timestamp=timestamp
        )
        db.add(enquiry_entry)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"⚠️ Lead Vault Error: {e}")
        return False
    finally:
        db.close()

def get_all_enquiries():
    """Fetches enquiries formatted as dictionaries for the Admin Dashboard Interface."""
    db = SessionLocal()
    try:
        rows = db.query(Enquiry).order_by(desc(Enquiry.timestamp)).all()
        # Converts records back into dictionaries to keep exact syntax match with your Jinja2 templates
        return [
            {
                "id": r.id,
                "name": r.name,
                "email": r.email,
                "subject": r.subject,
                "message": r.message,
                "status": r.status,
                "timestamp": r.timestamp
            } for r in rows
        ]
    except Exception as e:
        print(f"⚠️ Query Error: {e}")
        return []
    finally:
        db.close()

def delete_enquiry(enquiry_id: int):
    """Resolves and removes a specific single enquiry from the database."""
    db = SessionLocal()
    try:
        # Now it searches by the unique ID, so it will ONLY ever delete one row!
        db.query(Enquiry).filter(Enquiry.id == enquiry_id).delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Delete Error: {e}")
    finally:
        db.close()

# Removed the standalone init_db() call here.
# It is now safely triggered ONLY by the main.py initialization
# after environment variables are securely loaded.