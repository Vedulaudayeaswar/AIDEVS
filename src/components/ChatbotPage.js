import React, { useState, useEffect } from "react";
import "./ChatbotPage.css";
import ChatPanel from "./ChatPanel";
import PreviewPanel from "./PreviewPanel";
import { api, apiFetch } from "../lib/api";
import { useAuth } from "../auth/AuthContext";

function ChatbotPage() {
  const [messages, setMessages] = useState([]);
  const [previewCode, setPreviewCode] = useState({ html: "", css: "", js: "" });
  const [isLoading, setIsLoading] = useState(false);
  const { user } = useAuth();
  const isAuthenticated = Boolean(user);
  const [downloadReady, setDownloadReady] = useState(false);
  const [backendReady, setBackendReady] = useState(false);


  // Initial welcome message
  useEffect(() => {
    if (!isAuthenticated) return;

    const firstName = user ? user.firstName : "there";

    setMessages([
      {
        role: "assistant",
        content: `Hi ${firstName}! 👋 Welcome back to AIDevs! I'm your AI Website Builder with a team of expert engineers ready to help. What kind of website would you like to build today?`,
        timestamp: new Date(),
      },
    ]);
  }, [isAuthenticated, user]);

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
      const data = await api.post("/api/chat", { message: userMessage });

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
          content: `Error: ${error.message}. `,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPreview = async () => {
    try {
      const data = await api.post("/api/preview");
      if (data.success) {
        setPreviewCode({
          html: data.html,
          css: data.css,
          js: data.js,
        });
      }

      // Also check status after fetching preview
      checkStatus();
    } catch (error) {
      console.error("Preview fetch error:", error);
    }
  };

  const checkStatus = async () => {
    try {
      const data = await api.post("/api/status");
      if (data.success) {
        setBackendReady(data.backend_ready);
        setDownloadReady(data.download_ready);
      }
    } catch (error) {
      console.error("Status check error:", error);
    }
  };

  const downloadCode = async () => {
    // Check status first
    if (!downloadReady) {
      const statusMessage = !backendReady
        ? "⏳ Backend code is still being generated. Please wait for the complete build to finish."
        : "⚠️ Code is not ready for download yet.";

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: statusMessage,
          timestamp: new Date(),
        },
      ]);
      return;
    }

    try {
      const response = await apiFetch("/api/download", { method: "POST", body: {}, raw: true });
      const username = user ? user.username : "user";

      {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `aidevs_${username}_website.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        // Show success message
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              "✅ Your complete website package (frontend + backend) has been downloaded successfully!",
            timestamp: new Date(),
          },
        ]);
      }
    } catch (error) {
      console.error("Download error:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ Download error: ${error.message}`,
          timestamp: new Date(),
        },
      ]);
    }
  };

  const resetSession = async () => {
    try {
      await api.post("/api/reset");

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
          downloadReady={downloadReady}
          backendReady={backendReady}
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
