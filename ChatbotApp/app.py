"""
Simple Chatbot - Web Version (Flask + Gemini)
------------------------------------------------
Setup:
    pip install flask google-generativeai

Set your API key before running:
    export GEMINI_API_KEY="your-actual-key"

Run:
    python app.py

Then open in your browser:
    http://127.0.0.1:5000
"""

import os

from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-this"  # needed for session/history

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")


@app.route("/")
def home():
    session["history"] = []  # reset conversation on page load
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Please type something!"})

    history = session.get("history", [])

    # Build Gemini-formatted history
    gemini_history = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [turn["content"]]})

    try:
        chat_session = model.start_chat(history=gemini_history)
        response = chat_session.send_message(user_message)
        reply = response.text
    except Exception as e:
        reply = f"Sorry, something went wrong: {e}"

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    session["history"] = history

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True)
