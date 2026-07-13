# 🏛️ Vardhan Holidays: AI-Powered Heritage Explorer

Vardhan Holidays is a premium cultural discovery platform designed to guide travelers through the architectural and historical wonders of South India. This platform leverages generative AI for historical grounding and neural voice synthesis to provide an immersive, hands-free tour experience.

## 🚀 Features

- **Heritage Explorer:** A dynamic directory of historical sites (Chola, Pandya, Pallava, and Nayak dynasties) with real-time filtering and search capabilities.
- **Oracle AI Concierge:** A RAG-grounded chatbot powered by **Google Gemini**, capable of answering complex historical and cultural queries.
- **Neural Voice Guide:** High-fidelity TTS (Text-to-Speech) using Edge-TTS, allowing users to experience guided tours in English or Tamil.
- **Secure Admin Portal:** A comprehensive dashboard to manage bookings, track revenue, update tour packages, and resolve traveler enquiries.
- **Identity Vault:** Secure user registration and profile management.

## 🛠️ Technical Stack

- **Backend:** Flask (Python)
- **Database:** SQLAlchemy (SQLite for local, MySQL for production)
- **AI Engine:** Google GenAI SDK (Gemini 2.5 Flash)
- **Frontend:** HTML5, Tailwind CSS, Jinja2
- **Audio Engine:** `edge-tts` (Asynchronous Neural Voice Synthesis)
- **Architecture:** Modular Blueprint design for high scalability

## 📂 Project Structure

```text
/
├── app/
│   ├── api/            # Route blueprints (explorer, admin, bookings, chatbot)
│   ├── database/       # SQLAlchemy models and persistence logic
│   └── services/       # AI Engine integration
├── static/             # Assets, images, and ephemeral audio logs
├── templates/          # Jinja2 HTML templates
├── main.py             # Flask application entry point
└── requirements.txt    # Project dependencies


git clone [https://github.com/dhanushmsr/Tour-Guide-With-LLM-and-Voice-based-guide.git](https://github.com/dhanushmsr/Tour-Guide-With-LLM-and-Voice-based-guide.git)
cd Tour-Guide-With-LLM-and-Voice-based-guide

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

python main.py```

For more about this:  mdhanushdsm@gmail.com
https://dhanush-m.vercel.app/
