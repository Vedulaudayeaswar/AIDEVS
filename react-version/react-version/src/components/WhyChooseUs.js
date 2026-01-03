import React, { useEffect } from "react";

const WhyChooseUs = () => {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const percentageValue =
              entry.target.querySelector(".percentage-value");
            if (
              percentageValue &&
              !percentageValue.classList.contains("animated")
            ) {
              percentageValue.classList.add("animated");

              function animatePercentage() {
                setTimeout(() => {
                  percentageValue.textContent = "20";
                }, 0);

                setTimeout(() => {
                  let count = 20;
                  const target = 80;
                  const duration = 900;
                  const steps = 30;
                  const increment = (target - count) / steps;
                  const stepDuration = duration / steps;

                  const counter = setInterval(() => {
                    count += increment;
                    if (count >= target) {
                      count = target;
                      clearInterval(counter);
                    }
                    percentageValue.textContent = Math.round(count);
                  }, stepDuration);
                }, 2400);

                setTimeout(() => {
                  percentageValue.textContent = "20";
                }, 5700);
              }

              animatePercentage();
              setInterval(animatePercentage, 6000);
            }
          }
        });
      },
      { threshold: 0.5 }
    );

    const cards = document.querySelectorAll(".feature-card");
    cards.forEach((card) => observer.observe(card));

    return () => {
      cards.forEach((card) => observer.unobserve(card));
    };
  }, []);

  return (
    <section className="why-choose-us">
      <div className="section-header">
        <div className="badge">
          <svg width="16" height="16" viewBox="0 0 16 16">
            <path
              d="M8 2 L10 6 L14 6 L11 9 L12 13 L8 10 L4 13 L5 9 L2 6 L6 6 Z"
              fill="currentColor"
            />
          </svg>
          <span>BENEFITS</span>
        </div>
        <h2 className="section-title">Why Choose Us</h2>
        <p className="section-subtitle">
          Try our website because: Partner with an AI agency delivering smart
          solutions.
        </p>
      </div>

      <div className="cards-container">
        {/* Card 1: Multi-Agent Architecture */}
        <div className="feature-card">
          <div className="card-icon">
            <div className="clock-animation">
              <div className="clock-face">
                <div className="clock-center"></div>
                <div className="clock-hand hour-hand"></div>
                <div className="clock-hand minute-hand"></div>
              </div>
            </div>
          </div>
          <div className="card-label">Multi-Agent Architecture</div>
          <h3 className="card-title">Multiple Specialists Working</h3>
          <p className="card-description">
            AI agents collaborate—frontend creators, backend engineers, testers,
            and a lead—all working together to build your perfect website.
          </p>
        </div>

        {/* Card 2: Iterative Refinement */}
        <div className="feature-card">
          <div className="card-icon">
            <div className="chart-animation">
              <div className="chart-label-before">BEFORE</div>
              <div className="chart-label-after">AFTER</div>
              <div className="chart-bars">
                <div className="chart-bar bar-1">
                  <div className="bar-fill"></div>
                </div>
                <div className="chart-bar bar-2">
                  <div className="bar-fill"></div>
                </div>
                <div className="chart-bar bar-3">
                  <div className="bar-fill"></div>
                </div>
                <div className="chart-bar bar-4">
                  <div className="bar-fill"></div>
                </div>
              </div>
              <div className="chart-percentage">
                <span className="percentage-value">20</span>
              </div>
              <div className="chart-metric">Automation</div>
            </div>
          </div>
          <div className="card-label">Iterative Refinement</div>
          <h3 className="card-title">Compare & Choose Best</h3>
          <p className="card-description">
            Generate multiple frontend and backend options. Review each version,
            select your favorite, and refine until it's exactly right.
          </p>
        </div>

        {/* Card 3: Real-Time Collaboration */}
        <div className="feature-card">
          <div className="card-icon">
            <div className="team-animation">
              <div className="code-icon-wrapper">
                <svg
                  width="48"
                  height="48"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z" />
                </svg>
              </div>
              <div className="team-icon icon-1">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                </svg>
              </div>
              <div className="team-icon icon-2">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                </svg>
              </div>
              <div className="team-icon icon-3">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                </svg>
              </div>
            </div>
          </div>
          <div className="card-label">Real-Time Collaboration</div>
          <h3 className="card-title">Live Team Sync</h3>
          <p className="card-description">
            Watch agents collaborate in real-time. Test engineer validates code
            while engineering lead coordinates all components instantly.
          </p>
        </div>
      </div>

      {/* Continuous Carousel */}
      <div className="carousel-wrapper">
        <div className="carousel-track">
          {[...Array(2)].map((_, setIndex) => (
            <React.Fragment key={setIndex}>
              <div className="carousel-item">
                AI-Powered Frontend Generation
              </div>
              <div className="carousel-item">Smart Backend Architecture</div>
              <div className="carousel-item">
                Automated Testing & Validation
              </div>
              <div className="carousel-item">Content Generation Ready</div>
              <div className="carousel-item">Downloadable Source Files</div>
              <div className="carousel-item">Engineering Lead Oversight</div>
              <div className="carousel-item">Multiple Design Iterations</div>
              <div className="carousel-item">User-Driven Refinement</div>
            </React.Fragment>
          ))}
        </div>
      </div>
    </section>
  );
};

export default WhyChooseUs;
