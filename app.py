import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from rag import init_db, extract_text, chunk_text, store_chunks, retrieve_chunks
from chatbot_config import CHATBOT_TITLE, SYSTEM_PROMPT

load_dotenv()

app = Flask(__name__)
init_db()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
MODEL = "gemini-3.1-flash-lite"

@app.route("/")
def home():
    return render_template("index.html", chatbot_title=CHATBOT_TITLE)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "Please select a file."}), 400

    text = extract_text(file)
    if not text.strip():
        return jsonify({"error": "No readable text found in the file."}), 400

    chunks = chunk_text(text)
    store_chunks(file.filename, chunks)
    return jsonify({"message": f"{file.filename} uploaded successfully."})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = data.get("message", "").strip()

    if not question:
        return jsonify({"reply": "Please enter a question."}), 400

    context = retrieve_chunks(question)

    if not context:
        return jsonify({"reply": "Information not found in the uploaded documents."})

    if not client:
        return jsonify({"reply": "GEMINI_API_KEY is not configured."}), 500

    prompt = f"""{SYSTEM_PROMPT}

Uploaded document context:
{context}

User question:
{question}

Answer only using the uploaded document context. If the answer is not present in the context, say that the information was not found in the uploaded documents.
"""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
