import sqlite3
import os
from datetime import datetime

DB_PATH = 'app/data/security.db'

def init_db():
    """Initializes the database schema for Security and Enquiries."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 1. Security Logs Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # 2. Curator Enquiries Table (Lead Vault)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'Unread',
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()

def log_security_event(ip_address, action):
    """Records unauthorized access attempts or sensitive protocol triggers."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO security_logs (ip, action, timestamp) VALUES (?, ?, ?)",
                (ip_address, action, timestamp)
            )
            conn.commit()
    except Exception as e:
        print(f"⚠️ Security Logging Error: {e}")

def save_enquiry(name, email, subject, message):
    """Stores traveler enquiries from the Enquiry Page into the database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO enquiries (name, email, subject, message, timestamp) VALUES (?, ?, ?, ?, ?)",
                (name, email, subject, message, timestamp)
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"⚠️ Enquiry Storage Error: {e}")
        return False

def get_all_enquiries():
    """Fetches all records for the Admin Dashboard Enquiry Vault."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row # Returns rows as dictionaries
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM enquiries ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []

# Run initialization on module load
init_db()