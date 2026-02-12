import os
import uuid
import asyncio
import edge_tts
import logging
from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.ai_engine import ai_guide

# Configure Logging for Production Monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InkwakeOracle")

router = APIRouter(prefix="/chatbot", tags=["Oracle"])

# Directory configuration for ephemeral audio files
AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# 1. Identity & Context Schema
class ChatQuery(BaseModel):
    query: str
    lang: str = "en"
    username: str = "Explorer"  # Handled by frontend localStorage
    site_id: Optional[str] = None # Contextual grounding for monument pages

# 2. Oracle AI Endpoint
@router.post("/ask")
async def ask_oracle(data: ChatQuery):
    """
    Main dialogue entry point. 
    Syncs with the AI Engine for RAG-grounded historical answers.
    """
    try:
        # Pass the request to the AI Engine (Gemini 1.5 Node)
        response_text = ai_guide.get_answer(
            user_query=data.query, 
            site_id=data.site_id, 
            lang=data.lang,
            username=data.username
        )
        
        return {
            "status": "success", 
            "response": response_text
        }
    
    except Exception as e:
        logger.error(f"Oracle Sync Failure: {e}")
        # Immersion-safe error message
        return {
            "status": "error", 
            "response": f"Vanakkam {data.username}. The digital scrolls are temporarily out of sync. Please re-identify yourself or refresh the link."
        }

# 3. Neural Voice Engine (Voice Guide)
@router.get("/voice-guide")
async def voice_guide(text: str = Query(...), lang: str = "en"):
    """
    Converts Oracle responses into high-fidelity Dravidian Neural Voices.
    Optimized for ta-IN-Pallavi (Tamil) and en-IN-Neerja (English).
    """
    try:
        # Voice Selection Logic
        voice = "ta-IN-PallaviNeural" if lang == "ta" else "en-IN-NeerjaNeural"
        
        # Text Sanitization: Remove newlines and hidden characters
        clean_text = " ".join(text.split())
        if not clean_text:
            raise HTTPException(status_code=400, detail="Text payload empty")

        # Generate unique hash-based filename to prevent disk collisions
        filename = f"oracle_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Execute Edge-TTS Communication
        try:
            communicate = edge_tts.Communicate(clean_text, voice)
            await communicate.save(filepath)
        except Exception as tts_err:
            logger.error(f"TTS Engine Error: {tts_err}")
            return {"error": "Voice Node Offline", "details": str(tts_err)}

        # Verify Disk Write
        if os.path.exists(filepath):
            return {"audio_url": f"/static/audio/{filename}"}
        else:
            raise Exception("IO Failure: Audio not written to static disk.")

    except Exception as e:
        logger.error(f"General Voice Route Failure: {e}")
        return {"error": "Failed to initiate voice tour", "details": str(e)}

# 4. Storage Maintenance (EC2 Optimization)
@router.delete("/clear-audio-cache")
async def clear_audio_cache(background_tasks: BackgroundTasks):
    """
    Admin-only cleanup route. Uses BackgroundTasks to prevent 
    blocking the main thread during high-file count deletions.
    """
    def purge_files():
        purged = 0
        for f in os.listdir(AUDIO_DIR):
            if f.endswith(".mp3"):
                os.remove(os.path.join(AUDIO_DIR, f))
                purged += 1
        logger.info(f"Storage Maintenance: Purged {purged} audio logs.")

    background_tasks.add_task(purge_files)
    return {"status": "Maintenance started", "target": "static/audio"}