import React, { useState, useEffect, useRef } from "react";
import * as THREE from "three";
import "./LoginModal.css";
import API_URL from "../config";

const LoginModal = ({ isOpen, onClose, onLoginSuccess }) => {
  const canvasRef = useRef(null);
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Three.js background
  useEffect(() => {
    if (!isOpen || !canvasRef.current) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, 400 / 500, 0.1, 1000);
    camera.position.z = 20;

    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      alpha: true,
      antialias: true,
    });
    renderer.setSize(400, 500);
    renderer.setClearColor(0x000000, 0);

    // Particles
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 300;
    const posArray = new Float32Array(particlesCount * 3);

    for (let i = 0; i < particlesCount * 3; i++) {
      posArray[i] = (Math.random() - 0.5) * 50;
    }

    particlesGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(posArray, 3)
    );

    const particlesMaterial = new THREE.PointsMaterial({
      size: 0.1,
      color: 0x00ffff,
      transparent: true,
      opacity: 0.6,
    });

    const particlesMesh = new THREE.Points(
      particlesGeometry,
      particlesMaterial
    );
    scene.add(particlesMesh);

    // Animated sphere
    const geometry = new THREE.IcosahedronGeometry(3, 0);
    const material = new THREE.MeshBasicMaterial({
      color: 0x00ffff,
      wireframe: true,
    });
    const icosahedron = new THREE.Mesh(geometry, material);
    scene.add(icosahedron);

    let animationId;
    const animate = () => {
      animationId = requestAnimationFrame(animate);

      particlesMesh.rotation.y += 0.002;
      icosahedron.rotation.x += 0.01;
      icosahedron.rotation.y += 0.01;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationId);
      renderer.dispose();
    };
  }, [isOpen]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.success) {
        // Store JWT token
        localStorage.setItem("aidevs_token", data.token);
        localStorage.setItem("aidevs_username", data.username);

        onLoginSuccess(data);
      } else {
        setError(data.error || "Login failed");
      }
    } catch (error) {
      setError("Network error. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="login-modal-overlay" onClick={onClose}>
      <div className="login-modal" onClick={(e) => e.stopPropagation()}>
        <canvas ref={canvasRef} className="login-canvas" />

        <div className="login-content">
          <button className="close-button" onClick={onClose}>
            ✕
          </button>

          <div className="login-header">
            <h2>Welcome Back</h2>
            <p>Login to continue building</p>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="firstname.lastname"
                required
                autoComplete="username"
              />
              <small>
                Use your auto-generated username (firstname.lastname)
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Enter your password"
                required
                autoComplete="current-password"
              />
            </div>

            {error && <div className="error-message">{error}</div>}

            <button
              type="submit"
              className="login-button"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Logging in..." : "Login"}
            </button>

            <div className="register-link">
              Don't have an account? <a href="/register">Register here</a>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginModal;
