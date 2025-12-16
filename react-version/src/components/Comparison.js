import React, { useEffect } from "react";

const Comparison = () => {
  useEffect(() => {
    const cards = document.querySelectorAll(".comparison-card");

    const observerOptions = {
      threshold: 0.15,
      rootMargin: "0px 0px -50px 0px",
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (
          entry.isIntersecting &&
          !entry.target.classList.contains("slide-in")
        ) {
          setTimeout(() => {
            entry.target.classList.add("slide-in");
          }, 100);
        }
      });
    }, observerOptions);

    cards.forEach((card) => observer.observe(card));

    return () => {
      cards.forEach((card) => observer.unobserve(card));
    };
  }, []);

  const platformFeatures = [
    {
      title: "Interactive Design Approval",
      description:
        "Asks you to review colors, layouts, and styling choices—ensuring the design matches your vision",
    },
    {
      title: "Multiple Design Options",
      description:
        "Generates 3-5 different frontend designs for you to compare and choose from",
    },
    {
      title: "Iterative Refinement",
      description: "Continuously refines based on your feedback until perfect",
    },
    {
      title: "Automated Workflows",
      description:
        "Multi-agent system handles frontend, backend, and testing simultaneously",
    },
    {
      title: "Personalized AI-Driven Strategies",
      description: "Tailored to your specific business needs and requirements",
    },
    {
      title: "Data-Backed, Real-Time Insights",
      description: "Live collaboration tracking and progress updates",
    },
    {
      title: "Scalable AI Systems",
      description: "Backend architecture designed for growth and performance",
    },
    {
      title: "Production-Ready Code",
      description: "Download organized, commented, deployment-ready files",
    },
  ];

  const othersLimitations = [
    {
      title: "Manual Workflows",
      description: "You have to manually describe every detail repeatedly",
    },
    {
      title: "Generic, One-Size-Fits-All Solutions",
      description: "Cannot generate multiple design variations to choose from",
    },
    {
      title: "No Design Review Process",
      description:
        "Doesn't ask if you like the colors, fonts, or layout choices",
    },
    {
      title: "Decision-Making Based on Guesswork",
      description: "No iterative feedback loop for refinements",
    },
    {
      title: "Lacks Scalability",
      description:
        "Single-response format, no coordinated multi-agent workflow",
    },
    {
      title: "No Testing Validation",
      description: "You must manually test and debug everything",
    },
  ];

  return (
    <section className="comparison-section">
      <div className="comparison-container">
        <div className="comparison-header">
          <div className="comparison-badge">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 3v18M3 12h18M8 8l-4 4 4 4M16 8l4 4-4 4"></path>
            </svg>
            <span>COMPARISON</span>
          </div>
          <h2 className="comparison-title">Why Choose Our Platform</h2>
          <p className="comparison-subtitle">
            See how our AI outperforms generic tools with specialized website
            building capabilities
          </p>
        </div>

        <div className="comparison-cards-grid">
          {/* Left Card */}
          <div className="comparison-card left">
            <div className="card-header premium">
              <div className="platform-logo">
                <svg width="60" height="60" viewBox="0 0 100 100" fill="none">
                  <rect
                    width="100"
                    height="100"
                    rx="20"
                    fill="url(#platformGradient)"
                  />
                  <path
                    d="M30 50 L45 65 L70 35"
                    stroke="white"
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <defs>
                    <linearGradient
                      id="platformGradient"
                      x1="0"
                      y1="0"
                      x2="100"
                      y2="100"
                    >
                      <stop offset="0%" stopColor="#000000" />
                      <stop offset="100%" stopColor="#333333" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <h3 className="platform-name">AIDevs Platform</h3>
              <span className="platform-badge premium-badge">Premium</span>
            </div>

            <div className="features-list">
              {platformFeatures.map((feature, index) => (
                <div className="feature-item" key={index}>
                  <div className="feature-icon check">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" fill="#d1fae5" />
                      <path
                        d="M8 12 L11 15 L16 9"
                        stroke="#10b981"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                  <div className="feature-text">
                    <strong>{feature.title}</strong>
                    <p>{feature.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <button className="cta-button premium-cta">
              <span>Get Started</span>
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          {/* Right Card */}
          <div className="comparison-card right">
            <div className="card-header basic">
              <div className="platform-logo">
                <svg width="60" height="60" viewBox="0 0 100 100" fill="none">
                  <rect width="100" height="100" rx="20" fill="#e5e7eb" />
                  <circle
                    cx="50"
                    cy="50"
                    r="20"
                    stroke="#9ca3af"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    d="M50 35 L50 50 L60 60"
                    stroke="#9ca3af"
                    strokeWidth="4"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <h3 className="platform-name">Others (ChatGPT/Claude)</h3>
              <span className="platform-badge basic-badge">Basic</span>
            </div>

            <div className="features-list">
              {othersLimitations.map((feature, index) => (
                <div className="feature-item" key={index}>
                  <div className="feature-icon cross">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" fill="#fee2e2" />
                      <path
                        d="M15 9 L9 15 M9 9 L15 15"
                        stroke="#ef4444"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                  <div className="feature-text">
                    <strong>{feature.title}</strong>
                    <p>{feature.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Comparison;
