# My Chatbot

## Project Overview

This project is a chatbot application with a React frontend and FastAPI backend using WebSockets for real-time streaming of chat responses.

---

## Session ID Handling

- The **backend** generates a unique `session_id` for each new user session.
- The **frontend** initially tries to load an existing `session_id` from `localStorage`.
- If no `session_id` exists, the frontend connects to the backend without one.
- The backend sends back a `"session"` message containing the newly created `session_id`.
- The frontend saves this `session_id` in state and in `localStorage` for persistence.
- All future WebSocket communications include this `session_id` to maintain session continuity.

---

## Running the Backend

```bash
uvicorn main:app --reload --host localhost --port 8000
```

---

## Running the Frontend

```bash
npm install
npm start
```

---

## Key Notes

- **WebSocket connection:** The frontend waits for a valid `session_id` before connecting.
- **Session persistence:** Messages and `session_id` are saved to `localStorage` to maintain chat history across page reloads.
- **Streaming:** The backend streams chat responses in chunks, which the frontend assembles and displays in real-time.

---
