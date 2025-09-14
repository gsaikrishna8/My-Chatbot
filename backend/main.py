import uuid
import json
import httpx
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import os
from fastapi.middleware.cors import CORSMiddleware



# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Get API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is missing in .env")

print("Loaded API Key:", OPENROUTER_API_KEY[:5] + "..." + OPENROUTER_API_KEY[-5:])

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# In-memory session store
sessions: Dict[str, List[Dict[str, str]]] = {}

# Define your assistant's personality (system prompt)
SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a friendly and helpful assistant. Answer user queries in a clear and engaging way."
}

# OpenRouter API settings
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}


# Helper: Stream responses from OpenRouter
async def openrouter_stream(messages: List[Dict[str, str]]):
    data = {
        "model": "gpt-4o",
        "messages": messages,
        "stream": True,
        "max_tokens": 1000  # Limit to something safe (try 500–1000)
    }

    print("Sending to OpenRouter:", json.dumps(data, indent=2))

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", OPENROUTER_API_URL, headers=HEADERS, json=data) as response:
            async for chunk in response.aiter_lines():
                print("Raw chunk:", chunk)
                if chunk.startswith("data: "):
                    data_str = chunk[len("data: "):].strip()
                    if data_str == "[DONE]":
                        print("Completed stream.")
                        break
                    try:
                        yield json.loads(data_str)
                    except json.JSONDecodeError:
                        print("JSON Decode Failed:", data_str)
                        continue

# WebSocket route for chat
@app.websocket("/ws/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    try:
        # Get initial session ID or create new one
        init_data = await websocket.receive_json()
        session_id = init_data.get("session_id")
        if not session_id or session_id not in sessions:
            session_id = str(uuid.uuid4())
            sessions[session_id] = [SYSTEM_PROMPT.copy()]
            print(f"Created new session: {session_id}")
        else:
            print(f"Resumed session: {session_id}")

        await websocket.send_json({"type": "session", "session_id": session_id})

        # Send previous messages (excluding system prompt)
        for msg in sessions[session_id][1:]:  # Skip system prompt
            await websocket.send_json({
                "type": "history",
                "sender": msg["role"],
                "text": msg["content"]
            })

        # Chat loop
        while True:
            data = await websocket.receive_json()
            message = data.get("message")
            if not message:
                await websocket.send_json({"type": "error", "content": "Message is required"})
                continue

            # Log user message
            print("User message:", message)

            # Add user message to session history
            sessions[session_id].append({"role": "user", "content": message})

            # Notify client that streaming is starting
            await websocket.send_json({"type": "start"})

            assistant_content = ""

            async for chunk in openrouter_stream(sessions[session_id]):
                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if delta:
                    assistant_content += delta
                    await websocket.send_json({
                        "type": "chunk",
                        "role": "assistant",
                        "content": delta
                    })

            print("Assistant full response:", assistant_content)

            sessions[session_id].append({"role": "assistant", "content": assistant_content})
            await websocket.send_json({"type": "end"})

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print("Unexpected error:", e)
        await websocket.send_json({"type": "error", "content": str(e)})
