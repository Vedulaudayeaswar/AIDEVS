import React, { useState } from "react";

const FAQ = () => {
  const [activeIndex, setActiveIndex] = useState(null);

  const faqs = [
    {
      question: "How does your AI website builder work?",
      answer:
        "Simply describe your website requirements in plain English. Our multi-agent AI system generates multiple frontend designs and backend architectures. You review the options, select your favorites, and provide feedback. Our AI iteratively refines the code until you're completely satisfied, then delivers production-ready, downloadable files.",
    },
    {
      question: "What makes your platform different from ChatGPT or Claude?",
      answer:
        "Unlike generic AI chatbots, we specialize in full-stack website development. We generate multiple design variations and actively ask for your approval on colors, layouts, fonts, and styling choices. Our multi-agent system coordinates frontend creators, backend engineers, test specialists, and an engineering lead—all working together to build, validate, and deliver your complete website.",
    },
    {
      question: "Do I need coding experience to use your platform?",
      answer:
        "Absolutely not! Our platform is designed for everyone, regardless of technical background. Simply describe what you want in plain English, and our AI handles all the complexity. We explain every step in simple, actionable terms and provide fully commented, organized code that's ready to deploy.",
    },
    {
      question: "How long does it take to build a website?",
      answer:
        "Most projects are completed within 24-48 hours, depending on complexity. Our AI agents work simultaneously on frontend, backend, and testing, significantly reducing development time. Simple landing pages can be ready in hours, while complex full-stack applications with databases and APIs typically take 1-2 days.",
    },
    {
      question: "Can I customize the design after it's generated?",
      answer:
        "Yes! Our iterative refinement process allows unlimited revisions. If you don't like the colors, layouts, or any design element, simply tell us and we'll regenerate new options. You can request changes to fonts, spacing, components, features, or entire page sections until the design perfectly matches your vision.",
    },
    {
      question: "What technologies do you use for frontend and backend?",
      answer:
        "For frontend, we generate modern React, Vue.js, or vanilla HTML/CSS/JavaScript based on your preferences. Backend options include Node.js with Express, Python with Flask/Django, or serverless architectures using AWS Lambda. We also set up databases (PostgreSQL, MongoDB, MySQL) and implement secure API endpoints with authentication.",
    },
    {
      question: "Is my data safe when using your platform?",
      answer:
        "Absolutely. We take security seriously. All data is encrypted in transit and at rest. We don't store your project details longer than necessary, and you retain full ownership of all generated code and content. Our AI agents operate in isolated environments, and we comply with industry-standard security practices.",
    },
    {
      question: "Do I get the source code and files?",
      answer:
        "Yes! You receive complete, organized source code files for both frontend and backend. Everything is fully commented, properly structured, and deployment-ready. Files include HTML, CSS, JavaScript, server code, database schemas, API documentation, and deployment instructions—all downloadable as a ZIP package.",
    },
    {
      question: "Can your AI build e-commerce websites?",
      answer:
        "Definitely! We specialize in e-commerce platforms with product catalogs, shopping carts, secure payment gateway integration (Stripe, PayPal), inventory management, order tracking, and admin dashboards. Our AI can build complete online stores with user authentication, checkout flows, and real-time analytics.",
    },
    {
      question: "What kind of support do you provide after delivery?",
      answer:
        "After delivery, you receive comprehensive documentation explaining your codebase. If you encounter issues or need modifications, our engineering lead agent can assist with debugging and enhancements. We also provide deployment guides for popular hosting platforms like Vercel, Netlify, AWS, and Heroku.",
    },
  ];

  const toggleFAQ = (index) => {
    setActiveIndex(activeIndex === index ? null : index);
  };

  return (
    <section className="faq-section">
      <div className="faq-container">
        <div className="faq-header">
          <div className="faq-badge">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <span>FAQS</span>
          </div>
          <h2 className="faq-title">Questions? Answers!</h2>
          <p className="faq-subtitle">
            Find quick answers to the most common questions about our AI website
            builder
          </p>
        </div>

        <div className="faq-items">
          {faqs.map((faq, index) => (
            <div
              key={index}
              className={`faq-item ${activeIndex === index ? "active" : ""}`}
              onClick={() => toggleFAQ(index)}
            >
              <div className="faq-question">
                <span>{faq.question}</span>
                <svg
                  className="chevron"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>
              <div className="faq-answer">
                <p>{faq.answer}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="faq-contact">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
            <polyline points="22,6 12,13 2,6"></polyline>
          </svg>
          <p>
            Feel free to mail us for any enquiries:{" "}
            <a href="mailto:udayeaswar24@gmail.com">udayeaswar24@gmail.com</a>
          </p>
        </div>
      </div>
    </section>
  );
};

export default FAQ;
