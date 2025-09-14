import React, { useEffect, useState } from "react";
import "./TypingIndicator.css";
const TypingIndicator: React.FC = () => {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length === 3 ? "" : prev + "."));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <span style={{ marginLeft: 5, fontStyle: "italic" }}>Typing{dots}</span>
  );
};

export default TypingIndicator;
