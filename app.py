from flask import Flask, jsonify, request
from uuid import uuid4
import os


app = Flask(__name__)


# ============================================================
# Temporary in-memory chat storage
# ============================================================

chats = {}


# ============================================================
# Health Check
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "online",
            "service": "VEYRiX API",
            "version": "0.2"
        }
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
    Receive a message.

    The AI engine will be connected after the
    Flask service is successfully deployed.
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

    # Store user message
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

    # Temporary response while the hosted AI engine
    # is being configured.
    response = (
        "VEYRiX backend is online, but the AI engine "
        "has not been connected to the Render server yet."
    )

    # Store assistant response
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
# Error Handling
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
# Start Server
# ============================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    print("=" * 60)
    print("VEYRiX AI v0.2")
    print("=" * 60)
    print("Backend: Flask")
    print("Deployment: Render")
    print("AI Engine: Pending")
    print("API Keys: None")
    print("Memory: Temporary")
    print()
    print(f"VEYRiX server starting on port {port}...")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
