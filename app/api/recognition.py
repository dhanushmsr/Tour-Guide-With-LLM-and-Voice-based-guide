import os
import json
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.vision_engine import identify_landmark

# 1. Initialize the router with protocol-specific tags
router = APIRouter(prefix="/recognition", tags=["Recognition"])

# Path to ensure the site actually exists in the database after being identified by CV
DATA_PATH = "app/data/sites_info.json"

@router.post("/scan")
def scan_monument(file: UploadFile = File(...)):
    """
    Receives an image from the mobile/web scanner, processes it through 
    the OpenCV Vision Engine, and returns a verified Site ID.
    
    NOTE: This endpoint is defined as standard 'def' (instead of 'async def') 
    so FastAPI automatically runs the synchronous, CPU-heavy OpenCV ORB/FLANN 
    matching inside a dedicated background threadpool without freezing the server.
    """
    try:
        # 1. Read binary image data from the uploaded file
        contents = file.file.read()
        
        if not contents:
            return {
                "status": "error",
                "message": "Empty image file received. Please try scanning again."
            }
        
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
                site_exists = any(str(s.get("id")) == str(site_id) for s in sites)
                
                if not site_exists:
                    return {
                        "status": "partial_match",
                        "message": f"Landmark identified as '{site_id}', but the digital scroll is not yet published.",
                        "site_id": site_id
                    }
        else:
            print(f"⚠️ Warning: Digital archive not found at {DATA_PATH}")

        # 4. Successful Identification
        return {
            "status": "success", 
            "site_id": site_id,
            "verification": "Geometric Match Confirmed"
        }

    except Exception as e:
        print(f"❌ Vision Protocol Error: {str(e)}")
        traceback.print_exc()
        return {
            "status": "error", 
            "message": "System failure during image processing."
        }
    finally:
        # Ensure file handle is closed cleanly
        file.file.close()

@router.get("/status")
def get_scanner_status():
    """Returns the health and reference library metrics of the Computer Vision node."""
    reference_count = 0
    ref_dir = "static/reference_monuments/"
    
    try:
        if os.path.exists(ref_dir):
            reference_count = len([
                f for f in os.listdir(ref_dir) 
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
            ])
    except Exception as e:
        print(f"⚠️ Error reading reference directory: {e}")
        
    return {
        "node": "Inkwake Vision v2.5",
        "reference_library_size": reference_count,
        "engine": "OpenCV ORB / FLANN",
        "active": True
    }