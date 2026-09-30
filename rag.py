import io
import re
import sqlite3
from pypdf import PdfReader
from docx import Document

DB_NAME = "rag_store.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def extract_text(file):
    filename = file.filename.lower()
    data = file.read()

    if filename.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if filename.endswith(".docx"):
        document = Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs)

    if filename.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")

    return ""

def chunk_text(text, size=700):
    words = re.findall(r"\S+", text)
    chunks = []
    for i in range(0, len(words), size):
        chunks.append(" ".join(words[i:i + size]))
    return chunks

def store_chunks(filename, chunks):
    conn = get_connection()
    conn.execute("DELETE FROM chunks WHERE filename = ?", (filename,))
    conn.executemany(
        "INSERT INTO chunks (filename, content) VALUES (?, ?)",
        [(filename, chunk) for chunk in chunks]
    )
    conn.commit()
    conn.close()

def retrieve_chunks(question, limit=5):
    question_words = {
        word.lower()
        for word in re.findall(r"[A-Za-z0-9]+", question)
        if len(word) > 2
    }

    conn = get_connection()
    rows = conn.execute("SELECT filename, content FROM chunks").fetchall()
    conn.close()

    scored = []
    for filename, content in rows:
        content_words = set(re.findall(r"[A-Za-z0-9]+", content.lower()))
        score = len(question_words & content_words)
        if score > 0:
            scored.append((score, filename, content))

    scored.sort(reverse=True, key=lambda item: item[0])

    selected = scored[:limit]
    return "\n\n".join(
        f"[Source: {filename}]\n{content}" for _, filename, content in selected
    )
