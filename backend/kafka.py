import uuid
import json
import httpx
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import os
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio

# Load environment variables early
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Kafka settings
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
USER_MESSAGES_TOPIC = "chat_user_messages"
ASSISTANT_RESPONSES_TOPIC = "chat_assistant_responses"

producer = None
consumer = None

# Initialize FastAPI app early (before startup events)
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is missing in .env")

print("Loaded API Key:", OPENROUTER_API_KEY[:5] + "..." + OPENROUTER_API_KEY[-5:])

# In-memory session store
sessions: Dict[str, List[Dict[str, str]]] = {}

# System prompt
SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a friendly and helpful assistant. Answer user queries in a clear and engaging way."
}

# Kafka startup and shutdown events
@app.on_event("startup")
async def startup_event():
    global producer, consumer
    loop = asyncio.get_event_loop()

    producer = AIOKafkaProducer(loop=loop, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()

    consumer = AIOKafkaConsumer(
        ASSISTANT_RESPONSES_TOPIC,
        loop=loop,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="fastapi_chat_consumer"
    )
    await consumer.start()

@app.on_event("shutdown")
async def shutdown_event():
    if producer:
        await producer.stop()
    if consumer:
        await consumer.stop()

# WebSocket route for chat with Kafka integration
@app.websocket("/ws/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    try:
        # Receive initial session_id or create a new one
        init_data = await websocket.receive_json()
        session_id = init_data.get("session_id")
        if not session_id or session_id not in sessions:
            session_id = str(uuid.uuid4())
            sessions[session_id] = [SYSTEM_PROMPT.copy()]
            print(f"Created new session: {session_id}")
        else:
            print(f"Resumed session: {session_id}")

        # Send session_id back to client
        await websocket.send_json({"type": "session", "session_id": session_id})

        # Send chat history (excluding system prompt)
        for msg in sessions[session_id][1:]:
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

            print("User message:", message)

            # Append user message to session history
            sessions[session_id].append({"role": "user", "content": message})

            # Produce user message to Kafka
            msg_obj = {
                "session_id": session_id,
                "role": "user",
                "content": message
            }
            await producer.send_and_wait(USER_MESSAGES_TOPIC, json.dumps(msg_obj).encode("utf-8"))
            print(f"Produced message to Kafka topic {USER_MESSAGES_TOPIC}")

            # Notify client that streaming will start
            await websocket.send_json({"type": "start"})

            # Consume assistant responses from Kafka and stream to client
            assistant_content = ""
            async for msg in consumer:
                msg_value = json.loads(msg.value.decode("utf-8"))
                if msg_value.get("session_id") == session_id:
                    delta = msg_value.get("content", "")
                    if delta:
                        assistant_content += delta
                        await websocket.send_json({
                            "type": "chunk",
                            "role": "assistant",
                            "content": delta
                        })

                    # When 'done' flag is True, end streaming for this response
                    if msg_value.get("done", False):
                        await websocket.send_json({"type": "end"})
                        break

            # Append assistant response to session history
            sessions[session_id].append({"role": "assistant", "content": assistant_content})

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print("Unexpected error:", e)
        await websocket.send_json({"type": "error", "content": str(e)})
