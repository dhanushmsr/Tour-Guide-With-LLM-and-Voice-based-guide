import os
import json
import uvicorn
import threading
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# 1. Import Inkwake Module Suite
from app.api import chatbot, recognition, explorer, admin
from app.database import log_security_event, save_enquiry

# --- Modern Lifespan Handler (Replaces @app.on_event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the Heritage Node.
    Ensures directory structure and JSON vaults exist before the server starts.
    """
    directories = [
        "static/audio", 
        "static/images", 
        "static/reference_monuments", 
        "app/data"
    ]
    for folder in directories:
        os.makedirs(folder, exist_ok=True)
    
    # Initialize JSON DB files if missing
    db_files = {
        "app/data/sites_info.json": [],
        "app/data/users_info.json": []
    }
    for path, default_val in db_files.items():
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default_val, f)
    
    print("🚀 Inkwake Heritage Node [v2.6] Online & Secured")
    yield
    # Shutdown logic can go here if needed

app = FastAPI(
    title="Inkwake Heritage Guide",
    description="AI-Powered Cultural Discovery Platform for Tamil Nadu Heritage",
    version="2.6.0",
    lifespan=lifespan
)

# 2. Asset Configuration & Static Mounting
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Storage Cleanup Engine ---
def cleanup_temp_files():
    """
    Background Task: Automatically purges neural audio cache older than 24 hours.
    Crucial for AWS EC2 instances with limited storage.
    """
    while True:
        try:
            audio_dir = "static/audio"
            if os.path.exists(audio_dir):
                now = time.time()
                for f in os.listdir(audio_dir):
                    file_path = os.path.join(audio_dir, f)
                    # If file is older than 1 day
                    if os.path.getmtime(file_path) < now - 86400:
                        os.remove(file_path)
        except Exception as e:
            print(f"Cleanup Thread Error: {e}")
        time.sleep(3600)  # Runs every hour

# Initialize Cleanup Thread as a background daemon
threading.Thread(target=cleanup_temp_files, daemon=True).start()

# --- Security & Traffic Middleware ---
@app.middleware("http")
async def monitor_activity(request: Request, call_next):
    """Logs sensitive node access (Admin/Recognition) to the SQLite security vault."""
    client_ip = request.client.host
    path = request.url.path
    
    if path.startswith("/admin") or path.startswith("/recognition"):
        log_security_event(client_ip, f"ACCESS_TRIGGER: {request.method} {path}")
        
    return await call_next(request)

# --- Router Integration ---
app.include_router(explorer.router)
app.include_router(chatbot.router)
app.include_router(recognition.router)
app.include_router(admin.router)

# --- Core Application Routes ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/chatbot-ui", response_class=HTMLResponse)
async def oracle_interface(request: Request):
    return templates.TemplateResponse("chatbot_page.html", {"request": request})

@app.get("/enquiry", response_class=HTMLResponse)
async def enquiry_page(request: Request):
    return templates.TemplateResponse("enquiry_page.html", {"request": request})

@app.post("/submit-enquiry")
async def handle_enquiry(
    name: str = Form(...), 
    email: str = Form(...), 
    subject: str = Form(...), 
    message: str = Form(...)
):
    """
    Handles POST data from the Enquiry Page. 
    Returns JSON for the new AJAX frontend to handle success states without reloading.
    """
    success = save_enquiry(name, email, subject, message)
    if success:
        return JSONResponse(content={"status": "success", "message": "Enquiry Archived in Vault"})
    
    return JSONResponse(
        status_code=500, 
        content={"status": "error", "message": "Vault Persistence Failure"}
    )

@app.get("/site/{site_id}", response_class=HTMLResponse)
async def monument_details(request: Request, site_id: str):
    json_path = "app/data/sites_info.json"
    site_data = None
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            sites = json.load(f)
            site_data = next((s for s in sites if s.get("id") == site_id), None)
    
    if not site_data:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        
    return templates.TemplateResponse("site_detail.html", {"request": request, "site": site_data})

# --- Custom 404 Sentinel ---
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

# --- Server Launch ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)