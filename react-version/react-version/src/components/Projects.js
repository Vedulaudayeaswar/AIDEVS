import React, { useEffect, useState } from "react";

const Projects = () => {
  const [currentSlide, setCurrentSlide] = useState(0);

  const projects = [
    {
      number: "01",
      title: "Medicare — AI-Powered Medical Website",
      description:
        "We built a complete healthcare website with appointment booking, patient portal, telemedicine integration, and AI symptom checker. Clean interface with HIPAA-compliant backend architecture.",
      image: "/medicare.png",
      metrics: [
        { value: 45, label: "Faster appointment booking" },
        { value: 35, label: "Reduced patient wait time" },
      ],
    },
    {
      number: "02",
      title: "Stellaria — Smart E-Commerce Platform",
      description:
        "Created a full-stack e-commerce website with AI-powered product recommendations, dynamic inventory management, secure payment gateway integration, and real-time analytics dashboard.",
      image: "/stelleria.png",
      metrics: [
        { value: 52, label: "Increase in conversion rate" },
        { value: 28, label: "Higher average order value" },
      ],
    },
    {
      number: "03",
      title: "Workflow HR — Automated HR Management System",
      description:
        "Developed an AI-powered HR workflow automation platform handling employee onboarding, leave management, payroll integration, and automated compliance reporting with intelligent chatbot support.",
      image: "/workflowhrautomation.png",
      metrics: [
        { value: 60, label: "Saved admin time" },
        { value: 42, label: "Faster employee onboarding" },
      ],
    },
    {
      number: "04",
      title: "FitLife — AI Fitness & Wellness Platform",
      description:
        "Built a comprehensive fitness website with personalized workout plans, nutrition tracking, AI-powered form correction, progress analytics, and integrated video streaming for guided exercises.",
      image: "/fitness.png",
      metrics: [
        { value: 38, label: "Improved user engagement" },
        { value: 55, label: "Higher workout completion rate" },
      ],
    },
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % projects.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [projects.length]);

  useEffect(() => {
    const slide = document.querySelector(
      `.project-slide[data-slide="${currentSlide}"]`
    );
    if (slide) {
      const metricElements = slide.querySelectorAll(".metric-percentage");
      metricElements.forEach((element) => {
        const target = parseInt(element.getAttribute("data-target"));
        const duration = 2000;
        const startTime = performance.now();

        element.textContent = "0%";

        function updateCounter(currentTime) {
          const elapsed = currentTime - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const easeOutQuart = 1 - Math.pow(1 - progress, 4);
          const currentValue = Math.round(easeOutQuart * target);

          element.textContent = currentValue + "%";

          if (progress < 1) {
            requestAnimationFrame(updateCounter);
          } else {
            element.textContent = target + "%";
          }
        }

        requestAnimationFrame(updateCounter);
      });
    }
  }, [currentSlide]);

  return (
    <section className="projects-section">
      <div className="projects-container">
        <div className="projects-header">
          <div className="projects-badge">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <rect x="3" y="3" width="18" height="18" rx="2"></rect>
              <path d="M3 9h18M9 21V9"></path>
            </svg>
            <span>PROJECTS</span>
          </div>
          <h2 className="projects-title">Proven Impact & Results</h2>
          <p className="projects-subtitle">
            Explore real websites built by our AI system with measurable
            business impact
          </p>
        </div>

        <div className="project-tabs">
          {projects.map((_, index) => (
            <button
              key={index}
              className={`project-tab ${
                currentSlide === index ? "active" : ""
              }`}
              onClick={() => setCurrentSlide(index)}
            >
              PROJECT {index + 1}
            </button>
          ))}
        </div>

        <div className="projects-carousel">
          {projects.map((project, index) => (
            <div
              key={index}
              className={`project-slide ${
                currentSlide === index ? "active" : ""
              }`}
              data-slide={index}
            >
              <div className="project-content">
                <div className="project-image-container">
                  <img src={project.image} alt={project.title} />
                </div>

                <div className="project-info">
                  <div className="project-number">{project.number}</div>
                  <h3 className="project-title">{project.title}</h3>
                  <p className="project-description">{project.description}</p>

                  <div className="metrics-grid">
                    {project.metrics.map((metric, i) => (
                      <div className="metric-card" key={i}>
                        <div
                          className="metric-percentage"
                          data-target={metric.value}
                        >
                          0%
                        </div>
                        <div className="metric-label">{metric.label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Projects;
