import React, { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const Features = () => {
  const sectionsRef = useRef([]);
  const visualsRef = useRef([]);
  const containerRef = useRef(null);
  const visualContainerRef = useRef(null);

  useEffect(() => {
    const sections = sectionsRef.current.filter(Boolean);
    const visuals = visualsRef.current.filter(Boolean);
    const visualContainer = visualContainerRef.current;

    if (sections.length === 0 || !visualContainer) return;

    // Clear any existing ScrollTriggers
    ScrollTrigger.getAll().forEach((trigger) => trigger.kill());

    // Calculate total scroll distance for all sections
    const totalHeight = sections.length * window.innerHeight;

    // Create timeline for each section
    sections.forEach((section, i) => {
      const visual = visuals[i];

      ScrollTrigger.create({
        trigger: section,
        start: "top center",
        end: "bottom center",
        onEnter: () => {
          // Fade out all visuals
          gsap.to(visuals, {
            opacity: 0,
            scale: 0.96,
            duration: 0.4,
            ease: "power2.out",
          });
          // Fade in current visual
          gsap.to(visual, {
            opacity: 1,
            scale: 1,
            duration: 0.4,
            ease: "power2.out",
          });
          // Update text opacity
          sections.forEach((s) => s.classList.remove("active"));
          section.classList.add("active");
        },
        onEnterBack: () => {
          // Fade out all visuals
          gsap.to(visuals, {
            opacity: 0,
            scale: 0.96,
            duration: 0.4,
            ease: "power2.out",
          });
          // Fade in current visual
          gsap.to(visual, {
            opacity: 1,
            scale: 1,
            duration: 0.4,
            ease: "power2.out",
          });
          // Update text opacity
          sections.forEach((s) => s.classList.remove("active"));
          section.classList.add("active");
        },
      });
    });

    // Pin the visual container - end pinning before reaching the last section's end
    ScrollTrigger.create({
      trigger: containerRef.current,
      start: "top top",
      end: () => `+=${totalHeight - window.innerHeight * 0.5}`,
      pin: visualContainer,
      pinSpacing: false,
    });

    // Initialize first visual
    gsap.set(visuals[0], { opacity: 1, scale: 1 });
    gsap.set(visuals.slice(1), { opacity: 0, scale: 0.96 });
    sections[0]?.classList.add("active");

    return () => {
      ScrollTrigger.getAll().forEach((trigger) => trigger.kill());
    };
  }, []);

  const features = [
    {
      title: "AI Agents Build Your Website",
      description:
        "Multiple specialized AI agents—frontend creators, backend engineers, test specialists, and an engineering lead—collaborate in real-time to build your complete website.",
    },
    {
      title: "Generate Multiple Options, Pick the Best",
      description:
        "Our AI creates multiple frontend designs and backend architectures. Review each version side-by-side, compare features, and select the one that fits your vision perfectly.",
    },
    {
      title: "Automated Testing & Validation",
      description:
        "Test engineer agents validate every component, check responsiveness, verify functionality, and ensure your code is production-ready before delivery.",
    },
    {
      title: "Download Production-Ready Files",
      description:
        "Get clean, organized frontend and backend code files. Fully commented, properly structured, and ready to deploy to any hosting platform.",
    },
  ];

  return (
    <section id="features" className="features-scroll-section">
      <div className="features-header">
        <div className="badge">
          <svg width="16" height="16" viewBox="0 0 16 16">
            <path
              d="M8 2 L10 6 L14 6 L11 9 L12 13 L8 10 L4 13 L5 9 L2 6 L6 6 Z"
              fill="currentColor"
            />
          </svg>
          <span>FEATURES</span>
        </div>
        <h2 className="features-main-title">All features in 1 tool</h2>
        <p className="features-main-subtitle">
          Discover features that simplify workflows & grow your business.
        </p>
      </div>

      <div className="scroll-features-container" ref={containerRef}>
        <div className="features-content">
          <div className="feature-text-sections">
            {features.map((feature, index) => (
              <div
                className="feature-section"
                key={index}
                ref={(el) => (sectionsRef.current[index] = el)}
              >
                <h3 className="feature-section-title">{feature.title}</h3>
                <p className="feature-section-description">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>

          <div className="feature-visual-container" ref={visualContainerRef}>
            {/* Visual 1: Terminal View */}
            <div
              className="feature-visual active"
              data-visual={0}
              ref={(el) => (visualsRef.current[0] = el)}
            >
              <div className="visual-content terminal-view">
                <div className="terminal-header">
                  <div className="terminal-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span className="terminal-title">AI Agents Workspace</span>
                </div>
                <div className="terminal-body">
                  <div className="agent-task">
                    <span className="agent-name">Frontend Agent:</span>
                    <div className="progress-bar">
                      <div className="progress" style={{ width: "75%" }}></div>
                    </div>
                    <span className="task-status">Building components...</span>
                  </div>
                  <div className="agent-task">
                    <span className="agent-name">Backend Agent:</span>
                    <div className="progress-bar">
                      <div className="progress" style={{ width: "60%" }}></div>
                    </div>
                    <span className="task-status">
                      Setting up API routes...
                    </span>
                  </div>
                  <div className="agent-task">
                    <span className="agent-name">Test Agent:</span>
                    <div className="progress-bar">
                      <div className="progress" style={{ width: "40%" }}></div>
                    </div>
                    <span className="task-status">Writing test cases...</span>
                  </div>
                  <div className="agent-task">
                    <span className="agent-name">Lead Agent:</span>
                    <div className="progress-bar">
                      <div className="progress" style={{ width: "85%" }}></div>
                    </div>
                    <span className="task-status">Coordinating tasks...</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Visual 2: Comparison View */}
            <div
              className="feature-visual"
              data-visual={1}
              ref={(el) => (visualsRef.current[1] = el)}
            >
              <div className="visual-content comparison-view">
                <div className="compare-side before">
                  <div className="compare-label">BEFORE</div>
                  <div className="metrics-list">
                    <div className="metric-item">
                      <div className="metric-name">Development Time</div>
                      <div className="metric-value">8 weeks</div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-name">Code Quality</div>
                      <div className="metric-value">Manual</div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-name">Testing</div>
                      <div className="metric-value">Limited</div>
                    </div>
                  </div>
                </div>
                <div className="compare-side after">
                  <div className="compare-label">AFTER</div>
                  <div className="metrics-list">
                    <div className="metric-item">
                      <div className="metric-name">Development Time</div>
                      <div className="metric-value">2 days</div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-name">Code Quality</div>
                      <div className="metric-value">AI-Optimized</div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-name">Testing</div>
                      <div className="metric-value">Complete</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Visual 3: Testing View */}
            <div
              className="feature-visual"
              data-visual={2}
              ref={(el) => (visualsRef.current[2] = el)}
            >
              <div className="visual-content testing-view">
                <div className="testing-header">
                  <span className="test-icon">✓</span> Test Results
                </div>
                <div className="test-results">
                  <div className="test-item passed">
                    <span className="test-check">✓</span>
                    <span className="test-name">Component Rendering</span>
                    <span className="test-time">125ms</span>
                  </div>
                  <div className="test-item passed">
                    <span className="test-check">✓</span>
                    <span className="test-name">API Integration</span>
                    <span className="test-time">89ms</span>
                  </div>
                  <div className="test-item passed">
                    <span className="test-check">✓</span>
                    <span className="test-name">Responsive Layout</span>
                    <span className="test-time">156ms</span>
                  </div>
                  <div className="test-item passed">
                    <span className="test-check">✓</span>
                    <span className="test-name">Database Connection</span>
                    <span className="test-time">203ms</span>
                  </div>
                </div>
                <div className="test-summary">All tests passed • 4/4</div>
              </div>
            </div>

            {/* Visual 4: Files View */}
            <div
              className="feature-visual"
              data-visual={3}
              ref={(el) => (visualsRef.current[3] = el)}
            >
              <div className="visual-content files-view">
                <div className="files-header">📁 Project Structure</div>
                <div className="file-tree">
                  <div className="file-item folder">📁 frontend/</div>
                  <div className="file-item file indent-1">📄 index.html</div>
                  <div className="file-item file indent-1">📄 styles.css</div>
                  <div className="file-item file indent-1">📄 app.js</div>
                  <div className="file-item folder">📁 backend/</div>
                  <div className="file-item file indent-1">📄 server.js</div>
                  <div className="file-item file indent-1">📄 routes.js</div>
                  <div className="file-item file indent-1">📄 database.js</div>
                  <div className="file-item folder">📁 tests/</div>
                </div>
                <button className="download-btn">⬇ Download All Files</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Features;
