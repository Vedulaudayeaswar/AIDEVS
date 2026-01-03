"""Frontend Engineer Agent - Generates HTML/CSS/JS"""
from .base_agent import BaseAgent

FRONTEND_SYSTEM_PROMPT = """You are an ELITE Frontend Designer creating STUNNING Framer.ai-quality websites.

🎨 PREMIUM DESIGN STANDARDS:

COLOR & AESTHETICS:
- Rich, deep colors: #0A0A0A (black), #FAFAFA (white)
- Sophisticated gradients: linear-gradient(135deg, #667eea 0%, #764ba2 100%)
- Glass morphism: background: rgba(255,255,255,0.1); backdrop-filter: blur(10px);
- Subtle shadows: 0 8px 32px rgba(0,0,0,0.12)
- Accent colors that pop but don't overwhelm

✨ ANIMATION & INTERACTION:
- Smooth transitions: transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
- Hover effects: transform: translateY(-4px); box-shadow enhancement
- Scroll animations: fade-in, slide-up effects
- Button animations: scale on hover, ripple effects
- Loading states: skeleton screens, smooth reveals
- Parallax effects where appropriate

📐 LAYOUT MASTERY:
- HEADER: 
  * Glassmorphic, backdrop-filter blur
  * Sticky with smooth shadow on scroll
  * Logo scales on scroll
  * Mobile hamburger with smooth menu slide
  * Height: 70-80px, padding: 0 5%

- HERO:
  * Full viewport (min-height: 100vh)
  * Gradient backgrounds with overlay
  * Headline: font-size: clamp(2.5rem, 8vw, 5rem); font-weight: 700;
  * Animated CTA button with gradient, shadow, and hover lift
  * Background particles or subtle animation
  * Center everything: display: grid; place-items: center;

- FEATURES:
  * Grid: display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  * Cards: background: white; border-radius: 20px; padding: 2.5rem;
  * Hover: transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.1);
  * Icons with gradient backgrounds
  * Stagger animations on load

- FOOTER:
  * Clean multi-column layout
  * Social icons with hover animations
  * Subtle top border or gradient separator

🚀 TECHNICAL EXCELLENCE:

CSS TECHNIQUES:
```css
/* Modern Reset */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

/* Smooth Scrolling */
html { scroll-behavior: smooth; }

/* Custom Properties */
:root {
  --primary: #667eea;
  --secondary: #764ba2;
  --dark: #0A0A0A;
  --light: #FAFAFA;
  --shadow: 0 10px 30px rgba(0,0,0,0.1);
  --radius: 16px;
  --transition: cubic-bezier(0.4, 0, 0.2, 1);
}

/* Glass Effect */
.glass {
  background: rgba(255,255,255,0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.2);
}

/* Gradient Text */
.gradient-text {
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Button Animation */
.btn {
  position: relative;
  overflow: hidden;
  transition: all 0.4s var(--transition);
}
.btn:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
.btn::before {
  content: '';
  position: absolute;
  top: 50%; left: 50%;
  width: 0; height: 0;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}
.btn:hover::before { width: 300px; height: 300px; }

/* Card Hover */
.card {
  transition: all 0.3s var(--transition);
}
.card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(0,0,0,0.15);
}

/* Fade In Animation */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-in { animation: fadeInUp 0.8s var(--transition) forwards; }
```

JAVASCRIPT FOR INTERACTIONS:
```javascript
// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', e => {
    e.preventDefault();
    document.querySelector(anchor.getAttribute('href')).scrollIntoView({ behavior: 'smooth' });
  });
});

// Header shadow on scroll
window.addEventListener('scroll', () => {
  const header = document.querySelector('header');
  header.style.boxShadow = window.scrollY > 50 ? '0 4px 20px rgba(0,0,0,0.1)' : 'none';
});

// Animate elements on scroll
const observerOptions = { threshold: 0.1 };
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if(entry.isIntersecting) entry.target.classList.add('animate-in');
  });
}, observerOptions);
document.querySelectorAll('.card, .feature').forEach(el => observer.observe(el));
```

💎 QUALITY CHECKLIST:
✅ Responsive breakpoints: 480px, 768px, 1024px, 1440px
✅ Accessibility: semantic HTML, ARIA labels, proper contrast
✅ Performance: optimized animations, no jank
✅ Modern fonts: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto
✅ Consistent spacing: 8px grid (8, 16, 24, 32, 48, 64px)
✅ Interactive states: hover, active, focus, disabled
✅ Loading states and micro-interactions

OUTPUT STRUCTURE:
Generate ONLY the section code with:
1. Inline <style> with all CSS
2. Semantic HTML5
3. <script> for interactions if needed
4. NO explanations, NO markdown wrappers
5. Production-ready, copy-paste code

BUILD PIXEL-PERFECT. BUILD ANIMATED. BUILD BEAUTIFUL.
"""

class FrontendAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Frontend Engineer",
            role="frontend",
            system_prompt=FRONTEND_SYSTEM_PROMPT
        )
        self.sections = {
            'header': '',
            'hero': '',
            'features': '',
            'footer': ''
        }
    
    def generate_section(self, section_name, requirements, existing_code=None, api_key=None):
        """Generate specific website section with premium quality"""
        context = f"Existing sections to maintain consistency:\n{existing_code}" if existing_code else ""
        
        # Section-specific design guidelines with code examples
        section_guides = {
            'header': """
🎯 HEADER DESIGN GUIDE:

STRUCTURE:
<style>
header {
  position: fixed;
  top: 0;
  width: 100%;
  z-index: 1000;
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(20px);
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
}
header.scrolled { box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
nav { display: flex; justify-content: space-between; align-items: center; padding: 1.5rem 5%; }
.logo { font-size: 1.5rem; font-weight: 700; }
.nav-links { display: flex; gap: 2rem; list-style: none; }
.nav-links a { position: relative; transition: color 0.3s; }
.nav-links a::after { 
  content: ''; position: absolute; bottom: -5px; left: 0; 
  width: 0; height: 2px; background: currentColor; transition: width 0.3s; 
}
.nav-links a:hover::after { width: 100%; }
@media (max-width: 768px) { .nav-links { display: none; } }
</style>
""",
            'hero': """
🎯 HERO SECTION DESIGN GUIDE:

STRUCTURE:
<style>
.hero {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
  color: white;
  text-align: center;
  padding: 2rem;
}
.hero::before {
  content: '';
  position: absolute;
  width: 500px;
  height: 500px;
  background: rgba(255,255,255,0.1);
  border-radius: 50%;
  top: -250px;
  right: -250px;
  animation: float 6s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}
.hero-content { position: relative; z-index: 1; max-width: 800px; }
.hero h1 {
  font-size: clamp(2.5rem, 8vw, 5rem);
  font-weight: 700;
  margin-bottom: 1rem;
  line-height: 1.1;
  animation: fadeInUp 1s ease-out;
}
.hero p {
  font-size: clamp(1.1rem, 2vw, 1.5rem);
  opacity: 0.95;
  margin-bottom: 2rem;
  animation: fadeInUp 1s ease-out 0.2s backwards;
}
.hero-btn {
  display: inline-block;
  padding: 1rem 2.5rem;
  background: white;
  color: #667eea;
  border-radius: 50px;
  font-weight: 600;
  font-size: 1.1rem;
  transition: all 0.4s cubic-bezier(0.4,0,0.2,1);
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
  animation: fadeInUp 1s ease-out 0.4s backwards;
}
.hero-btn:hover {
  transform: translateY(-3px) scale(1.05);
  box-shadow: 0 15px 40px rgba(0,0,0,0.3);
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
""",
            'features': """
🎯 FEATURES SECTION DESIGN GUIDE:

STRUCTURE:
<style>
.features {
  padding: 6rem 5%;
  background: #FAFAFA;
}
.features-container {
  max-width: 1200px;
  margin: 0 auto;
}
.section-title {
  text-align: center;
  font-size: clamp(2rem, 5vw, 3rem);
  margin-bottom: 3rem;
  color: #0A0A0A;
}
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}
.feature-card {
  background: white;
  padding: 2.5rem;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  transition: all 0.4s cubic-bezier(0.4,0,0.2,1);
  opacity: 0;
  transform: translateY(30px);
}
.feature-card.animate-in {
  animation: fadeInUp 0.8s ease-out forwards;
}
.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(0,0,0,0.12);
}
.feature-icon {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: grid;
  place-items: center;
  font-size: 2rem;
  margin-bottom: 1.5rem;
  color: white;
}
.feature-card h3 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: #0A0A0A;
}
.feature-card p {
  color: #666;
  line-height: 1.6;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
<script>
const observer = new IntersectionObserver(entries => {
  entries.forEach((entry, index) => {
    if(entry.isIntersecting) {
      setTimeout(() => entry.target.classList.add('animate-in'), index * 100);
    }
  });
}, { threshold: 0.1 });
document.querySelectorAll('.feature-card').forEach(card => observer.observe(card));
</script>
""",
            'footer': """
🎯 FOOTER DESIGN GUIDE:

STRUCTURE:
<style>
footer {
  background: #0A0A0A;
  color: #FAFAFA;
  padding: 4rem 5% 2rem;
}
.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 3rem;
  margin-bottom: 3rem;
}
.footer-column h4 {
  font-size: 1.2rem;
  margin-bottom: 1.5rem;
  color: white;
}
.footer-links {
  list-style: none;
}
.footer-links li {
  margin-bottom: 0.8rem;
}
.footer-links a {
  color: #999;
  transition: color 0.3s;
}
.footer-links a:hover {
  color: #667eea;
}
.social-icons {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}
.social-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  display: grid;
  place-items: center;
  transition: all 0.3s;
}
.social-icon:hover {
  background: #667eea;
  transform: translateY(-3px);
}
.footer-bottom {
  text-align: center;
  padding-top: 2rem;
  border-top: 1px solid rgba(255,255,255,0.1);
  color: #666;
}
</style>
"""
        }
        
        guide = section_guides.get(section_name, "Create a stunning, professional section.")
        
        prompt = f"""Create a PREMIUM {section_name.upper()} section with Framer.ai quality:

USER REQUIREMENTS:
{requirements}

DESIGN REFERENCE & CODE EXAMPLES:
{guide}

{context}

CRITICAL REQUIREMENTS:
1. Use the design patterns from the guide above
2. Include smooth animations and transitions
3. Add hover effects and micro-interactions
4. Make it fully responsive (mobile-first)
5. Use modern CSS (Grid, Flexbox, custom properties, clamp())
6. Include necessary JavaScript for interactions
7. Use gradient backgrounds, glass effects, and shadows
8. Add scroll animations where appropriate
9. STUNNING visual design that matches Framer.ai quality

OUTPUT FORMAT:
- Generate ONLY the section HTML with inline <style> and <script>
- NO full page structure, NO explanations
- Production-ready code that can be inserted directly
- Include all CSS animations and JavaScript interactions

Make it BEAUTIFUL, ANIMATED, and PROFESSIONAL."""
        
        response = self.generate_response(prompt, api_key=api_key)
        code_blocks = self.extract_code(response)
        
        # Update section storage
        if 'html' in code_blocks:
            self.sections[section_name] = code_blocks['html']
        
        return {
            'response': response,
            'code': code_blocks,
            'section': section_name
        }
    
    def update_section(self, section_name, modification, existing_code):
        """Update existing section without affecting others"""
        prompt = f"""Modify the {section_name} section with this change:
{modification}

Current code:
{existing_code}

Keep all other sections unchanged. Only update the {section_name} section."""
        
        response = self.generate_response(prompt)
        code_blocks = self.extract_code(response)
        
        return {
            'response': response,
            'code': code_blocks,
            'section': section_name
        }
    
    def combine_sections(self, sections_dict=None):
        """Combine all sections into complete premium HTML"""
        # Use provided sections or instance sections
        sections = sections_dict if sections_dict else self.sections
        
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIDevs - Premium Website</title>
    <style>
        /* Modern CSS Reset & Base Styles */
        *, *::before, *::after {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --font-base: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            --transition-smooth: cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        html {{
            scroll-behavior: smooth;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        
        body {{
            font-family: var(--font-base);
            line-height: 1.6;
            overflow-x: hidden;
        }}
        
        img {{
            max-width: 100%;
            height: auto;
            display: block;
        }}
        
        a {{
            text-decoration: none;
            color: inherit;
        }}
        
        button {{
            font-family: inherit;
            border: none;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    {header}
    {hero}
    {features}
    {footer}
</body>
</html>"""
        
        return html_template.format(
            header=sections.get('header', ''),
            hero=sections.get('hero', ''),
            features=sections.get('features', ''),
            footer=sections.get('footer', '')
        )
