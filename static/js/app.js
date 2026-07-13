/**
 * Inkwake Heritage Guide - Frontend Logic
 * Handles: AI Chat, Image Scanning, & Audio Guides
 */

// --- 1. Chatbot & Multilingual Logic ---
async function sendChatMessage() {
    const queryInput = document.getElementById('user-query');
    const chatBox = document.getElementById('chat-box');
    const lang = document.getElementById('lang-selector').value;
    const query = queryInput.value.trim();

    if (!query) return;

    // Append User Message to UI
    chatBox.innerHTML += `<div class="user-msg"><strong>You:</strong> ${query}</div>`;
    queryInput.value = '';

    try {
        const response = await fetch(`/api/chatbot/ask?query=${encodeURIComponent(query)}&lang=${lang}`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.status === "success") {
            // Append Bot Message
            chatBox.innerHTML += `<div class="bot-msg"><strong>AI:</strong> ${data.text}</div>`;
            
            // Auto-generate voice if it's a short response or desired
            // playVoice(data.text, lang); 
            
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    } catch (error) {
        console.error("Chat Error:", error);
        chatBox.innerHTML += `<div class="bot-msg error">Sorry, I encountered an error.</div>`;
    }
}

// --- 2. Image Recognition (Feature 3) ---
document.getElementById('camera-input').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // UI Feedback: Show loading state
    const scanOverlay = document.getElementById('scan-result-overlay');
    const landmarkName = document.getElementById('landmark-name');
    landmarkName.innerText = "Analyzing Landmark...";
    scanOverlay.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/recognition/scan', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.status === "success") {
            // Populate Results
            landmarkName.innerText = data.name;
            document.getElementById('landmark-desc').innerText = data.history;
            
            // Set up Navigation Link (Feature 5)
            const mapLink = document.getElementById('map-link');
            mapLink.href = `https://www.google.com/maps/dir/?api=1&destination=${data.coordinates.lat},${data.coordinates.lng}`;
            
            // Store data for voice playback
            window.currentScanText = data.history;
            window.currentScanLang = document.getElementById('lang-selector').value;
        } else {
            landmarkName.innerText = "Unknown Landmark";
            document.getElementById('landmark-desc').innerText = data.message;
        }
    } catch (error) {
        console.error("Scan Error:", error);
        landmarkName.innerText = "Error";
        document.getElementById('landmark-desc').innerText = "Could not reach the vision server.";
    }
});

// --- 3. Voice Generation & Playback (Feature 4) ---
async function playResultVoice() {
    const text = window.currentScanText;
    const lang = window.currentScanLang || 'ta';

    if (!text) return;

    try {
        const response = await fetch(`/api/chatbot/voice-guide?text=${encodeURIComponent(text)}&lang=${lang}`);
        const data = await response.json();

        if (data.audio_url) {
            const audio = new Audio(data.audio_url);
            audio.play();
        }
    } catch (error) {
        console.error("Voice Error:", error);
    }
}

// --- 4. UI Helpers ---
function closeResult() {
    document.getElementById('scan-result-overlay').classList.add('hidden');
}

// Handle "Enter" key for chat
document.getElementById('user-query').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
});