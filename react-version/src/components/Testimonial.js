import React from "react";

const Testimonial = () => {
  return (
    <section className="testimonial-section">
      <div className="testimonial-content">
        <p className="testimonial-text">
          "We turn <span className="highlight">your ideas</span> into full-stack
          websites, understand your vision, and{" "}
          <span className="highlight">use AI</span> to build exactly what you
          need. The best part? <span className="highlight">We iterate</span>,
          too."
        </p>
        <div className="testimonial-author">
          <img src="/uday.jpeg" alt="Developer" className="author-image" />
          <span className="author-name">Developer of AIDevs</span>
        </div>
      </div>
    </section>
  );
};

export default Testimonial;
