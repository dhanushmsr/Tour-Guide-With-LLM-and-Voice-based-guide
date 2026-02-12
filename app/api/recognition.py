import json
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.vision_engine import identify_landmark

# 1. Initialize the router with protocol-specific tags
router = APIRouter(prefix="/recognition", tags=["Recognition"])

# Path to ensure the site actually exists in the database after being identified by CV
DATA_PATH = "app/data/sites_info.json"

@router.post("/scan")
async def scan_monument(file: UploadFile = File(...)):
    """
    Receives an image from the mobile/web scanner, processes it through 
    the OpenCV Vision Engine, and returns a verified Site ID.
    """
    try:
        # 1. Read binary image data
        contents = await file.read()
        
        # 2. Invoke OpenCV ORB/FLANN Feature Matching
        site_id = identify_landmark(contents)
        
        if not site_id:
            return {
                "status": "error", 
                "message": "Landmark not recognized. Please adjust your angle or lighting."
            }

        # 3. Cross-reference with JSON Database to ensure site data exists
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                sites = json.load(f)
                site_exists = any(s.get("id") == site_id for s in sites)
                
                if not site_exists:
                    return {
                        "status": "partial_match",
                        "message": f"Landmark identified as {site_id}, but the digital scroll is not yet published.",
                        "site_id": site_id
                    }

        # 4. Successful Identification
        return {
            "status": "success", 
            "site_id": site_id,
            "verification": "Geometric Match Confirmed"
        }

    except Exception as e:
        print(f"Vision Protocol Error: {e}")
        return {"status": "error", "message": "System failure during image processing."}

@router.get("/status")
async def get_scanner_status():
    """Returns the health of the Computer Vision node."""
    reference_count = 0
    ref_dir = "static/reference_monuments/"
    
    if os.path.exists(ref_dir):
        reference_count = len([f for f in os.listdir(ref_dir) if f.endswith(('.jpg', '.png'))])
        
    return {
        "node": "Inkwake Vision v2.5",
        "reference_library_size": reference_count,
        "active": True
    }