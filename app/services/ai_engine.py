import os
import json
from dotenv import load_dotenv
# Ensure you are only importing what is needed
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()
# Force reload of .env to ensure the new API Key is captured
load_dotenv()

class HeritageAIEngine:
    def __init__(self):
        """
        Initializes the Gemini engine with optimized 2026 model configurations
        and local data grounding for the Inkwake platform.
        """
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.data_path = "app/data/sites_info.json"
        
        # Deployment Strategy: 
        # Flash for speed/cost. Pro for complex historical failover.
        self.primary_model = "gemini-2.5-flash" 
        self.fallback_model = "gemini-3-pro-preview"
        
        # Validate API Key existence on startup
        if not self.api_key:
            print("❌ CRITICAL ERROR: GOOGLE_API_KEY not found in .env file.")
        else:
            print(f"✅ Inkwake Oracle Node: API Key detected (ends in ...{self.api_key[-4:]})")

        self.llm = self._init_llm(self.primary_model)
        
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)

    def _init_llm(self, model_name):
        """Helper to initialize the LLM object with production safety settings."""
        if not self.api_key:
            # Return a dummy object or handle gracefully to prevent crash on init
            return None

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.api_key,
            temperature=0.3,
            max_output_tokens=1024,
            # Safety settings tuned for scholarly historical context
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_ONLY_HIGH",
            }
        )

    def _get_context(self, site_id=None):
        """ Retrieves historical facts from local JSON for RAG grounding. """
        try:
            if not os.path.exists(self.data_path):
                return "General knowledge of Chola, Pandya, and Pallava dynasties."

            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if site_id:
                # Find specific monument facts
                site = next((s for s in data if s.get("id") == site_id), None)
                if site:
                    return (f"Monument: {site['name']}. District: {site['district']}. "
                            f"History: {site['history_text']}. Culture: {site.get('culture', '')}")
            
            # Global context summary
            all_names = [s.get("name") for s in data]
            return f"The Inkwake vault contains records for: {', '.join(all_names)}."
            
        except Exception as e:
            print(f"⚠️ RAG Context Error: {e}")
            return "Expertise in Tamil Nadu Heritage and Dravidian architecture."

    def get_answer(self, user_query, site_id=None, lang="en", username="Explorer"):
        """
        Generates a factual response with failover logic.
        """
        # If API key was missing during init
        if not self.llm:
            return "Error: API Key missing. Please configure your .env file."

        context = self._get_context(site_id)
        lang_instruction = "Tamil (தமிழ்)" if lang == "ta" else "English"
        
        system_instruction = f"""
        Role: You are the 'Inkwake AI Oracle', a scholarly but welcoming guardian of Tamil history.
        User Identity: You are speaking with {username}.
        Grounding Context: {context}
        Language: Response MUST be entirely in {lang_instruction}.
        
        Protocols:
        1. Personalized Vanakkam: Begin your response with 'Vanakkam {username}'.
        2. Factual Integrity: Use terms like 'Vimana', 'Mandapam', and 'Dravidian'.
        3. Continuity: Politely refocus the user on heritage if they drift off-topic.
        4. Efficiency: Limit response to 3 precise paragraphs.
        """

        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=user_query)
        ]

        try:
            # Attempt 1: Flash Model
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            # This print will show the specific API error in your terminal
            print(f"❌ Primary Model Error: {e}")
            
            # Attempt 2: Failover to Pro Model
            try:
                print(f"🔄 Failover: Initializing {self.fallback_model}...")
                fallback_llm = self._init_llm(self.fallback_model)
                response = fallback_llm.invoke(messages)
                return response.content
            except Exception as fe:
                print(f"❌ Critical System Failure: {fe}")
                # We return the actual error string to the UI for your debugging
                return (f"Oracle Error: {str(fe)}. "
                        "Please verify your API Key and internet connection.")

# Global Singleton
ai_guide = HeritageAIEngine()