from flask import Flask, jsonify, request, send_from_directory
from uuid import uuid4
from pathlib import Path

from veyrix.core import ask_veyrix


BASE_DIR = Path(__file__).resolve().parent


app = Flask(
    __name__,
    static_folder=None
)


# ============================================================
# Temporary in-memory chat storage
# ============================================================

chats = {}


# ============================================================
# Website
# ============================================================

@app.route("/")
def index():
    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(
        BASE_DIR / "css",
        filename
    )


@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(
        BASE_DIR / "js",
        filename
    )


# ============================================================
# Chat API
# ============================================================

@app.route("/api/chats", methods=["GET"])
def get_chats():
    """
    Return all available chats.
    """

    result = []

    for chat_id, chat in chats.items():
        result.append(
            {
                "id": chat_id,
                "name": chat["name"]
            }
        )

    return jsonify(result)


@app.route("/api/chats", methods=["POST"])
def create_chat():
    """
    Create a new conversation.
    """

    chat_id = str(uuid4())

    chats[chat_id] = {
        "id": chat_id,
        "name": "New Chat",
        "messages": []
    }

    return jsonify(
        {
            "id": chat_id,
            "name": "New Chat"
        }
    ), 201


@app.route("/api/chats/<chat_id>", methods=["GET"])
def get_chat(chat_id):
    """
    Return all messages in a conversation.
    """

    chat = chats.get(chat_id)

    if chat is None:
        return jsonify(
            {
                "error": "Chat not found"
            }
        ), 404

    return jsonify(chat["messages"])


@app.route("/api/chats/<chat_id>/message", methods=["POST"])
def send_message(chat_id):
    """
    Send a user message to VEYRiX and return the response.
    """

    chat = chats.get(chat_id)

    if chat is None:
        return jsonify(
            {
                "error": "Chat not found"
            }
        ), 404

    data = request.get_json(silent=True)

    if not data:
        return jsonify(
            {
                "error": "Request body must contain JSON"
            }
        ), 400

    user_message = data.get("message")

    if not isinstance(user_message, str):
        return jsonify(
            {
                "error": "Message must be a string"
            }
        ), 400

    user_message = user_message.strip()

    if not user_message:
        return jsonify(
            {
                "error": "Message cannot be empty"
            }
        ), 400

    # Add user message
    chat["messages"].append(
        {
            "role": "user",
            "content": user_message
        }
    )

    # Automatically name the chat from the first message
    if chat["name"] == "New Chat":
        chat["name"] = user_message[:40]

        if len(user_message) > 40:
            chat["name"] += "..."

    try:
        # Ask local VEYRiX model
        response = ask_veyrix(
            chat["messages"]
        )

    except Exception as error:
        # Remove the user message if the AI failed.
        chat["messages"].pop()

        print()
        print("=" * 60)
        print("VEYRiX BACKEND ERROR")
        print("=" * 60)
        print(error)
        print("=" * 60)
        print()

        return jsonify(
            {
                "error": "VEYRiX could not generate a response.",
                "details": str(error)
            }
        ), 500

    # Store VEYRiX response
    chat["messages"].append(
        {
            "role": "assistant",
            "content": response
        }
    )

    return jsonify(
        {
            "response": response
        }
    )


@app.route("/api/chats/<chat_id>/clear", methods=["POST"])
def clear_chat(chat_id):
    """
    Delete all messages from a conversation.
    """

    chat = chats.get(chat_id)

    if chat is None:
        return jsonify(
            {
                "error": "Chat not found"
            }
        ), 404

    chat["messages"].clear()
    chat["name"] = "New Chat"

    return jsonify(
        {
            "success": True
        }
    )


@app.route("/api/chats/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    """
    Completely delete a conversation.
    """

    if chat_id not in chats:
        return jsonify(
            {
                "error": "Chat not found"
            }
        ), 404

    del chats[chat_id]

    return jsonify(
        {
            "success": True
        }
    )


# ============================================================
# Error handling
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify(
        {
            "error": "Endpoint not found"
        }
    ), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify(
        {
            "error": "Internal server error"
        }
    ), 500


# ============================================================
# Start server
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("VEYRiX AI v0.2")
    print("=" * 60)
    print("Backend: Flask")
    print("AI Engine: Ollama")
    print("Model: Qwen3 1.7B")
    print("API Keys: None")
    print("Memory: Temporary")
    print()
    print("VEYRiX server starting...")
    print("Open: http://127.0.0.1:5000")
    print("=" * 60)
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
