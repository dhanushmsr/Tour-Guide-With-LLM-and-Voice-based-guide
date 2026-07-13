import os
import uuid
import asyncio
import edge_tts
import logging
import threading
from flask import Blueprint, request, jsonify

from app.services.ai_engine import ai_guide

# Configure Logging for Production Monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InkwakeOracle")

# Replace APIRouter with Flask Blueprint
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

# Directory configuration for ephemeral audio files
AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)


# 2. Oracle AI Endpoint
@chatbot_bp.route("/ask", methods=["POST"])
def ask_oracle():
    """
    Main dialogue entry point. 
    Syncs with the AI Engine for RAG-grounded historical answers.
    """
    # Extract JSON payload (Replacing FastAPI's Pydantic BaseModel)
    data = request.get_json() or {}
    query = data.get("query")
    lang = data.get("lang", "en")
    username = data.get("username", "Explorer")
    site_id = data.get("site_id")
    
    try:
        # Pass the request to the AI Engine (Gemini Node)
        response_text = ai_guide.get_answer(
            user_query=query, 
            site_id=site_id, 
            lang=lang,
            username=username
        )
        
        return jsonify({
            "status": "success", 
            "response": response_text
        })
    
    except Exception as e:
        logger.error(f"❌ Oracle Sync Failure: {str(e)}")
        # Immersion-safe error message
        return jsonify({
            "status": "error", 
            "response": f"Vanakkam {username}. The digital scrolls are temporarily out of sync. Please re-identify yourself or refresh the link."
        })

# 3. Neural Voice Engine (Voice Guide)
@chatbot_bp.route("/voice-guide", methods=["GET"])
def voice_guide():
    """
    Converts Oracle responses into high-fidelity Dravidian Neural Voices.
    Optimized for ta-IN-Pallavi (Tamil) and en-IN-Neerja (English).
    """
    # Extract query parameters in Flask
    text = request.args.get("text")
    lang = request.args.get("lang", "en")
    
    if not text:
        return jsonify({"error": "Text payload missing"}), 400

    try:
        # Voice Selection Logic
        voice = "ta-IN-PallaviNeural" if lang == "ta" else "en-IN-NeerjaNeural"
        
        # Text Sanitization: Remove newlines, Markdown asterisks, and hidden characters
        clean_text = " ".join(text.replace("*", "").replace("#", "").split())
        if not clean_text or len(clean_text) < 2:
            return jsonify({"error": "Text payload empty or invalid for audio synthesis"}), 400

        # Generate unique hash-based filename to prevent disk collisions
        filename = f"oracle_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Asynchronous wrapper for Edge-TTS to run on a synchronous Flask server
        async def generate_audio():
            communicate = edge_tts.Communicate(clean_text, voice)
            await communicate.save(filepath)

        # Execute Edge-TTS Communication safely via asyncio.run
        try:
            asyncio.run(generate_audio())
        except Exception as tts_err:
            logger.error(f"❌ TTS Engine Error: {tts_err}")
            return jsonify({"error": "Voice Node Offline", "details": str(tts_err)})

        # Verify Disk Write
        if os.path.exists(filepath):
            return jsonify({"audio_url": f"/static/audio/{filename}"})
        else:
            raise Exception("IO Failure: Audio not written to static disk.")

    except Exception as e:
        logger.error(f"❌ General Voice Route Failure: {e}")
        return jsonify({"error": "Failed to initiate voice tour", "details": str(e)})

# 4. Storage Maintenance (EC2 / Cloud Optimization)
@chatbot_bp.route("/clear-audio-cache", methods=["DELETE"])
def clear_audio_cache():
    """
    Admin-only cleanup route. Uses Python Threading to prevent 
    blocking the main thread during high-file count deletions.
    """
    def purge_files():
        purged = 0
        try:
            if os.path.exists(AUDIO_DIR):
                for f in os.listdir(AUDIO_DIR):
                    if f.endswith(".mp3"):
                        os.remove(os.path.join(AUDIO_DIR, f))
                        purged += 1
            logger.info(f"🧹 Storage Maintenance: Purged {purged} audio logs.")
        except Exception as e:
            logger.error(f"⚠️ Maintenance Error: {e}")

    # Launch cleanup in background
    threading.Thread(target=purge_files).start()
    return jsonify({"status": "Maintenance started", "target": AUDIO_DIR})