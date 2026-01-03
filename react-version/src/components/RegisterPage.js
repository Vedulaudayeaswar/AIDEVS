import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import * as THREE from "three";
import "./RegisterPage.css";
import API_URL from "../config";

const RegisterPage = () => {
  const navigate = useNavigate();
  const canvasRef = useRef(null);

  const [formData, setFormData] = useState({
    firstName: "",
    middleName: "",
    lastName: "",
    password: "",
    apiKey: "",
  });

  const [validation, setValidation] = useState({
    first_uppercase: false,
    min_length: false,
    has_number: false,
    has_special: false,
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Three.js background animation
  useEffect(() => {
    if (!canvasRef.current) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    camera.position.z = 30;

    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      alpha: true,
      antialias: true,
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 1);

    // Create floating particles
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 800;
    const posArray = new Float32Array(particlesCount * 3);

    for (let i = 0; i < particlesCount * 3; i++) {
      posArray[i] = (Math.random() - 0.5) * 100;
    }

    particlesGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(posArray, 3)
    );

    const particlesMaterial = new THREE.PointsMaterial({
      size: 0.15,
      color: 0x00ffff,
      transparent: true,
      opacity: 0.8,
    });

    const particlesMesh = new THREE.Points(
      particlesGeometry,
      particlesMaterial
    );
    scene.add(particlesMesh);

    // Create geometric shapes
    const geometry = new THREE.TorusKnotGeometry(5, 1.5, 100, 16);
    const material = new THREE.MeshBasicMaterial({
      color: 0x00ffff,
      wireframe: true,
    });
    const torusKnot = new THREE.Mesh(geometry, material);
    torusKnot.position.set(-15, 0, -10);
    scene.add(torusKnot);

    const geometry2 = new THREE.OctahedronGeometry(4);
    const octahedron = new THREE.Mesh(geometry2, material);
    octahedron.position.set(15, 0, -10);
    scene.add(octahedron);

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);

      particlesMesh.rotation.y += 0.001;
      torusKnot.rotation.x += 0.005;
      torusKnot.rotation.y += 0.005;
      octahedron.rotation.x += 0.003;
      octahedron.rotation.y += 0.003;

      renderer.render(scene, camera);
    };

    animate();

    // Handle window resize
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      renderer.dispose();
    };
  }, []);

  // Real-time password validation
  useEffect(() => {
    if (formData.password) {
      setValidation({
        first_uppercase:
          formData.password.length > 0 &&
          formData.password[0] === formData.password[0].toUpperCase() &&
          formData.password[0] !== formData.password[0].toLowerCase(),
        min_length: formData.password.length >= 8,
        has_number: /\d/.test(formData.password),
        has_special: /[!@#$%^&*(),.?":{}|<>]/.test(formData.password),
      });
    }
  }, [formData.password]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error when user types
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.firstName || formData.firstName.trim().length < 2) {
      newErrors.firstName = "First name must be at least 2 characters";
    }

    if (!formData.lastName || formData.lastName.trim().length < 2) {
      newErrors.lastName = "Last name must be at least 2 characters";
    }

    if (
      !validation.first_uppercase ||
      !validation.min_length ||
      !validation.has_number ||
      !validation.has_special
    ) {
      newErrors.password = "Password does not meet requirements";
    }

    if (!formData.apiKey || !formData.apiKey.startsWith("gsk_")) {
      newErrors.apiKey = 'API key must start with "gsk_"';
    }

    if (formData.apiKey && formData.apiKey.length < 30) {
      newErrors.apiKey = "API key must be at least 30 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.success) {
        // Store JWT token
        localStorage.setItem("aidevs_token", data.token);
        localStorage.setItem("aidevs_username", data.username);

        // Redirect to chatbot
        navigate("/chatbot");
      } else {
        setErrors({ general: data.error || "Registration failed" });
      }
    } catch (error) {
      setErrors({ general: "Network error. Please try again." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const maskApiKey = (key) => {
    if (key.length < 10) return key;
    return `${key.slice(0, 3)}${"*".repeat(key.length - 7)}${key.slice(-4)}`;
  };

  return (
    <div className="register-page">
      <canvas ref={canvasRef} className="three-canvas" />

      <div className="register-container">
        <div className="register-card">
          <div className="register-header">
            <h1>Welcome to AIDevs</h1>
            <p>Create your account to start building amazing websites</p>
          </div>

          <form onSubmit={handleSubmit} className="register-form">
            <div className="form-group">
              <label htmlFor="firstName">First Name *</label>
              <input
                type="text"
                id="firstName"
                name="firstName"
                value={formData.firstName}
                onChange={handleChange}
                className={errors.firstName ? "error" : ""}
                placeholder="John"
                required
              />
              {errors.firstName && (
                <span className="error-text">{errors.firstName}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="middleName">Middle Name</label>
              <input
                type="text"
                id="middleName"
                name="middleName"
                value={formData.middleName}
                onChange={handleChange}
                placeholder="Optional"
              />
            </div>

            <div className="form-group">
              <label htmlFor="lastName">Last Name *</label>
              <input
                type="text"
                id="lastName"
                name="lastName"
                value={formData.lastName}
                onChange={handleChange}
                className={errors.lastName ? "error" : ""}
                placeholder="Doe"
                required
              />
              {errors.lastName && (
                <span className="error-text">{errors.lastName}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="password">Password *</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className={errors.password ? "error" : ""}
                placeholder="Enter strong password"
                required
              />
              {errors.password && (
                <span className="error-text">{errors.password}</span>
              )}

              {formData.password && (
                <div className="password-validation">
                  <div
                    className={`validation-item ${
                      validation.first_uppercase ? "valid" : ""
                    }`}
                  >
                    {validation.first_uppercase ? "✓" : "○"} First letter
                    uppercase
                  </div>
                  <div
                    className={`validation-item ${
                      validation.min_length ? "valid" : ""
                    }`}
                  >
                    {validation.min_length ? "✓" : "○"} Minimum 8 characters
                  </div>
                  <div
                    className={`validation-item ${
                      validation.has_number ? "valid" : ""
                    }`}
                  >
                    {validation.has_number ? "✓" : "○"} Contains number
                  </div>
                  <div
                    className={`validation-item ${
                      validation.has_special ? "valid" : ""
                    }`}
                  >
                    {validation.has_special ? "✓" : "○"} Contains special
                    character
                  </div>
                </div>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="apiKey">Groq API Key *</label>
              <input
                type="text"
                id="apiKey"
                name="apiKey"
                value={formData.apiKey}
                onChange={handleChange}
                className={errors.apiKey ? "error" : ""}
                placeholder="gsk_..."
                required
              />
              {errors.apiKey && (
                <span className="error-text">{errors.apiKey}</span>
              )}
              {formData.apiKey && formData.apiKey.length > 10 && (
                <div className="api-key-preview">
                  Preview: {maskApiKey(formData.apiKey)}
                </div>
              )}
              <small>
                Get your FREE API key from{" "}
                <a
                  href="https://console.groq.com/keys"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Groq Console
                </a>
              </small>
            </div>

            {errors.general && (
              <div className="error-message">{errors.general}</div>
            )}

            <button
              type="submit"
              className="submit-button"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Creating Account..." : "Create Account"}
            </button>

            <div className="login-link">
              Already have an account?{" "}
              <button type="button" onClick={() => navigate("/")}>
                Login
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
