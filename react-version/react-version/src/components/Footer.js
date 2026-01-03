import React from "react";

const Footer = () => {
  return (
    <footer id="contact" className="footer">
      <div className="footer-content">
        <div className="footer-brand">
          <div className="footer-logo">
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
          <h2 className="footer-brand-name">
            AI<span className="footer-brand-ai">DEVS</span>
          </h2>
          <p className="footer-tagline">
            Custom AI solutions, built for the innovators of tomorrow
          </p>
        </div>

        <nav className="footer-nav">
          <a href="#features">Features</a>
          <a href="#services">Services</a>
          <a href="#updates">Updates</a>
          <a href="#contact">Contact</a>
        </nav>

        <a
          href="https://www.linkedin.com/in/uday-easwar-22290a27a/"
          target="_blank"
          rel="noopener noreferrer"
          className="linkedin-icon"
          aria-label="LinkedIn Profile"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
          </svg>
        </a>

        <p className="copyright">aidevs@2026 developed by udayeaswar</p>
      </div>
    </footer>
  );
};

export default Footer;
