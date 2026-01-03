import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./ChatbotPage.css";
import ChatPanel from "./ChatPanel";
import PreviewPanel from "./PreviewPanel";

function ChatbotPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [previewCode, setPreviewCode] = useState({ html: "", css: "", js: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check authentication on mount
  useEffect(() => {
    const token = localStorage.getItem("aidevs_token");
    if (!token) {
      navigate("/register");
      return;
    }
    setIsAuthenticated(true);
  }, [navigate]);

  // Initial welcome message
  useEffect(() => {
    if (!isAuthenticated) return;

    const username = localStorage.getItem("aidevs_username");
    const firstName = username ? username.split(".")[0] : "there";

    setMessages([
      {
        role: "assistant",
        content: `Hi ${firstName}! 👋 Welcome back to AIDevs! I'm your AI Website Builder with a team of expert engineers ready to help. What kind of website would you like to build today?`,
        timestamp: new Date(),
      },
    ]);
  }, [isAuthenticated]);

  const sendMessage = async (userMessage) => {
    // Add user message to chat
    const newUserMessage = {
      role: "user",
      content: userMessage,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);

    try {
      const token = localStorage.getItem("aidevs_token");

      if (!token) {
        navigate("/register");
        return;
      }

      // Send to backend with JWT
      const response = await fetch("http://localhost:5000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: userMessage,
        }),
      });

      const data = await response.json();

      if (data.success) {
        // Add assistant response
        const assistantMessage = {
          role: "assistant",
          content: data.response,
          timestamp: new Date(),
        };

        // Add indicator if using default API key
        if (data.using_default_key) {
          assistantMessage.usingDefaultKey = true;
        }

        setMessages((prev) => [...prev, assistantMessage]);

        // Update preview if code was generated
        if (data.has_preview) {
          fetchPreview();
        }
      } else {
        throw new Error(data.error);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${error.message}. Please make sure the backend server is running.`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPreview = async () => {
    try {
      const token = localStorage.getItem("aidevs_token");

      const response = await fetch("http://localhost:5000/api/preview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({}),
      });

      const data = await response.json();
      if (data.success) {
        setPreviewCode({
          html: data.html,
          css: data.css,
          js: data.js,
        });
      }
    } catch (error) {
      console.error("Preview fetch error:", error);
    }
  };

  const downloadCode = async () => {
    try {
      const token = localStorage.getItem("aidevs_token");
      const username = localStorage.getItem("aidevs_username");

      const response = await fetch("http://localhost:5000/api/download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({}),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `aidevs_${username}_website.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error("Download error:", error);
    }
  };

  const resetSession = async () => {
    try {
      const token = localStorage.getItem("aidevs_token");

      await fetch("http://localhost:5000/api/reset", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({}),
      });

      // Reset local state
      setMessages([
        {
          role: "assistant",
          content:
            "Session reset! Let's build something new. What kind of website would you like to create?",
          timestamp: new Date(),
        },
      ]);
      setPreviewCode({ html: "", css: "", js: "" });
    } catch (error) {
      console.error("Reset error:", error);
    }
  };

  return (
    <div className="ChatbotPage">
      <div className="split-container">
        <ChatPanel
          messages={messages}
          onSendMessage={sendMessage}
          isLoading={isLoading}
          onReset={resetSession}
          onDownload={downloadCode}
        />
        <PreviewPanel
          html={previewCode.html}
          css={previewCode.css}
          js={previewCode.js}
        />
      </div>
    </div>
  );
}

export default ChatbotPage;
