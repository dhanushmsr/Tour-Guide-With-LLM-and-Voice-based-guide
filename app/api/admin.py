import os
import json
import csv
import io
import shutil
import time
from fastapi import APIRouter, Request, Form, Depends, HTTPException, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response

# Import custom database functions for Enquiry Vault
from app.database import get_all_enquiries

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")

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
async def get_current_user(request: Request):
    """Verifies the transient session cookie."""
    user_session = request.cookies.get("admin_session")
    if user_session != "authenticated":
        raise HTTPException(status_code=401)
    return True

# --- Authentication ---
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@router.post("/login")
async def login(response: Response, password: str = Form(...)):
    if password == ADMIN_PWD:
        response = RedirectResponse(url="/admin/dashboard", status_code=303)
        response.set_cookie(key="admin_session", value="authenticated", httponly=True, samesite="lax")
        return response
    return RedirectResponse(url="/admin/login?error=InvalidPassword", status_code=303)

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login")
    response.delete_cookie("admin_session")
    return response

# --- Dashboard & Management ---
@router.get("/dashboard")
async def admin_dashboard(request: Request):
    try:
        await get_current_user(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login")
        
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
                
    return templates.TemplateResponse("admin_panel.html", {
        "request": request, 
        "sites": sites, 
        "registered_users": registered_users,
        "enquiries": enquiries
    })

# --- Identity Vault Actions ---

@router.post("/log-user")
async def log_user(name: str = Form(...), email: str = Form(...), phone: str = Form(...)):
    """Bridge for the frontend registry to record traveler contact data."""
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
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/delete-user/{username}")
async def delete_user(request: Request, username: str):
    await get_current_user(request)
    if os.path.exists(USER_PATH):
        with open(USER_PATH, "r", encoding="utf-8") as f:
            users = json.load(f)
        users = [u for u in users if u.get("name") != username]
        with open(USER_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.post("/clear-all-users")
async def clear_all_users(request: Request):
    await get_current_user(request)
    with open(USER_PATH, "w", encoding="utf-8") as f:
        json.dump([], f)
    return RedirectResponse(url="/admin/dashboard", status_code=303)

# --- Heritage Vault Actions (CRUD) ---

@router.get("/add", response_class=HTMLResponse)
async def add_site_page(request: Request):
    await get_current_user(request)
    return templates.TemplateResponse("admin_add_site.html", {"request": request, "edit_mode": False})

@router.get("/edit/{site_id}", response_class=HTMLResponse)
async def edit_site_page(request: Request, site_id: str):
    await get_current_user(request)
    site_to_edit = None
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            sites = json.load(f)
            site_to_edit = next((s for s in sites if s.get("id") == site_id), None)
    
    if not site_to_edit:
        return RedirectResponse(url="/admin/dashboard?error=NotFound")

    return templates.TemplateResponse("admin_add_site.html", {
        "request": request, 
        "site": site_to_edit, 
        "edit_mode": True
    })

@router.post("/add-site")
async def add_site(
    request: Request,
    name: str = Form(...), category: str = Form(...), district: str = Form(...),
    history_text: str = Form(...), culture: str = Form(...),
    lat: float = Form(...), lng: float = Form(...),
    video_url: str = Form(""), gallery_urls: str = Form(""),
    image_url: str = Form(None), image_file: UploadFile = File(None)
):
    await get_current_user(request)
    
    final_image_path = image_url
    if image_file and image_file.filename:
        ext = os.path.splitext(image_file.filename)[1]
        local_filename = f"{name.lower().replace(' ', '_')}{ext}"
        filepath = os.path.join(UPLOAD_DIR, local_filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        final_image_path = f"/static/images/{local_filename}"

    sites = []
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            try: sites = json.load(f)
            except: sites = []
    
    sites.append({
        "id": name.lower().replace(" ", "-"), "name": name, "category": category,
        "district": district, "image_url": final_image_path,
        "gallery": [u.strip() for u in gallery_urls.split(",") if u.strip()],
        "video_url": video_url, "history_text": history_text, "culture": culture,
        "coordinates": {"lat": lat, "lng": lng}
    })
    
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(sites, f, indent=4)
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.post("/update-site/{old_id}")
async def update_site(
    request: Request, old_id: str,
    name: str = Form(...), category: str = Form(...), district: str = Form(...),
    history_text: str = Form(...), culture: str = Form(...),
    lat: float = Form(...), lng: float = Form(...),
    video_url: str = Form(""), gallery_urls: str = Form(""),
    image_url: str = Form(None), image_file: UploadFile = File(None)
):
    await get_current_user(request)
    
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            sites = json.load(f)
        
        for s in sites:
            if s["id"] == old_id:
                if image_file and image_file.filename:
                    ext = os.path.splitext(image_file.filename)[1]
                    local_filename = f"{name.lower().replace(' ', '_')}{ext}"
                    filepath = os.path.join(UPLOAD_DIR, local_filename)
                    with open(filepath, "wb") as buffer:
                        shutil.copyfileobj(image_file.file, buffer)
                    s["image_url"] = f"/static/images/{local_filename}"
                elif image_url:
                    s["image_url"] = image_url

                s.update({
                    "name": name, "category": category, "district": district,
                    "history_text": history_text, "culture": culture,
                    "video_url": video_url,
                    "gallery": [u.strip() for u in gallery_urls.split(",") if u.strip()],
                    "coordinates": {"lat": lat, "lng": lng}
                })
        
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(sites, f, indent=4)
            
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.post("/delete/{site_id}")
async def delete_site(request: Request, site_id: str):
    await get_current_user(request)
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            sites = json.load(f)
        sites = [s for s in sites if s.get("id") != site_id]
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(sites, f, indent=4)
    return RedirectResponse(url="/admin/dashboard", status_code=303)