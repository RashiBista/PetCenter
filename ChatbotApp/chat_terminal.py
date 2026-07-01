"""
Simple Chatbot - works with OpenAI OR Google Gemini
-----------------------------------------------------
Setup:
    pip install openai google-generativeai

Set ONE of these environment variables before running:
    export OPENAI_API_KEY="your-openai-key"
    export GEMINI_API_KEY="your-gemini-key"

Then choose the provider below (PROVIDER = "openai" or "gemini") and run:
    python simple_chatbot.py
"""

import os

# ---- CHOOSE YOUR PROVIDER ----
PROVIDER = "gemini"  # change to "openai" if you want to use OpenAI instead


def chat_openai(message, history):
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    messages = [{"role": "system", "content": "You are a helpful assistant for PetCenter, a pet health app."}]
    messages += history
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return response.choices[0].message.content


def chat_gemini(message, history):
    import google.generativeai as genai

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash")

    # Gemini expects history as a list of {"role": ..., "parts": [...]}
    gemini_history = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [turn["content"]]})

    chat_session = model.start_chat(history=gemini_history)
    response = chat_session.send_message(message)
    return response.text


def main():
    print("🐾 PetCenter Chatbot (provider:", PROVIDER, ")")
    print("Type 'quit' to exit.\n")

    history = []  # list of {"role": "user"/"assistant", "content": "..."}

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            print("Bot: Goodbye! 🐶")
            break
        if not user_input:
            continue

        try:
            if PROVIDER == "openai":
                reply = chat_openai(user_input, history)
            elif PROVIDER == "gemini":
                reply = chat_gemini(user_input, history)
            else:
                print("Unknown PROVIDER. Set it to 'openai' or 'gemini'.")
                break
        except Exception as e:
            print(f"Bot: Sorry, something went wrong: {e}")
            continue

        print(f"Bot: {reply}\n")

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
