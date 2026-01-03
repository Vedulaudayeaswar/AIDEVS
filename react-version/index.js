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
    // Normalize coordinates to 0-1 range
    const point = {
      x: x,
      y: y,
      age: 0,
      radius: this.radius,
      momentum: momentum || 1,
    };

    this.ripples.push(point);

    // Remove oldest ripple if we have too many
    if (this.ripples.length > this.maxRipples) {
      this.ripples.shift();
    }
  }

  // Update all ripples
  update() {
    // Clear with neutral gray (127, 127, 127 = no displacement)
    this.clear();

    // Update and draw each ripple
    this.ripples = this.ripples.filter((ripple) => {
      ripple.age += this.speed;

      // Remove ripple if too old
      if (ripple.age > this.maxAge) {
        return false;
      }

      // Draw ripple
      this.drawRipple(ripple);
      return true;
    });
  }

  // Draw a single ripple - realistic concentric circles with proper physics
  drawRipple(ripple) {
    const t = ripple.age / this.maxAge;
    const radius = ripple.radius * (1 + t * 12) * ripple.momentum;
    const alpha = Math.pow(1 - t, 1.5); // Smoother fade using power curve

    // Convert normalized coordinates to canvas coordinates
    const x = ripple.x * this.size;
    const y = ripple.y * this.size;
    const r = radius * this.size;

    // Draw multiple concentric circles for realistic wave propagation
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

      // Create realistic contrast with physics-based brightness
      const brightness = 95 * alpha * Math.pow(1 - i * 0.18, 2);

      // Wave peak (bright)
      gradient.addColorStop(
        0,
        `rgba(${127 + brightness}, ${127 + brightness}, ${127 + brightness}, 1)`
      );
      // Wave crest
      gradient.addColorStop(
        0.3,
        `rgba(${127 + brightness * 0.6}, ${127 + brightness * 0.6}, ${
          127 + brightness * 0.6
        }, 1)`
      );
      // Wave trough (dark)
      gradient.addColorStop(
        0.6,
        `rgba(${127 - brightness * 0.4}, ${127 - brightness * 0.4}, ${
          127 - brightness * 0.4
        }, 1)`
      );
      // Fade out
      gradient.addColorStop(1, "rgba(127, 127, 127, 0)");

      // Draw the ripple ring
      this.ctx.fillStyle = gradient;
      this.ctx.fillRect(0, 0, this.size, this.size);
    }
  }

  // Get the canvas as a texture
  getTexture() {
    return this.canvas;
  }
}

// Three.js Scene Setup
let scene, camera, renderer, mesh, waterTexture, ballMesh;
let mouse = { x: 0, y: 0 };
let lastMouse = { x: 0, y: 0 };
let centralBall = {
  x: 0.5,
  y: 0.5,
  size: 0.15, // Larger ball
  floatOffset: 0,
};

function init() {
  const canvas = document.getElementById("water-canvas");

  // Create scene
  scene = new THREE.Scene();

  // Create camera with perspective for 3D effect
  camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -10, 10);
  camera.position.z = 5;

  // Create renderer
  renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: true,
    alpha: true,
  });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(window.devicePixelRatio);

  // Create water texture with realistic ripple parameters
  waterTexture = new WaterTexture({
    size: 512,
    radius: 0.06, // Larger for more visible ripples
    maxAge: 140, // Longer lasting for smoother fade
    speed: 0.35, // Slower for realistic water
    maxRipples: 15, // More concurrent ripples
  });

  // Create custom shader material with realistic water effects
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
                
                // Sample the displacement texture
                vec4 displacement = texture2D(uTexture, uv);
                
                // Convert from 0-1 to -1 to 1 range
                vec2 distortion = (displacement.rg - 0.5) * 2.0;
                
                // Apply realistic water displacement
                vec2 distortedUv = uv + distortion * 0.22;
                
                // Create realistic water surface gradient
                float dist = length(uv - 0.5);
                vec3 waterColor = vec3(0.95, 0.96, 0.97); // Soft water tint
                vec3 color = waterColor + vec3(0.03) * (1.0 - dist);
                
                // Realistic ripple effect with depth
                float rippleEffect = (displacement.r - 0.5) * 2.0;
                float rippleDepth = abs(rippleEffect);
                
                // Create shadows in ripple troughs (darker areas)
                float shadow = rippleDepth * 0.35;
                color -= vec3(shadow);
                
                // Add realistic wave patterns with multiple frequencies
                float wavePattern = 0.0;
                wavePattern += sin(distortedUv.x * 40.0 + uTime * 0.6) * 0.012;
                wavePattern += sin(distortedUv.y * 35.0 - uTime * 0.5) * 0.012;
                wavePattern += sin(distortedUv.x * 25.0 + distortedUv.y * 25.0 + uTime * 0.4) * 0.008;
                color += vec3(wavePattern);
                
                // Add realistic specular highlights on wave peaks
                float fresnel = pow(1.0 - rippleDepth, 3.0);
                float specular = smoothstep(0.4, 0.8, rippleEffect) * 0.25;
                color += vec3(specular * fresnel);
                
                // Add subtle caustics effect
                float caustics = sin(distortedUv.x * 50.0 + uTime) * sin(distortedUv.y * 50.0 - uTime * 0.7);
                caustics = max(0.0, caustics) * 0.08 * (1.0 - rippleDepth);
                color += vec3(caustics);
                
                // Add refraction effect at ripple edges
                float refraction = smoothstep(0.2, 0.5, rippleDepth) * 0.15;
                color += vec3(refraction * vec3(0.9, 0.95, 1.0));
                
                gl_FragColor = vec4(color, 1.0);
            }
        `,
  });

  // Create plane geometry for water
  const geometry = new THREE.PlaneGeometry(2, 2);
  mesh = new THREE.Mesh(geometry, material);
  mesh.position.z = 0;
  scene.add(mesh);

  // Create LARGE 3D white spherical ball - highly visible
  const ballSize = 0.35; // Much larger sphere for high visibility
  const ballGeometry = new THREE.SphereGeometry(ballSize, 64, 64);

  // Create a gradient material for realistic shading
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
        // Create gradient from top (bright) to bottom (darker)
        vec3 lightDir = normalize(vec3(0.5, 1.2, 1.0));
        float diffuse = max(dot(vNormal, lightDir), 0.0);
        
        // Soft gradient based on Y position
        float gradient = (vPosition.y + 1.0) * 0.5;
        
        // Combine lighting - very bright and visible
        vec3 color = vec3(1.0, 1.0, 1.0);
        color *= 0.95 + diffuse * 0.4;
        color *= 0.85 + gradient * 0.5;
        
        // Add very strong rim light for better visibility
        float rim = 1.0 - max(dot(vNormal, vec3(0.0, 0.0, 1.0)), 0.0);
        rim = pow(rim, 2.0);
        color += rim * 0.35;
        
        gl_FragColor = vec4(color, 1.0); // Full opacity
      }
    `,
  });

  ballMesh = new THREE.Mesh(ballGeometry, ballMaterial);
  ballMesh.position.z = -1.5; // Much closer for high visibility
  ballMesh.position.y = 0;

  // Add very visible shadow/glow behind the ball
  const shadowGeometry = new THREE.SphereGeometry(ballSize * 1.25, 64, 64);
  const shadowMaterial = new THREE.MeshBasicMaterial({
    color: 0xa0a0a0,
    transparent: true,
    opacity: 0.5, // Very visible shadow
  });
  const ballShadow = new THREE.Mesh(shadowGeometry, shadowMaterial);
  ballShadow.position.copy(ballMesh.position);
  ballShadow.position.z -= 0.25;
  ballShadow.position.y -= 0.05;

  scene.add(ballShadow);
  scene.add(ballMesh);

  // Store shadow reference
  centralBall.shadow = ballShadow;

  // Add event listeners
  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("resize", onWindowResize);

  // Start animation
  animate();
}

// Mouse move handler - gentler mouse ripples that also spread wide
function onMouseMove(event) {
  // Normalize mouse coordinates to 0-1 range
  mouse.x = event.clientX / window.innerWidth;
  mouse.y = 1 - event.clientY / window.innerHeight;

  // Calculate momentum based on mouse movement speed - gentler
  const dx = mouse.x - lastMouse.x;
  const dy = mouse.y - lastMouse.y;
  const momentum = Math.min(Math.sqrt(dx * dx + dy * dy) * 10, 1.5);

  // Add ripple at mouse position with wider spread
  if (momentum > 0.008) {
    waterTexture.addPoint(mouse.x, mouse.y, momentum * 1.0);
  }

  lastMouse.x = mouse.x;
  lastMouse.y = mouse.y;
}

// Create continuous ripples from the central ball - only when coming down
let rippleTimer = 0;
let lastFloatOffset = 0;
function updateCentralBallRipples() {
  rippleTimer++;

  // VERY SLOW, smooth floating animation - goes up slowly, comes down slowly
  const floatAmplitude = 0.15; // Large amplitude for very visible movement
  const floatSpeed = 0.008; // MUCH slower for very smooth motion
  const previousOffset = centralBall.floatOffset;
  centralBall.floatOffset = Math.sin(rippleTimer * floatSpeed) * floatAmplitude;

  if (ballMesh) {
    ballMesh.position.y = centralBall.floatOffset;

    // Update shader time for gradient animation
    if (ballMesh.material.uniforms) {
      ballMesh.material.uniforms.uTime.value = rippleTimer * 0.01;
    }

    // Update shadow position
    if (centralBall.shadow) {
      centralBall.shadow.position.y = centralBall.floatOffset - 0.05;
    }
  }

  // Detect when ball is moving downward and approaching water surface
  const isMovingDown = centralBall.floatOffset < previousOffset;
  const isTouchingWater =
    centralBall.floatOffset < -0.1 && centralBall.floatOffset > -0.15;

  // Only create realistic ripples when ball is moving DOWN and touches/enters water
  if (isMovingDown && isTouchingWater && rippleTimer % 5 === 0) {
    // Create realistic spreading ripples at multiple points around the ball's circumference
    const numRipples = 12; // More ripples for realistic effect
    for (let i = 0; i < numRipples; i++) {
      const angle = (i / numRipples) * Math.PI * 2;
      const rippleRadius = 0.16; // Larger radius for realistic spread
      const rx = centralBall.x + Math.cos(angle) * rippleRadius;
      const ry = centralBall.y + Math.sin(angle) * rippleRadius;
      waterTexture.addPoint(rx, ry, 1.4); // Strong momentum for visible ripples
    }
    // Main powerful ripple from center with realistic physics
    waterTexture.addPoint(centralBall.x, centralBall.y, 2.0);

    // Add secondary ripples for realism
    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2 + Math.PI / 8;
      const rippleRadius = 0.12;
      const rx = centralBall.x + Math.cos(angle) * rippleRadius;
      const ry = centralBall.y + Math.sin(angle) * rippleRadius;
      waterTexture.addPoint(rx, ry, 1.0);
    }
  }

  // Very subtle scale animation
  const scale = 1.0 + Math.sin(rippleTimer * 0.015) * 0.012;
  if (ballMesh) {
    ballMesh.scale.set(scale, scale, scale);
  }
}

// Window resize handler
function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);

  if (mesh.material.uniforms) {
    mesh.material.uniforms.uResolution.value.set(
      window.innerWidth,
      window.innerHeight
    );
  }
}

// Animation loop
function animate() {
  requestAnimationFrame(animate);

  // Update central ball ripples
  updateCentralBallRipples();

  // Update water texture
  waterTexture.update();

  // Update shader uniforms
  if (mesh.material.uniforms) {
    mesh.material.uniforms.uTexture.value.needsUpdate = true;
    mesh.material.uniforms.uTime.value += 0.016;
  }

  // Render scene
  renderer.render(scene, camera);
}

// Handle header transparency on scroll
function handleScroll() {
  const header = document.querySelector("header");
  const scrollPosition = window.scrollY;
  const viewportHeight = window.innerHeight;

  // Make header transparent when scrolled into second section
  if (scrollPosition > viewportHeight * 0.5) {
    header.classList.add("transparent");
  } else {
    header.classList.remove("transparent");
  }
}

// Animate counter when card comes into view
function animateCounter() {
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

            // Continuous animation loop between 20% and 80%
            function animatePercentage() {
              // Phase 1: Stay at 20% (0-40% of 6s = 2.4s)
              setTimeout(() => {
                percentageValue.textContent = "20";
              }, 0);

              // Phase 2: Transition from 20% to 80% (40-55% of 6s = 0.9s)
              setTimeout(() => {
                let count = 20;
                const target = 80;
                const duration = 900; // 0.9s
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

              // Phase 3: Stay at 80% (55-95% of 6s = 2.4s)
              // Already handled by the counter above

              // Phase 4: Reset to 20% (95-100% of 6s = 0.3s)
              setTimeout(() => {
                percentageValue.textContent = "20";
              }, 5700);
            }

            // Start the animation
            animatePercentage();

            // Repeat every 6 seconds
            setInterval(animatePercentage, 6000);
          }
        }
      });
    },
    { threshold: 0.5 }
  );

  const cards = document.querySelectorAll(".feature-card");
  cards.forEach((card) => observer.observe(card));
}

// Scroll-based Feature Carousel
function initFeatureCarousel() {
  const sections = document.querySelectorAll(".feature-section");
  const visuals = document.querySelectorAll(".feature-visual");

  if (sections.length === 0) return;

  function updateActiveFeature() {
    const scrollPos = window.scrollY;
    const windowHeight = window.innerHeight;

    sections.forEach((section, index) => {
      const rect = section.getBoundingClientRect();
      const sectionTop = rect.top + scrollPos;
      const sectionMiddle = sectionTop + rect.height / 2;
      const viewportMiddle = scrollPos + windowHeight / 2;

      // Check if section middle is near viewport middle
      const distance = Math.abs(sectionMiddle - viewportMiddle);
      const threshold = windowHeight / 3;

      if (distance < threshold) {
        // Activate this section
        sections.forEach((s) => s.classList.remove("active"));
        visuals.forEach((v) => v.classList.remove("active"));

        section.classList.add("active");
        if (visuals[index]) {
          visuals[index].classList.add("active");
        }
      }
    });
  }

  // Initial check
  updateActiveFeature();

  // Update on scroll with throttle
  let scrollTimeout;
  window.addEventListener("scroll", () => {
    if (scrollTimeout) {
      window.cancelAnimationFrame(scrollTimeout);
    }
    scrollTimeout = window.requestAnimationFrame(() => {
      updateActiveFeature();
    });
  });
}

// Add scroll listener
window.addEventListener("scroll", handleScroll);

// Initialize Service Cards with Dynamic Icon Movements
function initServiceCards() {
  const serviceCards = document.querySelectorAll(".service-card");

  serviceCards.forEach((card, index) => {
    const icon = card.querySelector(".service-icon");
    if (!icon) return;

    // Mouse move parallax effect with smooth easing
    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const deltaX = (x - centerX) / centerX;
      const deltaY = (y - centerY) / centerY;

      // Move icon based on mouse position with subtle effect
      const moveX = deltaX * 12;
      const moveY = deltaY * 12;
      const rotate = deltaX * 3;

      icon.style.transform = `translate(${moveX}px, ${moveY}px) rotate(${rotate}deg)`;

      // Card tilt effect
      const tiltX = deltaY * 2;
      const tiltY = -deltaX * 2;
      card.style.transform = `translateY(-8px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
    });

    // Reset on mouse leave with smooth transition
    card.addEventListener("mouseleave", () => {
      icon.style.transform = "translate(0, 0) rotate(0deg)";
      card.style.transform = "translateY(0) rotateX(0deg) rotateY(0deg)";
    });

    // Add continuous subtle floating movement
    let time = index * 1000; // Offset for each card
    let animationId;

    function animateIcon() {
      time += 16; // ~60fps
      const offsetX = Math.sin(time / 1500) * 2;
      const offsetY = Math.cos(time / 1800) * 2;
      const rotation = Math.sin(time / 2000) * 1.5;
      const scale = 1 + Math.sin(time / 2500) * 0.02;

      // Only apply subtle animation when not hovering
      if (!card.matches(":hover")) {
        icon.style.transform = `translate(${offsetX}px, ${offsetY}px) rotate(${rotation}deg) scale(${scale})`;
      }

      animationId = requestAnimationFrame(animateIcon);
    }

    animateIcon();

    // Cleanup on page unload
    window.addEventListener("beforeunload", () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    });
  });
}

// ===== PROJECTS CAROUSEL FUNCTIONALITY =====
let currentProjectSlide = 0;
let projectRotationInterval = null;

function initProjectsCarousel() {
  const slides = document.querySelectorAll(".project-slide");
  const tabs = document.querySelectorAll(".project-tab");

  console.log("Initializing projects carousel...");
  console.log("Found slides:", slides.length);
  console.log("Found tabs:", tabs.length);

  if (slides.length === 0 || tabs.length === 0) {
    console.error("Projects carousel elements not found!");
    return;
  }

  // Function to show a specific slide
  function showSlide(index) {
    console.log("Showing slide:", index);

    // Remove active class from all slides and tabs
    slides.forEach((slide, i) => {
      slide.classList.remove("active");
      console.log("Removed active from slide", i);
    });
    tabs.forEach((tab, i) => {
      tab.classList.remove("active");
      console.log("Removed active from tab", i);
    });

    // Add active class to current slide and tab
    slides[index].classList.add("active");
    tabs[index].classList.add("active");
    console.log("Added active to slide and tab", index);

    currentProjectSlide = index;

    // Animate metrics when slide becomes active
    animateProjectMetrics(slides[index]);
  }

  // Function to animate percentage counters
  function animateProjectMetrics(slide) {
    const metricElements = slide.querySelectorAll(".metric-percentage");
    console.log(
      "Animating metrics for slide, found",
      metricElements.length,
      "metrics"
    );

    metricElements.forEach((element, idx) => {
      const target = parseInt(element.getAttribute("data-target"));
      console.log("Animating metric", idx, "to", target + "%");

      const duration = 2000; // 2 seconds
      const startTime = performance.now();

      // Reset to 0 before animating
      element.textContent = "0%";

      function updateCounter(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function for smooth animation
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

  // Function to go to next slide
  function nextSlide() {
    const nextIndex = (currentProjectSlide + 1) % slides.length;
    console.log("Moving to next slide:", currentProjectSlide, "->", nextIndex);
    showSlide(nextIndex);
  }

  // Tab click handlers
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => {
      console.log("Tab clicked:", index);
      showSlide(index);
      // Reset auto-rotation timer
      clearInterval(projectRotationInterval);
      projectRotationInterval = setInterval(nextSlide, 5000);
      console.log("Auto-rotation timer reset");
    });
  });

  // Start auto-rotation (every 5 seconds)
  projectRotationInterval = setInterval(nextSlide, 5000);
  console.log("Auto-rotation started (5 seconds)");

  // Initialize first slide
  showSlide(0);

  // Pause rotation when user hovers over carousel
  const carousel = document.querySelector(".projects-carousel");
  if (carousel) {
    carousel.addEventListener("mouseenter", () => {
      console.log("Mouse entered carousel - pausing rotation");
      clearInterval(projectRotationInterval);
    });

    carousel.addEventListener("mouseleave", () => {
      console.log("Mouse left carousel - resuming rotation");
      projectRotationInterval = setInterval(nextSlide, 5000);
    });
  }
}

// ===== COMPARISON SECTION SCROLL ANIMATION =====
function initComparisonAnimation() {
  const cards = document.querySelectorAll(".comparison-card");

  if (cards.length === 0) {
    console.log("No comparison cards found");
    return;
  }

  console.log("Initializing comparison animation for", cards.length, "cards");

  const observerOptions = {
    threshold: 0.15,
    rootMargin: "0px 0px -50px 0px",
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (
        entry.isIntersecting &&
        !entry.target.classList.contains("slide-in")
      ) {
        console.log("Card entering view, adding slide-in class");
        // Small delay for dramatic effect
        setTimeout(() => {
          entry.target.classList.add("slide-in");
        }, 100);
      }
    });
  }, observerOptions);

  // Observe both comparison cards
  cards.forEach((card, index) => {
    console.log("Observing card", index, ":", card.classList);
    observer.observe(card);
  });
}

// FAQ Accordion Functionality
function initFAQAccordion() {
  const faqItems = document.querySelectorAll(".faq-item");

  faqItems.forEach((item) => {
    const question = item.querySelector(".faq-question");

    question.addEventListener("click", () => {
      const isActive = item.classList.contains("active");

      // Close all FAQ items
      faqItems.forEach((faq) => {
        faq.classList.remove("active");
      });

      // Open clicked item if it wasn't already open
      if (!isActive) {
        item.classList.add("active");
      }
    });
  });
}

// Footer Water Ripple Initialization
let footerScene, footerCamera, footerRenderer, footerWaterTexture;

function initFooter() {
  const footerCanvas = document.getElementById("footer-canvas");
  if (!footerCanvas) return;

  // Create scene
  footerScene = new THREE.Scene();

  // Create camera
  footerCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, -10, 10);
  footerCamera.position.z = 5;

  // Create renderer
  footerRenderer = new THREE.WebGLRenderer({
    canvas: footerCanvas,
    antialias: true,
    alpha: true,
  });

  const footerRect = footerCanvas.getBoundingClientRect();
  footerRenderer.setSize(footerRect.width, footerRect.height);
  footerRenderer.setPixelRatio(window.devicePixelRatio);

  // Create water texture
  footerWaterTexture = new WaterTexture({
    size: 512,
    radius: 0.06,
    maxAge: 140,
    speed: 0.35,
    maxRipples: 15,
  });

  // Create material (same as header)
  const material = new THREE.ShaderMaterial({
    uniforms: {
      uTexture: {
        value: new THREE.CanvasTexture(footerWaterTexture.getTexture()),
      },
      uTime: { value: 0 },
      uResolution: {
        value: new THREE.Vector2(footerRect.width, footerRect.height),
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
    transparent: true,
  });

  // Create plane
  const geometry = new THREE.PlaneGeometry(2, 2);
  const plane = new THREE.Mesh(geometry, material);
  footerScene.add(plane);

  // Animation loop for footer
  function animateFooter() {
    requestAnimationFrame(animateFooter);

    // Update water texture
    footerWaterTexture.update();

    // Update shader uniforms
    material.uniforms.uTexture.value.needsUpdate = true;
    material.uniforms.uTime.value += 0.016;

    // Render scene
    footerRenderer.render(footerScene, footerCamera);
  }

  animateFooter();

  // Add automatic ripples
  setInterval(() => {
    const x = Math.random();
    const y = Math.random();
    const momentum = 0.6 + Math.random() * 0.4;
    footerWaterTexture.addPoint(x, y, momentum);
  }, 1800);

  // Mouse interaction
  footerCanvas.addEventListener("mousemove", (e) => {
    const rect = footerCanvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    footerWaterTexture.addPoint(x, y, 0.8);
  });

  // Handle window resize
  window.addEventListener("resize", () => {
    const rect = footerCanvas.getBoundingClientRect();
    footerRenderer.setSize(rect.width, rect.height);
    material.uniforms.uResolution.value.set(rect.width, rect.height);
  });
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    init();
    animateCounter();
    initFeatureCarousel();
    initServiceCards();
    initProjectsCarousel();
    initComparisonAnimation();
    initFAQAccordion();
  });
} else {
  init();
  animateCounter();
  initFeatureCarousel();
  initServiceCards();
  initProjectsCarousel();
  initComparisonAnimation();
  initFAQAccordion();
}
