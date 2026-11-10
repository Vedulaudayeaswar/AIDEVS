import React, { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import LoginModal from "./LoginModal";
import { useAuth } from "../auth/AuthContext";

// Standalone /login route (used for redirects from protected pages).
export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { status } = useAuth();
  const target = (location.state && location.state.from) || "/projects";

  useEffect(() => {
    if (status === "authenticated") navigate(target, { replace: true });
  }, [status, navigate, target]);

  return (
    <div style={{ minHeight: "100vh", background: "#000" }}>
      <LoginModal isOpen onClose={() => navigate("/")} onLoginSuccess={() => navigate(target, { replace: true })} />
    </div>
  );
}
