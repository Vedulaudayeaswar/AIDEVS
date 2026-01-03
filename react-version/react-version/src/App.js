import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./App.css";
import HomePage from "./components/HomePage";
import ChatbotPage from "./components/ChatbotPage";
import RegisterPage from "./components/RegisterPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/chatbot" element={<ChatbotPage />} />
      </Routes>
    </Router>
  );
}

export default App;
