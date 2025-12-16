import React, { useEffect, useRef } from "react";
import * as THREE from "three";

// Water Texture Class - Tracks and renders ripples
class WaterTexture {
  constructor(options) {
    this.size = options.size || 512;
    this.radius = options.radius || 0.05;
    this.maxAge = options.maxAge || 100;
    this.speed = options.speed || 1;
    this.maxRipples = options.maxRipples || 10;

    // Create canvas for ripple tracking
    this.canvas = document.createElement("canvas");
    this.canvas.width = this.canvas.height = this.size;
    this.ctx = this.canvas.getContext("2d");

    // Initialize ripples array
    this.ripples = [];

    // Clear canvas
    this.clear();
  }

  clear() {
    this.ctx.fillStyle = "rgb(127, 127, 127)";
    this.ctx.fillRect(0, 0, this.size, this.size);
  }

  // Add a new ripple at the given position
  addPoint(x, y, momentum) {
    const point = {
      x: x,
      y: y,
      age: 0,
      radius: this.radius,
      momentum: momentum || 1,
    };

    this.ripples.push(point);

    if (this.ripples.length > this.maxRipples) {
      this.ripples.shift();
    }
  }

  update() {
    this.clear();

    this.ripples = this.ripples.filter((ripple) => {
      ripple.age += this.speed;

      if (ripple.age > this.maxAge) {
        return false;
      }

      this.drawRipple(ripple);
      return true;
    });
  }

  drawRipple(ripple) {
    const t = ripple.age / this.maxAge;
    const radius = ripple.radius * (1 + t * 12) * ripple.momentum;
    const alpha = Math.pow(1 - t, 1.5);

    const x = ripple.x * this.size;
    const y = ripple.y * this.size;
    const r = radius * this.size;

    for (let i = 0; i < 5; i++) {
      const offset = i * 0.16;
      const innerR = r * (0.7 + offset);
      const outerR = r * (1.0 + offset);

      const gradient = this.ctx.createRadialGradient(
        x,
        y,
        innerR,
        x,
        y,
        outerR
      );

      const brightness = 95 * alpha * Math.pow(1 - i * 0.18, 2);

      gradient.addColorStop(
        0,
        `rgba(${127 + brightness}, ${127 + brightness}, ${127 + brightness}, 1)`
      );
      gradient.addColorStop(
        0.3,
        `rgba(${127 + brightness * 0.6}, ${127 + brightness * 0.6}, ${
          127 + brightness * 0.6
        }, 1)`
      );
      gradient.addColorStop(
        0.6,
        `rgba(${127 - brightness * 0.4}, ${127 - brightness * 0.4}, ${
          127 - brightness * 0.4
        }, 1)`
      );
      gradient.addColorStop(1, "rgba(127, 127, 127, 0)");

      this.ctx.fillStyle = gradient;
      this.ctx.fillRect(0, 0, this.size, this.size);
    }
  }

  getTexture() {
    return this.canvas;
  }
}

const WaterCanvas = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;

    // Create scene
    const scene = new THREE.Scene();

    // Create camera
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -10, 10);
    camera.position.z = 5;

    // Create renderer
    const renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Create water texture
    const waterTexture = new WaterTexture({
      size: 512,
      radius: 0.06,
      maxAge: 140,
      speed: 0.35,
      maxRipples: 15,
    });

    // Create custom shader material
    const material = new THREE.ShaderMaterial({
      uniforms: {
        uTexture: { value: new THREE.CanvasTexture(waterTexture.getTexture()) },
        uTime: { value: 0 },
        uResolution: {
          value: new THREE.Vector2(window.innerWidth, window.innerHeight),
        },
      },
      vertexShader: `
        varying vec2 vUv;
        varying vec3 vPosition;
        void main() {
          vUv = uv;
          vPosition = position;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D uTexture;
        uniform float uTime;
        uniform vec2 uResolution;
        varying vec2 vUv;
        varying vec3 vPosition;
        
        void main() {
          vec2 uv = vUv;
          
          vec4 displacement = texture2D(uTexture, uv);
          vec2 distortion = (displacement.rg - 0.5) * 2.0;
          vec2 distortedUv = uv + distortion * 0.22;
          
          float dist = length(uv - 0.5);
          vec3 waterColor = vec3(0.95, 0.96, 0.97);
          vec3 color = waterColor + vec3(0.03) * (1.0 - dist);
          
          float rippleEffect = (displacement.r - 0.5) * 2.0;
          float rippleDepth = abs(rippleEffect);
          
          float shadow = rippleDepth * 0.35;
          color -= vec3(shadow);
          
          float wavePattern = 0.0;
          wavePattern += sin(distortedUv.x * 40.0 + uTime * 0.6) * 0.012;
          wavePattern += sin(distortedUv.y * 35.0 - uTime * 0.5) * 0.012;
          wavePattern += sin(distortedUv.x * 25.0 + distortedUv.y * 25.0 + uTime * 0.4) * 0.008;
          color += vec3(wavePattern);
          
          float fresnel = pow(1.0 - rippleDepth, 3.0);
          float specular = smoothstep(0.4, 0.8, rippleEffect) * 0.25;
          color += vec3(specular * fresnel);
          
          float caustics = sin(distortedUv.x * 50.0 + uTime) * sin(distortedUv.y * 50.0 - uTime * 0.7);
          caustics = max(0.0, caustics) * 0.08 * (1.0 - rippleDepth);
          color += vec3(caustics);
          
          float refraction = smoothstep(0.2, 0.5, rippleDepth) * 0.15;
          color += vec3(refraction * vec3(0.9, 0.95, 1.0));
          
          gl_FragColor = vec4(color, 1.0);
        }
      `,
    });

    // Create plane geometry
    const geometry = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.z = 0;
    scene.add(mesh);

    // Create 3D white spherical ball
    const ballSize = 0.35;
    const ballGeometry = new THREE.SphereGeometry(ballSize, 64, 64);

    const ballMaterial = new THREE.ShaderMaterial({
      transparent: false,
      uniforms: {
        uTime: { value: 0 },
      },
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vPosition;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          vPosition = position;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec3 vNormal;
        varying vec3 vPosition;
        uniform float uTime;
        
        void main() {
          vec3 lightDir = normalize(vec3(0.5, 1.2, 1.0));
          float diffuse = max(dot(vNormal, lightDir), 0.0);
          
          float gradient = (vPosition.y + 1.0) * 0.5;
          
          vec3 color = vec3(1.0, 1.0, 1.0);
          color *= 0.95 + diffuse * 0.4;
          color *= 0.85 + gradient * 0.5;
          
          float rim = 1.0 - max(dot(vNormal, vec3(0.0, 0.0, 1.0)), 0.0);
          rim = pow(rim, 2.0);
          color += rim * 0.35;
          
          gl_FragColor = vec4(color, 1.0);
        }
      `,
    });

    const ballMesh = new THREE.Mesh(ballGeometry, ballMaterial);
    ballMesh.position.z = -1.5;
    ballMesh.position.y = 0;

    // Add shadow
    const shadowGeometry = new THREE.SphereGeometry(ballSize * 1.25, 64, 64);
    const shadowMaterial = new THREE.MeshBasicMaterial({
      color: 0xa0a0a0,
      transparent: true,
      opacity: 0.5,
    });
    const ballShadow = new THREE.Mesh(shadowGeometry, shadowMaterial);
    ballShadow.position.copy(ballMesh.position);
    ballShadow.position.z -= 0.25;
    ballShadow.position.y -= 0.05;

    scene.add(ballShadow);
    scene.add(ballMesh);

    // Mouse tracking
    let mouse = { x: 0, y: 0 };
    let lastMouse = { x: 0, y: 0 };

    const onMouseMove = (event) => {
      mouse.x = event.clientX / window.innerWidth;
      mouse.y = 1 - event.clientY / window.innerHeight;

      const dx = mouse.x - lastMouse.x;
      const dy = mouse.y - lastMouse.y;
      const momentum = Math.min(Math.sqrt(dx * dx + dy * dy) * 10, 1.5);

      if (momentum > 0.008) {
        waterTexture.addPoint(mouse.x, mouse.y, momentum * 1.0);
      }

      lastMouse.x = mouse.x;
      lastMouse.y = mouse.y;
    };

    // Window resize handler
    const onWindowResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);

      if (mesh.material.uniforms) {
        mesh.material.uniforms.uResolution.value.set(
          window.innerWidth,
          window.innerHeight
        );
      }
    };

    // Central ball ripples
    let rippleTimer = 0;
    const centralBall = { x: 0.5, y: 0.5, floatOffset: 0 };

    const updateCentralBallRipples = () => {
      rippleTimer++;

      const floatAmplitude = 0.15;
      const floatSpeed = 0.008;
      const previousOffset = centralBall.floatOffset;
      centralBall.floatOffset =
        Math.sin(rippleTimer * floatSpeed) * floatAmplitude;

      if (ballMesh) {
        ballMesh.position.y = centralBall.floatOffset;

        if (ballMesh.material.uniforms) {
          ballMesh.material.uniforms.uTime.value = rippleTimer * 0.01;
        }

        if (ballShadow) {
          ballShadow.position.y = centralBall.floatOffset - 0.05;
        }
      }

      const isMovingDown = centralBall.floatOffset < previousOffset;
      const isTouchingWater =
        centralBall.floatOffset < -0.1 && centralBall.floatOffset > -0.15;

      if (isMovingDown && isTouchingWater && rippleTimer % 5 === 0) {
        const numRipples = 12;
        for (let i = 0; i < numRipples; i++) {
          const angle = (i / numRipples) * Math.PI * 2;
          const rippleRadius = 0.16;
          const rx = centralBall.x + Math.cos(angle) * rippleRadius;
          const ry = centralBall.y + Math.sin(angle) * rippleRadius;
          waterTexture.addPoint(rx, ry, 1.4);
        }
        waterTexture.addPoint(centralBall.x, centralBall.y, 2.0);

        for (let i = 0; i < 8; i++) {
          const angle = (i / 8) * Math.PI * 2 + Math.PI / 8;
          const rippleRadius = 0.12;
          const rx = centralBall.x + Math.cos(angle) * rippleRadius;
          const ry = centralBall.y + Math.sin(angle) * rippleRadius;
          waterTexture.addPoint(rx, ry, 1.0);
        }
      }

      const scale = 1.0 + Math.sin(rippleTimer * 0.015) * 0.012;
      if (ballMesh) {
        ballMesh.scale.set(scale, scale, scale);
      }
    };

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);

      updateCentralBallRipples();
      waterTexture.update();

      if (mesh.material.uniforms) {
        mesh.material.uniforms.uTexture.value.needsUpdate = true;
        mesh.material.uniforms.uTime.value += 0.016;
      }

      renderer.render(scene, camera);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("resize", onWindowResize);

    animate();

    // Cleanup
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", onWindowResize);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      ballGeometry.dispose();
      ballMaterial.dispose();
      shadowGeometry.dispose();
      shadowMaterial.dispose();
    };
  }, []);

  return <canvas ref={canvasRef} id="water-canvas" />;
};

export default WaterCanvas;
