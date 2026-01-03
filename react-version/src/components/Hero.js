import React from "react";
import { useNavigate } from "react-router-dom";

const Hero = () => {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate("/chatbot");
  };

  return (
    <>
      <main>
        <div className="hero-content">
          <div className="badge">
            <svg width="16" height="16" viewBox="0 0 16 16">
              <path
                d="M8 2 L10 6 L14 6 L11 9 L12 13 L8 10 L4 13 L5 9 L2 6 L6 6 Z"
                fill="currentColor"
              />
            </svg>
            <span>AI AUTOMATION FOR PROFESSIONAL DEVELOPERS</span>
          </div>

          <h1>
            <div className="logo-large">
              <svg width="100" height="100" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="#333"
                  stroke="#666"
                  strokeWidth="2"
                />
                <path
                  d="M30 40 L50 30 L70 40 L50 50 Z M50 50 L70 60 L50 70 L30 60 Z"
                  fill="white"
                />
              </svg>
            </div>
            <span className="brand-name">
              AI<span className="brand-ai">DEVS</span>
            </span>
          </h1>

          <p className="tagline">
            Custom AI solutions, built for the innovators of tomorrow
          </p>

          <div className="cta-buttons">
            <button
              className="btn-primary btn-large"
              onClick={handleGetStarted}
            >
              Get Started
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                style={{ marginLeft: "8px" }}
              >
                <path
                  d="M5 10 L15 10 M10 5 L15 10 L10 15"
                  stroke="currentColor"
                  strokeWidth="2"
                  fill="none"
                />
              </svg>
            </button>
            <button className="btn-secondary btn-large">
              See Our Services
            </button>
          </div>
        </div>

        <button className="btn-floating" onClick={handleGetStarted}>
          <svg width="20" height="20" viewBox="0 0 20 20">
            <rect x="3" y="3" width="6" height="6" fill="currentColor" />
            <rect x="11" y="3" width="6" height="6" fill="currentColor" />
            <rect x="3" y="11" width="6" height="6" fill="currentColor" />
            <rect x="11" y="11" width="6" height="6" fill="currentColor" />
          </svg>
          Get Started
        </button>
      </main>
    </>
  );
};

export default Hero;
