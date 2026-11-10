import React, { Suspense, lazy } from "react";
import { BrowserRouter as Router, Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import "./styles/aidevs.css";
import HomePage from "./components/HomePage";
import RegisterPage from "./components/RegisterPage";
import LoginPage from "./components/LoginPage";
import ServerStatus from "./components/ServerStatus";
import { AuthProvider, RequireAuth } from "./auth/AuthContext";

// Heavy screens are code-split so the marketing page stays fast.
const ProjectsPage = lazy(() => import("./studio/ProjectsPage"));
const Studio = lazy(() => import("./studio/Studio"));
const ChatbotPage = lazy(() => import("./components/ChatbotPage"));
const AccountPage = lazy(() => import("./studio/AccountPage"));
const AdminPage = lazy(() => import("./studio/AdminPage"));
const LegalPage = lazy(() => import("./studio/LegalPage"));

const Loading = () => (
  <div className="aid-fullscreen-msg"><div className="aid-spinner" />Loading…</div>
);

function App() {
  return (
    <AuthProvider>
      <Router>
        <ServerStatus />
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/projects" element={<RequireAuth><ProjectsPage /></RequireAuth>} />
            <Route path="/studio/:projectId" element={<RequireAuth><Studio /></RequireAuth>} />
            <Route path="/chatbot" element={<RequireAuth><ChatbotPage /></RequireAuth>} />
            <Route path="/account" element={<RequireAuth><AccountPage /></RequireAuth>} />
            <Route path="/admin" element={<RequireAuth><AdminPage /></RequireAuth>} />
            <Route path="/legal/:doc" element={<LegalPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </Router>
    </AuthProvider>
  );
}

export default App;
