import React, { useEffect, useState, useRef } from "react";
import "./App.css";
import { v4 as uuidv4 } from "uuid";
import ChatMessage from "./components/ChatMessage/ChatMessage";
// import TypingIndicator from "./components/TypingIndicator/TypingIndicator";

const WS_URL = `ws://${window.location.host}/ws/chat`;
// const WS_URL = "ws://127.0.0.1:8000/ws/chat";

export type ChatMessageType = {
  id: string;
  text: string;
  sender: "user" | "assistant";
  isTyping?: boolean;
};

function App() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  // const [isTyping, setIsTyping] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const streamingBufferRef = useRef<string>("");
  const sessionIdRef = useRef<string | null>(null);
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    if (!sessionReady) return;
    console.log("sessionId:", sessionId);
    // if (sessionId === null) return;

    console.log("Connecting to WebSocket:", WS_URL);
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log("WebSocket connected");
      ws.send(JSON.stringify({ session_id: sessionId }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "session") {
        setSessionId(data.session_id);
        return;
      }

      if (data.type === "start") {
        streamingBufferRef.current = "";
        setStreaming(true);
        setMessages((prev) => [
          ...prev,
          { id: uuidv4(), sender: "assistant", text: "", isTyping: true },
        ]);
      }

      if (data.type === "chunk") {
        streamingBufferRef.current += data.content;
        setMessages((prev) => {
          const updated = [...prev];
          const lastIndex = updated.length - 1;
          if (lastIndex >= 0 && updated[lastIndex].sender === "assistant") {
            updated[lastIndex] = {
              ...updated[lastIndex],
              text: streamingBufferRef.current,
              isTyping: true,
            };
          }
          return updated;
        });
      }
      if (data.type === "history") {
        setMessages((Prev) => [
          ...Prev,
          {
            id: uuidv4(),
            sender: data.sender,
            text: data.text,
            isTyping: false,
          },
        ]);
      }

      if (data.type === "end") {
        setStreaming(false);
        setMessages((prev) => {
          const updated = [...prev];
          const lastIndex = updated.length - 1;
          if (lastIndex >= 0 && updated[lastIndex].sender === "assistant") {
            updated[lastIndex] = {
              ...updated[lastIndex],
              isTyping: false,
            };
          }
          return updated;
        });
      }

      if (data.type === "error") {
        console.error("Server error:", data.content);
      }
    };

    ws.onerror = (err) => console.error("WebSocket error:", err);
    ws.onclose = () => console.log("WebSocket closed");

    socketRef.current = ws;

    return () => {
      ws.close();
    };
  }, [sessionReady]);

  useEffect(() => {
    const savedSessionId = localStorage.getItem("chat_session_id");
    const savedMessages = localStorage.getItem("chat_message");

    if (savedSessionId) {
      setSessionId(savedSessionId);
    }
    setSessionReady(true);
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages));
    }
  }, []);

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem("chat_session_id", sessionId);
    }
  }, [sessionId]);
  useEffect(() => {
    localStorage.setItem("chat_message", JSON.stringify(messages));
  }, [messages]);
  const sendMessage = () => {
    if (!input.trim() || !socketRef.current || streaming) return;

    const userMessage: ChatMessageType = {
      id: uuidv4(),
      text: input,
      sender: "user",
    };

    setMessages((prev) => [...prev, userMessage]);

    socketRef.current.send(
      JSON.stringify({ session_id: sessionId, message: input })
    );
    setInput("");
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") sendMessage();
  };

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
  const handleClearSession = () => {
    setMessages([]);
    setSessionId(null);
    localStorage.removeItem("chat_session_id");
    localStorage.removeItem("chat_message");
  };
  return (
    <div className="chat-wrapper">
      <div className="chat-header">
        <button
          className="clear-btn"
          onClick={handleClearSession}
          disabled={messages.length === 0}
        >
          🗑 Clear
        </button>
      </div>

      <div className="chat-box">
        {messages.length === 0 ? (
          <div className="question-container">
            <h2>How can I assist you today?</h2>
          </div>
        ) : (
          <div className="chat-messages">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={messageEndRef} />
          </div>
        )}

        <div className="chat-input-area">
          <div className="chat-input-area-inner">
            <input
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              disabled={streaming}
            />
            <button onClick={sendMessage} disabled={streaming}>
              ➤
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
