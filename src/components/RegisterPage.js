import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import * as THREE from "three";
import "./RegisterPage.css";
import { useAuth } from "../auth/AuthContext";

const passwordChecks = (pw) => ({
  min_length: pw.length >= 8,
  has_letter: /[A-Za-z]/.test(pw),
  has_number: /\d/.test(pw),
  has_special: /[^A-Za-z0-9]/.test(pw),
});

const CHECK_LABELS = {
  min_length: "At least 8 characters",
  has_letter: "Contains a letter",
  has_number: "Contains a number",
  has_special: "Contains a special character",
};

const RegisterPage = () => {
  const navigate = useNavigate();
  const { register, status } = useAuth();
  const canvasRef = useRef(null);

  const [formData, setFormData] = useState({
    firstName: "",
    middleName: "",
    lastName: "",
    email: "",
    password: "",
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const validation = passwordChecks(formData.password);

  useEffect(() => {
    if (status === "authenticated") navigate("/projects", { replace: true });
  }, [status, navigate]);

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
    let frameId;
    const animate = () => {
      frameId = requestAnimationFrame(animate);

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
      cancelAnimationFrame(frameId);
      window.removeEventListener("resize", handleResize);
      renderer.dispose();
    };
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name] || errors.general) setErrors((prev) => ({ ...prev, [name]: "", general: "" }));
  };

  const validateForm = () => {
    const newErrors = {};
    if (formData.firstName.trim().length < 2) newErrors.firstName = "First name must be at least 2 characters";
    if (formData.lastName.trim().length < 2) newErrors.lastName = "Last name must be at least 2 characters";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(formData.email.trim())) newErrors.email = "Enter a valid email address";
    if (!Object.values(validation).every(Boolean)) newErrors.password = "Password does not meet the requirements";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    setIsSubmitting(true);
    try {
      await register({ ...formData, email: formData.email.trim() });
      navigate("/projects", { replace: true });
    } catch (error) {
      setErrors({ ...(error.data && error.data.fields ? error.data.fields : {}), general: error.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const field = (name, label, props = {}) => (
    <div className="form-group">
      <label htmlFor={name}>{label}</label>
      <input
        id={name}
        name={name}
        value={formData[name]}
        onChange={handleChange}
        className={errors[name] ? "error" : ""}
        aria-invalid={Boolean(errors[name])}
        aria-describedby={errors[name] ? `${name}-error` : undefined}
        {...props}
      />
      {errors[name] && <span className="error-text" id={`${name}-error`}>{errors[name]}</span>}
    </div>
  );

  return (
    <div className="register-page">
      <canvas ref={canvasRef} className="three-canvas" />
      <div className="register-container">
        <div className="register-card">
          <div className="register-header">
            <h1>Welcome to AIDevs</h1>
            <p>Create your account. No API keys needed — AI is included.</p>
          </div>
          <form onSubmit={handleSubmit} className="register-form" noValidate>
            {field("firstName", "First Name *", { type: "text", placeholder: "Jane", autoComplete: "given-name", required: true })}
            {field("middleName", "Middle Name", { type: "text", placeholder: "Optional", autoComplete: "additional-name" })}
            {field("lastName", "Last Name *", { type: "text", placeholder: "Doe", autoComplete: "family-name", required: true })}
            {field("email", "Email *", { type: "email", placeholder: "you@example.com", autoComplete: "email", required: true })}
            {field("password", "Password *", { type: "password", placeholder: "Create a strong password", autoComplete: "new-password", required: true })}
            {formData.password && (
              <div className="password-validation" aria-live="polite">
                {Object.entries(CHECK_LABELS).map(([key, label]) => (
                  <div key={key} className={`validation-item ${validation[key] ? "valid" : ""}`}>
                    {validation[key] ? "✓" : "○"} {label}
                  </div>
                ))}
              </div>
            )}
            {errors.general && <div className="error-message" role="alert">{errors.general}</div>}
            <p className="terms-note">By creating an account you agree to the <Link to="/legal/terms">Terms</Link> and
              {" "}<Link to="/legal/acceptable-use">Acceptable Use Policy</Link>, and acknowledge the <Link to="/legal/privacy">Privacy Policy</Link>.
              Your prompts and project content are processed by our AI provider (Groq).</p>
            <button type="submit" className="submit-button" disabled={isSubmitting}>
              {isSubmitting ? "Creating Account..." : "Create Account"}
            </button>
            <div className="login-link">
              Already have an account? <Link to="/login">Log in</Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
