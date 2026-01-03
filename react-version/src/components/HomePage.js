import React, { useEffect } from "react";
import "./HomePage.css";
import WaterCanvas from "./WaterCanvas";
import SphereBall from "./SphereBall";
import Header from "./Header";
import Hero from "./Hero";
import Testimonial from "./Testimonial";
import WhyChooseUs from "./WhyChooseUs";
import Services from "./Services";
import Process from "./Process";
import Features from "./Features";
import Projects from "./Projects";
import Comparison from "./Comparison";
import FAQ from "./FAQ";
import Footer from "./Footer";

function HomePage() {
  useEffect(() => {
    // Handle header transparency on scroll
    const handleScroll = () => {
      const header = document.querySelector("header");
      const scrollPosition = window.scrollY;
      const viewportHeight = window.innerHeight;

      if (scrollPosition > viewportHeight * 0.5) {
        header?.classList.add("transparent");
      } else {
        header?.classList.remove("transparent");
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="HomePage">
      <WaterCanvas />
      <SphereBall />
      <Header />
      <Hero />
      <Testimonial />
      <WhyChooseUs />
      <Services />
      <Process />
      <Features />
      <Projects />
      <Comparison />
      <FAQ />
      <Footer />
    </div>
  );
}

export default HomePage;
