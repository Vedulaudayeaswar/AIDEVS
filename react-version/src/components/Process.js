import React from "react";

const Process = () => {
  const processCards = [
    {
      number: "01",
      title: "Tell Us What You Need",
      description:
        "Describe your website requirements in plain English. Our AI analyzes your needs and prepares multiple specialized agents—frontend creators, backend engineers, and testers—to start building your perfect website.",
      svg: "card1",
    },
    {
      number: "02",
      title: "Generate & Select Best Options",
      description:
        "AI agents create multiple frontend designs and backend architectures. Review them side-by-side, compare features and performance, then select your preferred design and technical stack.",
      svg: "card2",
    },
    {
      number: "03",
      title: "Receive Production-Ready Code",
      description:
        "Test engineer validates all functionality and responsiveness. Engineering lead ensures code quality. Download your complete, organized, and deployment-ready frontend and backend files with full documentation.",
      svg: "card3",
    },
  ];

  return (
    <section id="updates" className="process-section">
      <div className="process-container">
        <div className="process-header">
          <div className="process-badge">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <span>PROCESS</span>
          </div>
          <h2 className="process-title">Simple & Scalable</h2>
          <p className="process-subtitle">
            A transparent process of collaboration and feedback
          </p>
        </div>

        <div className="process-cards">
          {processCards.map((card, index) => (
            <div className="process-card" key={index}>
              <div className="card-number">{card.number}</div>
              <div className="card-pagination">
                {processCards.map((_, i) => (
                  <span
                    key={i}
                    className={`dot ${i === index ? "active" : ""}`}
                  ></span>
                ))}
              </div>
              <div className="card-image-container">
                {card.svg === "card1" && (
                  <svg
                    className="card-image-svg"
                    viewBox="0 0 800 450"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <defs>
                      <linearGradient
                        id="gradient1"
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="100%"
                      >
                        <stop
                          offset="0%"
                          style={{ stopColor: "#14b8a6", stopOpacity: 1 }}
                        />
                        <stop
                          offset="50%"
                          style={{ stopColor: "#06b6d4", stopOpacity: 1 }}
                        />
                        <stop
                          offset="100%"
                          style={{ stopColor: "#3b82f6", stopOpacity: 1 }}
                        />
                      </linearGradient>
                      <linearGradient
                        id="phoneGradient"
                        x1="0%"
                        y1="0%"
                        x2="0%"
                        y2="100%"
                      >
                        <stop
                          offset="0%"
                          style={{ stopColor: "#f0f0f0", stopOpacity: 1 }}
                        />
                        <stop
                          offset="100%"
                          style={{ stopColor: "#d0d0d0", stopOpacity: 1 }}
                        />
                      </linearGradient>
                    </defs>

                    <rect width="800" height="450" fill="#f3f4f6" />

                    <g transform="translate(300, 100)">
                      <rect
                        x="60"
                        y="20"
                        width="180"
                        height="320"
                        rx="20"
                        fill="url(#phoneGradient)"
                        stroke="#999"
                        strokeWidth="3"
                      />
                      <rect
                        x="70"
                        y="35"
                        width="160"
                        height="290"
                        rx="10"
                        fill="url(#gradient1)"
                      />

                      <rect
                        x="120"
                        y="30"
                        width="60"
                        height="8"
                        rx="4"
                        fill="#333"
                      />

                      <rect
                        x="90"
                        y="80"
                        width="120"
                        height="30"
                        rx="15"
                        fill="rgba(255,255,255,0.3)"
                      />
                      <rect
                        x="100"
                        y="120"
                        width="100"
                        height="30"
                        rx="15"
                        fill="rgba(255,255,255,0.4)"
                      />
                      <rect
                        x="110"
                        y="160"
                        width="110"
                        height="30"
                        rx="15"
                        fill="rgba(255,255,255,0.3)"
                      />

                      <circle
                        cx="120"
                        cy="220"
                        r="4"
                        fill="rgba(255,255,255,0.6)"
                      >
                        <animate
                          attributeName="opacity"
                          values="0.3;1;0.3"
                          dur="1.5s"
                          repeatCount="indefinite"
                        />
                      </circle>
                      <circle
                        cx="135"
                        cy="220"
                        r="4"
                        fill="rgba(255,255,255,0.6)"
                      >
                        <animate
                          attributeName="opacity"
                          values="0.3;1;0.3"
                          dur="1.5s"
                          begin="0.2s"
                          repeatCount="indefinite"
                        />
                      </circle>
                      <circle
                        cx="150"
                        cy="220"
                        r="4"
                        fill="rgba(255,255,255,0.6)"
                      >
                        <animate
                          attributeName="opacity"
                          values="0.3;1;0.3"
                          dur="1.5s"
                          begin="0.4s"
                          repeatCount="indefinite"
                        />
                      </circle>

                      <ellipse
                        cx="160"
                        cy="320"
                        rx="80"
                        ry="60"
                        fill="#fcd9bd"
                        stroke="#e0b59a"
                        strokeWidth="2"
                      />
                      <path
                        d="M 100 300 Q 90 320 100 340"
                        fill="#fcd9bd"
                        stroke="#e0b59a"
                        strokeWidth="2"
                      />
                    </g>

                    <circle
                      cx="100"
                      cy="100"
                      r="30"
                      fill="rgba(74, 222, 128, 0.2)"
                      opacity="0.6"
                    >
                      <animate
                        attributeName="cy"
                        values="100;90;100"
                        dur="3s"
                        repeatCount="indefinite"
                      />
                    </circle>
                    <rect
                      x="650"
                      y="80"
                      width="60"
                      height="60"
                      rx="10"
                      fill="rgba(59, 130, 246, 0.2)"
                      opacity="0.6"
                    >
                      <animate
                        attributeName="y"
                        values="80;70;80"
                        dur="4s"
                        repeatCount="indefinite"
                      />
                    </rect>
                  </svg>
                )}

                {card.svg === "card2" && (
                  <svg
                    className="card-image-svg"
                    viewBox="0 0 800 450"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <defs>
                      <linearGradient
                        id="techGradient"
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="100%"
                      >
                        <stop
                          offset="0%"
                          style={{ stopColor: "#1a1a1a", stopOpacity: 1 }}
                        />
                        <stop
                          offset="100%"
                          style={{ stopColor: "#2d2d2d", stopOpacity: 1 }}
                        />
                      </linearGradient>
                      <radialGradient id="glowRed" cx="50%" cy="50%" r="50%">
                        <stop
                          offset="0%"
                          style={{ stopColor: "#ef4444", stopOpacity: 1 }}
                        />
                        <stop
                          offset="100%"
                          style={{ stopColor: "#ef4444", stopOpacity: 0 }}
                        />
                      </radialGradient>
                    </defs>

                    <rect width="800" height="450" fill="#0a0a0a" />

                    <g transform="translate(50, 60)">
                      <rect
                        x="0"
                        y="0"
                        width="200"
                        height="300"
                        rx="12"
                        fill="url(#techGradient)"
                        stroke="#444"
                        strokeWidth="2"
                      />
                      <rect
                        x="10"
                        y="10"
                        width="180"
                        height="280"
                        rx="8"
                        fill="#1a1a1a"
                      />

                      <rect
                        x="20"
                        y="25"
                        width="100"
                        height="8"
                        rx="4"
                        fill="#4ade80"
                        opacity="0.6"
                      />
                      <rect
                        x="20"
                        y="45"
                        width="140"
                        height="8"
                        rx="4"
                        fill="#60a5fa"
                        opacity="0.6"
                      />
                      <rect
                        x="30"
                        y="65"
                        width="120"
                        height="8"
                        rx="4"
                        fill="#f59e0b"
                        opacity="0.6"
                      />
                      <rect
                        x="30"
                        y="85"
                        width="90"
                        height="8"
                        rx="4"
                        fill="#a78bfa"
                        opacity="0.6"
                      />
                      <rect
                        x="20"
                        y="105"
                        width="130"
                        height="8"
                        rx="4"
                        fill="#4ade80"
                        opacity="0.6"
                      />

                      <rect
                        x="20"
                        y="140"
                        width="30"
                        height="80"
                        rx="4"
                        fill="#4ade80"
                        opacity="0.4"
                      />
                      <rect
                        x="60"
                        y="180"
                        width="30"
                        height="40"
                        rx="4"
                        fill="#60a5fa"
                        opacity="0.4"
                      />
                      <rect
                        x="100"
                        y="160"
                        width="30"
                        height="60"
                        rx="4"
                        fill="#f59e0b"
                        opacity="0.4"
                      />
                      <rect
                        x="140"
                        y="170"
                        width="30"
                        height="50"
                        rx="4"
                        fill="#ec4899"
                        opacity="0.4"
                      />
                    </g>

                    <g transform="translate(300, 60)">
                      <rect
                        x="0"
                        y="0"
                        width="200"
                        height="300"
                        rx="12"
                        fill="url(#techGradient)"
                        stroke="#444"
                        strokeWidth="2"
                      />
                      <rect
                        x="10"
                        y="10"
                        width="180"
                        height="280"
                        rx="8"
                        fill="#1a1a1a"
                      />

                      <circle
                        cx="100"
                        cy="80"
                        r="40"
                        fill="#3b82f6"
                        opacity="0.3"
                      />
                      <rect
                        x="30"
                        y="140"
                        width="140"
                        height="12"
                        rx="6"
                        fill="#8b5cf6"
                        opacity="0.5"
                      />
                      <rect
                        x="30"
                        y="165"
                        width="140"
                        height="12"
                        rx="6"
                        fill="#ec4899"
                        opacity="0.5"
                      />
                      <rect
                        x="30"
                        y="190"
                        width="100"
                        height="12"
                        rx="6"
                        fill="#14b8a6"
                        opacity="0.5"
                      />

                      <circle cx="170" cy="30" r="15" fill="#4ade80" />
                      <path
                        d="M 163 30 L 168 35 L 177 25"
                        stroke="#fff"
                        strokeWidth="2"
                        fill="none"
                      />
                    </g>

                    <g transform="translate(550, 60)">
                      <rect
                        x="0"
                        y="0"
                        width="200"
                        height="300"
                        rx="12"
                        fill="url(#techGradient)"
                        stroke="#444"
                        strokeWidth="2"
                      />
                      <rect
                        x="10"
                        y="10"
                        width="180"
                        height="280"
                        rx="8"
                        fill="#1a1a1a"
                      />

                      <rect
                        x="25"
                        y="30"
                        width="60"
                        height="60"
                        rx="8"
                        fill="#6366f1"
                        opacity="0.4"
                      />
                      <rect
                        x="95"
                        y="30"
                        width="60"
                        height="60"
                        rx="8"
                        fill="#ec4899"
                        opacity="0.4"
                      />
                      <rect
                        x="25"
                        y="100"
                        width="60"
                        height="60"
                        rx="8"
                        fill="#f59e0b"
                        opacity="0.4"
                      />
                      <rect
                        x="95"
                        y="100"
                        width="60"
                        height="60"
                        rx="8"
                        fill="#14b8a6"
                        opacity="0.4"
                      />

                      <rect
                        x="25"
                        y="180"
                        width="130"
                        height="8"
                        rx="4"
                        fill="#888"
                        opacity="0.3"
                      />
                      <rect
                        x="25"
                        y="200"
                        width="100"
                        height="8"
                        rx="4"
                        fill="#888"
                        opacity="0.3"
                      />
                      <rect
                        x="25"
                        y="220"
                        width="110"
                        height="8"
                        rx="4"
                        fill="#888"
                        opacity="0.3"
                      />
                    </g>

                    <circle
                      cx="400"
                      cy="380"
                      r="60"
                      fill="url(#glowRed)"
                      opacity="0.4"
                    >
                      <animate
                        attributeName="opacity"
                        values="0.2;0.5;0.2"
                        dur="2s"
                        repeatCount="indefinite"
                      />
                    </circle>

                    <g transform="translate(350, 320)">
                      <rect
                        x="0"
                        y="0"
                        width="100"
                        height="15"
                        rx="7"
                        fill="#444"
                        stroke="#666"
                        strokeWidth="1"
                      />
                      <circle cx="85" cy="7.5" r="12" fill="#ef4444">
                        <animate
                          attributeName="opacity"
                          values="0.5;1;0.5"
                          dur="1.5s"
                          repeatCount="indefinite"
                        />
                      </circle>
                    </g>
                  </svg>
                )}

                {card.svg === "card3" && (
                  <svg
                    className="card-image-svg"
                    viewBox="0 0 800 450"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <defs>
                      <linearGradient
                        id="dashGradient"
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="100%"
                      >
                        <stop
                          offset="0%"
                          style={{ stopColor: "#0f172a", stopOpacity: 1 }}
                        />
                        <stop
                          offset="100%"
                          style={{ stopColor: "#1e293b", stopOpacity: 1 }}
                        />
                      </linearGradient>
                      <filter id="glow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                        <feMerge>
                          <feMergeNode in="coloredBlur" />
                          <feMergeNode in="SourceGraphic" />
                        </feMerge>
                      </filter>
                    </defs>

                    <rect width="800" height="450" fill="url(#dashGradient)" />

                    <g transform="translate(100, 50)">
                      <rect
                        x="0"
                        y="0"
                        width="600"
                        height="350"
                        rx="16"
                        fill="#0a0a0a"
                        stroke="#333"
                        strokeWidth="2"
                      />
                      <rect
                        x="8"
                        y="8"
                        width="584"
                        height="334"
                        rx="12"
                        fill="#0f1419"
                      />

                      <rect
                        x="25"
                        y="25"
                        width="550"
                        height="60"
                        rx="12"
                        fill="#1a1f2e"
                        opacity="0.8"
                      />

                      <g transform="translate(40, 35)">
                        <text
                          x="0"
                          y="15"
                          fill="#888"
                          fontSize="12"
                          fontFamily="Arial"
                        >
                          Tests Passed
                        </text>
                        <text
                          x="0"
                          y="38"
                          fill="#4ade80"
                          fontSize="24"
                          fontWeight="bold"
                          filter="url(#glow)"
                        >
                          100%
                        </text>
                      </g>

                      <g transform="translate(200, 35)">
                        <text
                          x="0"
                          y="15"
                          fill="#888"
                          fontSize="12"
                          fontFamily="Arial"
                        >
                          Code Quality
                        </text>
                        <text
                          x="0"
                          y="38"
                          fill="#60a5fa"
                          fontSize="24"
                          fontWeight="bold"
                          filter="url(#glow)"
                        >
                          A+
                        </text>
                      </g>

                      <g transform="translate(350, 35)">
                        <text
                          x="0"
                          y="15"
                          fill="#888"
                          fontSize="12"
                          fontFamily="Arial"
                        >
                          Build Time
                        </text>
                        <text
                          x="0"
                          y="38"
                          fill="#f59e0b"
                          fontSize="24"
                          fontWeight="bold"
                          filter="url(#glow)"
                        >
                          2.3s
                        </text>
                      </g>

                      <g transform="translate(500, 35)">
                        <circle
                          cx="15"
                          cy="25"
                          r="15"
                          fill="#4ade80"
                          opacity="0.2"
                        />
                        <path
                          d="M 10 25 L 13 28 L 20 20"
                          stroke="#4ade80"
                          strokeWidth="2"
                          fill="none"
                          filter="url(#glow)"
                        />
                      </g>

                      <g transform="translate(25, 110)">
                        <rect
                          x="0"
                          y="0"
                          width="250"
                          height="200"
                          rx="10"
                          fill="#1a1f2e"
                          opacity="0.6"
                        />

                        <g transform="translate(15, 20)">
                          <circle cx="8" cy="8" r="6" fill="#4ade80" />
                          <path
                            d="M 5 8 L 7 10 L 11 6"
                            stroke="#0a0a0a"
                            strokeWidth="1.5"
                            fill="none"
                          />
                          <text
                            x="25"
                            y="12"
                            fill="#e0e0e0"
                            fontSize="12"
                            fontFamily="monospace"
                          >
                            index.html
                          </text>
                        </g>

                        <g transform="translate(15, 50)">
                          <circle cx="8" cy="8" r="6" fill="#4ade80" />
                          <path
                            d="M 5 8 L 7 10 L 11 6"
                            stroke="#0a0a0a"
                            strokeWidth="1.5"
                            fill="none"
                          />
                          <text
                            x="25"
                            y="12"
                            fill="#e0e0e0"
                            fontSize="12"
                            fontFamily="monospace"
                          >
                            styles.css
                          </text>
                        </g>

                        <g transform="translate(15, 80)">
                          <circle cx="8" cy="8" r="6" fill="#4ade80" />
                          <path
                            d="M 5 8 L 7 10 L 11 6"
                            stroke="#0a0a0a"
                            strokeWidth="1.5"
                            fill="none"
                          />
                          <text
                            x="25"
                            y="12"
                            fill="#e0e0e0"
                            fontSize="12"
                            fontFamily="monospace"
                          >
                            script.js
                          </text>
                        </g>

                        <g transform="translate(15, 110)">
                          <circle cx="8" cy="8" r="6" fill="#4ade80" />
                          <path
                            d="M 5 8 L 7 10 L 11 6"
                            stroke="#0a0a0a"
                            strokeWidth="1.5"
                            fill="none"
                          />
                          <text
                            x="25"
                            y="12"
                            fill="#e0e0e0"
                            fontSize="12"
                            fontFamily="monospace"
                          >
                            api/server.js
                          </text>
                        </g>

                        <g transform="translate(15, 140)">
                          <circle cx="8" cy="8" r="6" fill="#4ade80" />
                          <path
                            d="M 5 8 L 7 10 L 11 6"
                            stroke="#0a0a0a"
                            strokeWidth="1.5"
                            fill="none"
                          />
                          <text
                            x="25"
                            y="12"
                            fill="#e0e0e0"
                            fontSize="12"
                            fontFamily="monospace"
                          >
                            README.md
                          </text>
                        </g>
                      </g>

                      <g transform="translate(300, 110)">
                        <rect
                          x="0"
                          y="0"
                          width="275"
                          height="200"
                          rx="10"
                          fill="#1a1f2e"
                          opacity="0.6"
                        />

                        <text
                          x="15"
                          y="25"
                          fill="#4ade80"
                          fontSize="11"
                          fontFamily="monospace"
                        >
                          $ npm run build
                        </text>
                        <text
                          x="15"
                          y="45"
                          fill="#888"
                          fontSize="10"
                          fontFamily="monospace"
                        >
                          ✓ Compiled successfully
                        </text>
                        <text
                          x="15"
                          y="60"
                          fill="#888"
                          fontSize="10"
                          fontFamily="monospace"
                        >
                          ✓ Optimized bundle
                        </text>
                        <text
                          x="15"
                          y="75"
                          fill="#888"
                          fontSize="10"
                          fontFamily="monospace"
                        >
                          ✓ Generated files
                        </text>

                        <g transform="translate(120, 110)">
                          <circle
                            cx="0"
                            cy="0"
                            r="35"
                            fill="#4ade80"
                            opacity="0.2"
                          >
                            <animate
                              attributeName="r"
                              values="35;38;35"
                              dur="2s"
                              repeatCount="indefinite"
                            />
                          </circle>
                          <path
                            d="M -10 -8 L 10 -8 M 0 -8 L 0 8 M -6 2 L 0 8 L 6 2"
                            stroke="#4ade80"
                            strokeWidth="2.5"
                            fill="none"
                            strokeLinecap="round"
                            filter="url(#glow)"
                          />
                          <rect
                            x="-12"
                            y="10"
                            width="24"
                            height="3"
                            rx="1.5"
                            fill="#4ade80"
                            filter="url(#glow)"
                          />
                        </g>
                      </g>
                    </g>

                    <circle cx="50" cy="100" r="3" fill="#4ade80" opacity="0.4">
                      <animate
                        attributeName="cy"
                        values="100;80;100"
                        dur="3s"
                        repeatCount="indefinite"
                      />
                    </circle>
                    <circle
                      cx="750"
                      cy="350"
                      r="4"
                      fill="#60a5fa"
                      opacity="0.4"
                    >
                      <animate
                        attributeName="cy"
                        values="350;330;350"
                        dur="4s"
                        repeatCount="indefinite"
                      />
                    </circle>
                  </svg>
                )}
              </div>
              <h3 className="card-title">{card.title}</h3>
              <p className="card-description">{card.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Process;
