import React, { useEffect } from "react";

const Services = () => {
  useEffect(() => {
    const serviceCards = document.querySelectorAll(".service-card");

    serviceCards.forEach((card, index) => {
      const icon = card.querySelector(".service-icon");
      if (!icon) return;

      card.addEventListener("mousemove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const deltaX = (x - centerX) / centerX;
        const deltaY = (y - centerY) / centerY;

        const moveX = deltaX * 12;
        const moveY = deltaY * 12;
        const rotate = deltaX * 3;

        icon.style.transform = `translate(${moveX}px, ${moveY}px) rotate(${rotate}deg)`;

        const tiltX = deltaY * 2;
        const tiltY = -deltaX * 2;
        card.style.transform = `translateY(-8px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
      });

      card.addEventListener("mouseleave", () => {
        icon.style.transform = "translate(0, 0) rotate(0deg)";
        card.style.transform = "translateY(0) rotateX(0deg) rotateY(0deg)";
      });

      let time = index * 1000;

      function animateIcon() {
        time += 16;
        const offsetX = Math.sin(time / 1500) * 2;
        const offsetY = Math.cos(time / 1800) * 2;
        const rotation = Math.sin(time / 2000) * 1.5;
        const scale = 1 + Math.sin(time / 2500) * 0.02;

        if (!card.matches(":hover")) {
          icon.style.transform = `translate(${offsetX}px, ${offsetY}px) rotate(${rotation}deg) scale(${scale})`;
        }

        requestAnimationFrame(animateIcon);
      }

      animateIcon();
    });
  }, []);

  const services = [
    {
      icon: (
        <>
          <polyline points="16 18 22 12 16 6"></polyline>
          <polyline points="8 6 2 12 8 18"></polyline>
          <line x1="12" y1="2" x2="12" y2="22"></line>
        </>
      ),
      title: "AI-Powered Full-Stack Development",
      description:
        "Describe your vision in plain English. Our multi-agent system generates complete frontend and backend code, comparing multiple options until you find the perfect fit.",
    },
    {
      icon: (
        <>
          <rect x="3" y="3" width="7" height="7" rx="1"></rect>
          <rect x="14" y="3" width="7" height="7" rx="1"></rect>
          <rect x="14" y="14" width="7" height="7" rx="1"></rect>
          <rect x="3" y="14" width="7" height="7" rx="1"></rect>
        </>
      ),
      title: "Compare & Choose Best Designs",
      description:
        "Review multiple AI-generated frontend designs side-by-side. Select your favorite, request modifications, and refine until it matches your exact vision.",
    },
    {
      icon: (
        <>
          <rect x="2" y="3" width="20" height="14" rx="2"></rect>
          <line x1="8" y1="21" x2="16" y2="21"></line>
          <line x1="12" y1="17" x2="12" y2="21"></line>
          <path d="M6 8h4M6 12h8"></path>
        </>
      ),
      title: "Smart Backend Engineering",
      description:
        "AI agents design optimal database schemas, API endpoints, and server logic tailored to your requirements. Choose from multiple backend architectures.",
    },
    {
      icon: (
        <>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          <polyline points="9 12 11 14 15 10"></polyline>
        </>
      ),
      title: "Test Engineer Validation",
      description:
        "Dedicated test agent validates functionality, checks responsiveness, verifies security, and ensures production-ready code quality.",
    },
    {
      icon: (
        <>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="12" y1="18" x2="12" y2="12"></line>
          <line x1="9" y1="15" x2="15" y2="15"></line>
        </>
      ),
      title: "AI Content Creation",
      description:
        "Generate captivating, high-quality content aligned with your brand voice. From landing page copy to product descriptions.",
    },
    {
      icon: (
        <>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </>
      ),
      title: "Production-Ready Code Export",
      description:
        "Get organized, commented, and deployment-ready frontend and backend files. Download complete project structure instantly.",
    },
  ];

  return (
    <section id="services" className="services-section">
      <div className="services-container">
        <div className="services-header">
          <div className="services-badge">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M12 1v6m0 6v6M5.6 5.6l4.2 4.2m4.2 4.2l4.2 4.2M1 12h6m6 0h6M5.6 18.4l4.2-4.2m4.2-4.2l4.2-4.2"></path>
            </svg>
            <span>SERVICES</span>
          </div>
          <h2 className="services-title">Our AI-Driven Services</h2>
          <p className="services-subtitle">
            Leverage AI features that boost performance to your business.
          </p>
        </div>

        <div className="services-grid" id="servicesGrid">
          {services.map((service, index) => (
            <div className="service-card" data-card={index} key={index}>
              <div className="service-card-content">
                <div className="service-icon">
                  <svg
                    width="48"
                    height="48"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    {service.icon}
                  </svg>
                </div>
                <h3 className="service-title">{service.title}</h3>
                <p className="service-description">{service.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Services;
