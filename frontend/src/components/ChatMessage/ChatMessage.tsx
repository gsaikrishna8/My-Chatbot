import React from "react";
import "./ChatMessage.css";
import TypingIndicator from "../TypingIndicator/TypingIndicator";

interface Props {
  message: {
    text: string;
    sender: "user" | "assistant";
    isTyping?: boolean;
  };
}

const ChatMessage: React.FC<Props> = ({ message }) => {
  const isUser = message.sender === "user";

  const avatar = isUser
    ? "https://cdn-icons-png.flaticon.com/512/1946/1946429.png"
    : "https://cdn-icons-png.flaticon.com/512/4712/4712035.png";

  return (
    <div className={`chat-message ${isUser ? "user" : "assistant"}`}>
      {!isUser && <img className="avatar" src={avatar} alt="bot" />}
      <div className="message-bubble">
        {message.text}
        {!isUser && message.isTyping && <TypingIndicator />}
      </div>
      {isUser && <img className="avatar" src={avatar} alt="user" />}
    </div>
  );
};

export default ChatMessage;
