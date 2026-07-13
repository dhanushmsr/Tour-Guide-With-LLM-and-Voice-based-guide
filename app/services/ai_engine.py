import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables once
load_dotenv()

class HeritageAIEngine:
    def __init__(self):
        """
        Initializes the native Google GenAI engine with production configurations,
        automatic retry resilience, and local data grounding for the Inkwake platform.
        """
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.data_path = "app/data/sites_info.json"
        
        # Primary: Latest high-speed Flash model
        self.primary_model = "gemini-2.5-flash" 
        # Fallback: Stable Flash variant with generous free-tier quotas (prevents limit: 0 errors)
        self.fallback_model = "gemini-1.5-flash"
        
        if not self.api_key:
            print("❌ CRITICAL ERROR: GOOGLE_API_KEY not found in environment!")
        else:
            print(f"Inkwake Oracle Node: API Key detected (ends in ...{self.api_key[-4:]})")

        # Initialize the official native Google client
        self.client = self._init_client()
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)

    def _init_client(self):
        """Helper to initialize the native GenAI client cleanly."""
        if not self.api_key:
            return None
        try:
            return genai.Client(api_key=self.api_key)
        except Exception as e:
            print(f"❌ Failed to initialize Google GenAI Client: {e}")
            return None

    def _get_context(self, site_id=None):
        """ Retrieves historical facts from local JSON for RAG grounding. """
        try:
            if not os.path.exists(self.data_path):
                return "General knowledge of Chola, Pandya, Pallava, and Nayak dynasties."

            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if site_id:
                site = next((s for s in data if str(s.get("id")) == str(site_id)), None)
                if site:
                    return (f"Monument: {site.get('name', 'Unknown')}. District: {site.get('district', 'Unknown')}. "
                            f"History: {site.get('history_text', 'No history recorded.')}. "
                            f"Culture: {site.get('culture', '')}")
            
            all_names = [s.get("name") for s in data if s.get("name")]
            return f"The Inkwake vault contains records for: {', '.join(all_names)}."
            
        except Exception as e:
            print(f"⚠️ RAG Context Error: {e}")
            return "Expertise in Tamil Nadu Heritage and Dravidian architecture."

    def get_answer(self, user_query, site_id=None, lang="en", username="Explorer"):
        """
        Generates a factual response using the native SDK with automatic retry and failover logic.
        """
        if not self.client:
            return "Oracle Offline: API Key missing. Please configure GOOGLE_API_KEY in your .env file."

        context = self._get_context(site_id)
        lang_instruction = "Tamil (தமிழ்)" if lang == "ta" else "English"
        
        system_instruction = f"""
Role: You are the 'Namma AI ', a scholarly but welcoming guardian of Tamil Nadu history.
User Identity: You are speaking with {username}.
Grounding Context: {context}
Language: Your response MUST be entirely in {lang_instruction}.

Protocols:
1. Personalized Greeting: Begin your response with 'Vanakkam {username},' (or Tamil equivalent if language is Tamil).
2. Factual Integrity: Use architectural terms like 'Vimana', 'Mandapam', 'Gopuram', and 'Dravidian'. Ground your answer strictly in the provided context when available.
3. Continuity: Politely refocus the user on Tamil heritage if they drift off-topic.
4. Efficiency & Format: Limit your response to 2-3 concise, highly readable paragraphs. Avoid excessive markdown bolding or asterisks so text-to-speech engines read it smoothly.
"""

        # Native SDK configuration with safety settings
        config = types.GenerateContentConfig(
            system_instruction=system_instruction.strip(),
            temperature=0.3,
            max_output_tokens=1024,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
            ]
        )

        # 1. Primary Model Attempt with Exponential Backoff Retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.primary_model,
                    contents=user_query.strip(),
                    config=config
                )
                return response.text
                
            except Exception as e:
                error_str = str(e)
                # If Google throws a temporary 503 overload or 429 rate spike, wait and retry
                if "503" in error_str or "429" in error_str or "UNAVAILABLE" in error_str:
                    wait_time = 2 ** attempt  # Waits 1s, then 2s, then 4s
                    print(f"⚠️ Server busy ({self.primary_model}). Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    # If it is a different syntax or permission error, exit loop immediately
                    print(f"❌ Unrecoverable error on {self.primary_model}: {e}")
                    break

        # 2. Failover Attempt: Switch to Backup Model if all Primary retries fail
        print(f"🔄 All retries exhausted. Failover: Initializing {self.fallback_model}...")
        try:
            response = self.client.models.generate_content(
                model=self.fallback_model,
                contents=user_query.strip(),
                config=config
            )
            return response.text
        except Exception as fe:
            print(f"❌ Critical Oracle Failure: {fe}")
            return (f"Vanakkam {username}. My neural connection to the archives is temporarily disrupted by heavy network traffic. "
                    "Please verify your system network or try again in a few moments.")

# Global Singleton
ai_guide = HeritageAIEngine()