import sqlite3
import os
from datetime import datetime

DB_PATH = 'app/data/security.db'

def init_db():
    """Initializes the SQLite database and creates the necessary heritage vaults."""
    # Ensure the data directory exists for AWS/Local environments
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 1. Security Archive: For monitoring unauthorized access or sensitive triggers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # 2. Identity Vault: For tracking registered travelers from the registry page
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registered_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # 3. Lead Vault: For storing curator enquiries (from the Enquiry Page)
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
    """Bridge for main.py to record security protocols."""
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
        print(f"⚠️ Security Archive Error: {e}")

def save_enquiry(name, email, subject, message):
    """Bridge for the Curator Enquiry route to store traveler messages."""
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
        print(f"⚠️ Lead Vault Error: {e}")
        return False

def get_all_enquiries():
    """Fetches enquiries for the Admin Dashboard Command Center."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # Enables dictionary-style access in Jinja2
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM enquiries ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []

# Trigger vault initialization on module load
init_db()