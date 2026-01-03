import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./ChatPanel.css";

const ChatPanel = ({
  messages,
  onSendMessage,
  isLoading,
  onReset,
  onDownload,
  downloadReady = false,
  backendReady = false,
}) => {
  const navigate = useNavigate();
  const [inputMessage, setInputMessage] = useState("");
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputMessage.trim() && !isLoading) {
      onSendMessage(inputMessage);
      setInputMessage("");
    }
  };

  const formatMessage = (content) => {
    // Basic markdown-like formatting
    return content.split("\n").map((line, i) => <p key={i}>{line}</p>);
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-title">
          <h2>AIDevs</h2>
          <span className="subtitle">Your AI Website Builder</span>
        </div>
        <div className="chat-actions">
          <button
            onClick={() => navigate("/")}
            className="btn-icon"
            title="Home"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
          </button>
          <button
            onClick={onDownload}
            className={`btn-icon ${downloadReady ? "" : "disabled"}`}
            title={
              downloadReady
                ? "Download Code"
                : backendReady
                ? "Download Code"
                : "Backend generation in progress..."
            }
            disabled={!downloadReady}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeOpacity={downloadReady ? "1" : "0.5"}
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            {!downloadReady && backendReady === false && (
              <span
                style={{
                  position: "absolute",
                  top: "-5px",
                  right: "-5px",
                  fontSize: "10px",
                }}
              >
                ⏳
              </span>
            )}
          </button>
          <button onClick={onReset} className="btn-icon" title="Reset Session">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
          </button>
        </div>
      </div>

      <div className="messages-container">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="message-avatar">
              {message.role === "assistant" ? "🤖" : "👤"}
            </div>
            <div className="message-content">
              <div className="message-text">
                {formatMessage(message.content)}
              </div>
              <div className="message-time">
                {message.timestamp?.toLocaleTimeString()}
                {message.usingDefaultKey && (
                  <span
                    style={{
                      marginLeft: "10px",
                      color: "#f39c12",
                      fontSize: "11px",
                    }}
                  >
                    ⚡ Using default Groq API
                  </span>
                )}
                {!message.usingDefaultKey && message.role === "assistant" && (
                  <span
                    style={{
                      marginLeft: "10px",
                      color: "#27ae60",
                      fontSize: "11px",
                    }}
                  >
                    ✓ Using your Groq API
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="input-container" onSubmit={handleSubmit}>
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Describe what you want to build..."
          disabled={isLoading}
          className="message-input"
        />
        <button
          type="submit"
          disabled={isLoading || !inputMessage.trim()}
          className="send-button"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </div>
  );
};

export default ChatPanel;
