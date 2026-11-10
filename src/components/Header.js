import React, { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";
import LoginModal from "./LoginModal";

const Header = () => {
  const navigate = useNavigate();
  const { user, status, logout } = useAuth();
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const isLoggedIn = status === "authenticated" && user;

  const handleGetStarted = () => navigate(isLoggedIn ? "/projects" : "/register");
  const handleLogin = () => setIsLoginModalOpen(true);
  const handleLoginSuccess = () => {
    setIsLoginModalOpen(false);
    navigate("/projects");
  };
  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  useEffect(() => {
    // Enable smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener("click", function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute("href"));
        if (target) {
          target.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }
      });
    });
  }, []);

  return (
    <>
      <header>
        <div className="logo">
          <svg width="40" height="40" viewBox="0 0 40 40">
            <path
              d="M10 15 L20 10 L30 15 L20 20 Z M20 20 L30 25 L20 30 L10 25 Z"
              fill="currentColor"
            />
          </svg>
          <span>AIDevs</span>
        </div>
        <nav>
          <a href="#features">Features</a>
          <a href="#services">Services</a>
          <a href="#updates">Updates</a>
          <a href="#contact">Contact</a>
        </nav>
        <div className="header-actions">
          {isLoggedIn ? (
            <>
              <span className="username-display">Hi, {user.firstName}</span>
              <button className="btn-secondary" onClick={() => navigate("/projects")}>
                My Projects
              </button>
              <button className="btn-secondary" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <button className="btn-secondary" onClick={handleLogin}>
              Login
            </button>
          )}
          <button className="btn-primary" onClick={handleGetStarted}>
            {isLoggedIn ? "Open Studio" : "Get Started"}
          </button>
        </div>
      </header>

      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLoginSuccess={handleLoginSuccess}
      />
    </>
  );
};

export default Header;
