import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import LoginModal from "./LoginModal";

const Header = () => {
  const navigate = useNavigate();
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState("");

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem("aidevs_token");
    const storedUsername = localStorage.getItem("aidevs_username");
    if (token && storedUsername) {
      setIsLoggedIn(true);
      setUsername(storedUsername);
    }
  }, []);

  const handleGetStarted = () => {
    const token = localStorage.getItem("aidevs_token");
    if (token) {
      navigate("/chatbot");
    } else {
      navigate("/register");
    }
  };

  const handleLogin = () => {
    setIsLoginModalOpen(true);
  };

  const handleLoginSuccess = (data) => {
    setIsLoggedIn(true);
    setUsername(data.username);
    setIsLoginModalOpen(false);
    navigate("/chatbot");
  };

  const handleLogout = () => {
    localStorage.removeItem("aidevs_token");
    localStorage.removeItem("aidevs_username");
    setIsLoggedIn(false);
    setUsername("");
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
              <span className="username-display">
                Hi, {username.split(".")[0]}
              </span>
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
            Get Started
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
