# import os
# import sqlite3
# from flask import Flask, render_template, request, jsonify
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_experimental.chains import ConversationChain
# from langchain.memory import ConversationBufferMemory
# from dotenv import load_dotenv

# load_dotenv()

# app = Flask(__name__)


# # --- DATABASE SETUP ---
# def init_db():
#     conn = sqlite3.connect('chat_history.db')
#     c = conn.cursor()
#     c.execute('''CREATE TABLE IF NOT EXISTS messages 
#                  (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)''')
#     conn.commit()
#     conn.close()


# init_db()

# # --- AI SETUP ---
# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.0-flash-exp",
#     google_api_key=os.getenv("GOOGLE_API_KEY"),
#     temperature=0.7
# )

# memory = ConversationBufferMemory()
# # Load existing history into LangChain memory on startup
# conn = sqlite3.connect('chat_history.db')
# c = conn.cursor()
# c.execute("SELECT role, content FROM messages")
# rows = c.fetchall()
# for role, content in rows:
#     if role == "user":
#         memory.chat_memory.add_user_message(content)
#     else:
#         memory.chat_memory.add_ai_message(content)
# conn.close()

# conversation = ConversationChain(llm=llm, memory=memory)


# # --- ROUTES ---
# @app.route('/')
# def index():
#     conn = sqlite3.connect('chat_history.db')
#     c = conn.cursor()
#     c.execute("SELECT role, content FROM messages")
#     chat_history = c.fetchall()
#     conn.close()
#     return render_template('index.html', chat_history=chat_history)


# @app.route('/get_response', methods=['POST'])
# def get_response():
#     user_input = request.json.get("message")

#     # 1. Save User Message to DB
#     conn = sqlite3.connect('chat_history.db')
#     c = conn.cursor()
#     c.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("user", user_input))

#     # 2. Get AI Response
#     try:
#         response = conversation.predict(input=user_input)
#         # 3. Save AI Response to DB
#         c.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("bot", response))
#         conn.commit()
#         return jsonify({"response": response})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         conn.close()


# if __name__ == '__main__':
#     app.run(debug=True)

import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.conversation.base import ConversationChain
from langchain.memory.buffer import ConversationBufferMemory

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# =====================================================
# DATABASE SETUP
# =====================================================
DB_NAME = "chat_history.db"

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# =====================================================
# AI SETUP (GEMINI)
# =====================================================
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7
)

# Keep only last 5 conversation turns in memory
memory = ConversationBufferMemory(k=5)

# Optional: system prompt
memory.chat_memory.add_ai_message(
    "You are a helpful, concise, and friendly AI assistant."
)

conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=False
)

# =====================================================
# ROUTES
# =====================================================
@app.route("/")
def index():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages")
    chat_history = c.fetchall()
    conn.close()

    return render_template("index.html", chat_history=chat_history)

@app.route("/get_response", methods=["POST"])
def get_response():
    user_input = request.json.get("message")

    if not user_input or not user_input.strip():
        return jsonify({"error": "Empty message"}), 400

    conn = get_db_connection()
    c = conn.cursor()

    try:
        # Save user message
        c.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            ("user", user_input)
        )
        conn.commit()

        # Generate AI response
        response = conversation.predict(input=user_input)

        # Save AI response
        c.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            ("ai", response)
        )
        conn.commit()

        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route("/clear_chat", methods=["POST", "GET"])
def clear_chat():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

    memory.clear()
    memory.chat_memory.add_ai_message(
        "You are a helpful, concise, and friendly AI assistant."
    )

    return jsonify({"status": "Chat cleared"})

# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
