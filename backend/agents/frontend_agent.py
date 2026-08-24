"""Frontend Engineer Agent - Generates HTML/CSS/JS"""
import html
import re

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
        project_brief = self._build_project_brief(requirements)
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
{project_brief}

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
10. If the website is ecommerce, include realistic commerce UI such as search, cart, product cards, trust badges, shipping/returns, checkout signals, and polished product imagery placeholders
11. Preserve all gathered project details: name, palette, selected header idea, selected hero copy, and prior sections

OUTPUT FORMAT:
- Generate ONLY the section HTML with inline <style> and <script>
- NO full page structure, NO explanations
- Production-ready code that can be inserted directly
- Include all CSS animations and JavaScript interactions

Make it BEAUTIFUL, ANIMATED, and PROFESSIONAL."""
        
        response = self.generate_response(prompt, api_key=api_key, max_tokens=6000)
        code_blocks = self.extract_code(response)
        if not self._is_usable_section(code_blocks.get('html', ''), section_name):
            fallback_html = self._fallback_section(section_name, requirements)
            response = fallback_html
            code_blocks = {'html': fallback_html}
        
        # Update section storage
        if 'html' in code_blocks:
            self.sections[section_name] = code_blocks['html']
        
        return {
            'response': response,
            'code': code_blocks,
            'section': section_name
        }

    def _build_project_brief(self, requirements):
        """Create a single prompt-friendly brief from gathered conversation state."""
        if not isinstance(requirements, dict):
            return str(requirements)

        gathered = requirements.get('gathered_info', {})
        lines = [
            f"Website type: {gathered.get('type', 'modern business website')}",
            f"Store/site details and palette: {gathered.get('details', '')}",
            f"Header instructions: {gathered.get('header_instructions', '')}",
            f"Hero instructions: {gathered.get('hero_instructions', '')}",
            f"Features instructions: {gathered.get('features_instructions', '')}",
            f"Footer instructions: {gathered.get('footer_instructions', '')}",
            f"Current user instruction: {requirements.get('current_message', '')}",
        ]
        return "\n".join(line for line in lines if line.split(': ', 1)[-1])

    def _is_usable_section(self, section_html, section_name):
        """Reject tiny/plain model outputs that make the live preview look broken."""
        if not section_html:
            return False
        section_html_lower = section_html.lower()
        has_target_tag = f"<{section_name}" in section_html_lower or (
            section_name == 'features' and 'feature' in section_html_lower
        )
        has_design = '<style' in section_html_lower and any(
            token in section_html_lower
            for token in ['display:', 'grid', 'flex', 'background:', 'box-shadow', 'border-radius']
        )
        return len(section_html) >= 1200 and has_target_tag and has_design

    def _fallback_section(self, section_name, requirements):
        """Deterministic premium ecommerce template when the model returns weak HTML."""
        brief = self._build_project_brief(requirements)
        safe_brief = html.escape(brief)
        store_name = self._extract_store_name(brief)
        hero_headline = self._extract_field(brief, 'Headline') or 'Elevate Your Everyday'
        hero_subtitle = self._extract_field(brief, 'Subtitle') or 'Premium gear in bold teal & charcoal tones'
        hero_cta = self._extract_field(brief, 'CTA') or 'Start Shopping'
        palette = {
            'charcoal': '#111827',
            'charcoal_2': '#17212f',
            'teal': '#14b8a6',
            'teal_dark': '#0f766e',
            'mint': '#ccfbf1',
            'ink': '#ecfeff',
            'muted': '#9ca3af',
        }

        if section_name == 'header':
            return f"""
<style>
  .aid-header {{ position: sticky; top: 0; z-index: 1000; background: rgba(17, 24, 39, 0.86); backdrop-filter: blur(18px); border-bottom: 1px solid rgba(20, 184, 166, 0.22); color: {palette['ink']}; }}
  .aid-nav {{ max-width: 1180px; margin: 0 auto; min-height: 76px; padding: 0 24px; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 24px; }}
  .aid-logo {{ display: inline-flex; align-items: center; gap: 10px; font-size: 1.25rem; font-weight: 800; letter-spacing: 0; }}
  .aid-logo-mark {{ width: 38px; height: 38px; border-radius: 12px; display: grid; place-items: center; color: {palette['charcoal']}; background: linear-gradient(135deg, {palette['teal']}, {palette['mint']}); box-shadow: 0 12px 30px rgba(20, 184, 166, 0.28); }}
  .aid-links {{ display: flex; justify-content: center; align-items: center; gap: 28px; list-style: none; }}
  .aid-links a {{ color: {palette['ink']}; font-weight: 650; opacity: .86; position: relative; }}
  .aid-links a::after {{ content: ""; position: absolute; left: 0; bottom: -9px; width: 0; height: 2px; background: {palette['teal']}; transition: width .25s ease; }}
  .aid-links a:hover::after {{ width: 100%; }}
  .aid-actions {{ display: flex; align-items: center; gap: 12px; }}
  .aid-search {{ min-width: 190px; border: 1px solid rgba(204, 251, 241, .22); background: rgba(255, 255, 255, .08); color: {palette['ink']}; border-radius: 999px; padding: 11px 15px; outline: none; }}
  .aid-action-btn {{ width: 42px; height: 42px; border-radius: 14px; display: grid; place-items: center; border: 1px solid rgba(204, 251, 241, .18); background: rgba(255,255,255,.08); color: {palette['ink']}; transition: transform .25s ease, background .25s ease; }}
  .aid-action-btn:hover {{ transform: translateY(-2px); background: rgba(20, 184, 166, .22); }}
  .aid-sale {{ color: {palette['charcoal']}; background: {palette['teal']}; padding: 7px 11px; border-radius: 999px; font-weight: 800; }}
  @media (max-width: 820px) {{ .aid-nav {{ grid-template-columns: 1fr auto; }} .aid-links, .aid-search {{ display: none; }} }}
</style>
<header class="aid-header" data-brief="{safe_brief}">
  <nav class="aid-nav" aria-label="Primary navigation">
    <a class="aid-logo" href="#"><span class="aid-logo-mark">A</span><span>{html.escape(store_name)}</span></a>
    <ul class="aid-links">
      <li><a href="#shop">Shop</a></li>
      <li><a href="#collections">Collections</a></li>
      <li><a href="#about">About</a></li>
      <li><a class="aid-sale" href="#deals">Deals</a></li>
    </ul>
    <div class="aid-actions">
      <input class="aid-search" aria-label="Search products" placeholder="Search gear" />
      <button class="aid-action-btn" aria-label="Account">◎</button>
      <button class="aid-action-btn" aria-label="Cart">◧</button>
    </div>
  </nav>
</header>"""

        if section_name == 'hero':
            return f"""
<style>
  .aid-hero {{ min-height: 82vh; padding: 112px 24px 72px; color: {palette['ink']}; background: radial-gradient(circle at 80% 18%, rgba(20,184,166,.32), transparent 34%), linear-gradient(135deg, {palette['charcoal']} 0%, {palette['charcoal_2']} 58%, #062925 100%); overflow: hidden; }}
  .aid-hero-wrap {{ max-width: 1180px; margin: 0 auto; display: grid; grid-template-columns: minmax(0, 1.02fr) minmax(320px, .98fr); gap: 48px; align-items: center; }}
  .aid-kicker {{ display: inline-flex; align-items: center; gap: 10px; color: {palette['mint']}; background: rgba(20,184,166,.12); border: 1px solid rgba(20,184,166,.28); padding: 9px 14px; border-radius: 999px; font-weight: 750; }}
  .aid-hero h1 {{ max-width: 760px; margin: 24px 0 16px; font-size: clamp(2.7rem, 7vw, 5.7rem); line-height: .95; letter-spacing: 0; }}
  .aid-hero p {{ max-width: 610px; color: rgba(236,254,255,.78); font-size: clamp(1.05rem, 2vw, 1.32rem); margin-bottom: 30px; }}
  .aid-hero-actions {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: center; }}
  .aid-primary {{ color: {palette['charcoal']}; background: linear-gradient(135deg, {palette['teal']}, {palette['mint']}); padding: 15px 24px; border-radius: 999px; font-weight: 850; box-shadow: 0 18px 38px rgba(20,184,166,.28); transition: transform .25s ease; }}
  .aid-primary:hover {{ transform: translateY(-3px); }}
  .aid-secondary {{ color: {palette['ink']}; border: 1px solid rgba(204,251,241,.25); padding: 14px 22px; border-radius: 999px; }}
  .aid-product-stage {{ position: relative; min-height: 480px; display: grid; place-items: center; }}
  .aid-product-card {{ width: min(420px, 92vw); border-radius: 28px; padding: 24px; background: rgba(255,255,255,.09); border: 1px solid rgba(204,251,241,.22); backdrop-filter: blur(22px); box-shadow: 0 30px 90px rgba(0,0,0,.32); animation: aidFloat 5.5s ease-in-out infinite; }}
  .aid-product-img {{ aspect-ratio: 1 / .78; border-radius: 22px; background: linear-gradient(145deg, #0f766e, #ccfbf1); display: grid; place-items: center; color: {palette['charcoal']}; font-size: clamp(4rem, 9vw, 7rem); font-weight: 900; }}
  .aid-product-meta {{ display: flex; justify-content: space-between; gap: 20px; margin-top: 18px; }}
  .aid-product-meta h3 {{ font-size: 1.2rem; }}
  .aid-price {{ color: {palette['mint']}; font-weight: 900; }}
  .aid-trust {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 30px; max-width: 620px; }}
  .aid-trust span {{ background: rgba(255,255,255,.07); border: 1px solid rgba(204,251,241,.14); border-radius: 16px; padding: 14px; color: rgba(236,254,255,.82); font-weight: 650; }}
  @keyframes aidFloat {{ 0%, 100% {{ transform: translateY(0) rotate(-1deg); }} 50% {{ transform: translateY(-16px) rotate(1deg); }} }}
  @media (max-width: 880px) {{ .aid-hero-wrap {{ grid-template-columns: 1fr; }} .aid-product-stage {{ min-height: 360px; }} .aid-trust {{ grid-template-columns: 1fr; }} }}
</style>
<section class="aid-hero">
  <div class="aid-hero-wrap">
    <div>
      <span class="aid-kicker">New season drop now live</span>
      <h1>{html.escape(hero_headline)}</h1>
      <p>{html.escape(hero_subtitle)}</p>
      <div class="aid-hero-actions">
        <a class="aid-primary" href="#shop">{html.escape(hero_cta)}</a>
        <a class="aid-secondary" href="#collections">View Collections</a>
      </div>
      <div class="aid-trust"><span>Free shipping</span><span>Secure checkout</span><span>30 day returns</span></div>
    </div>
    <div class="aid-product-stage" aria-label="Featured ecommerce product">
      <article class="aid-product-card">
        <div class="aid-product-img">A</div>
        <div class="aid-product-meta"><h3>Signature Everyday Kit</h3><span class="aid-price">$89</span></div>
      </article>
    </div>
  </div>
</section>"""

        if section_name == 'features':
            return f"""
<style>
  .aid-features {{ padding: 86px 24px; background: #f8fafc; color: {palette['charcoal']}; }}
  .aid-features-wrap {{ max-width: 1180px; margin: 0 auto; }}
  .aid-section-head {{ display: flex; justify-content: space-between; gap: 28px; align-items: end; margin-bottom: 34px; }}
  .aid-section-head h2 {{ font-size: clamp(2rem, 4.5vw, 3.6rem); line-height: 1; max-width: 620px; }}
  .aid-section-head p {{ max-width: 420px; color: #526071; }}
  .aid-feature-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; }}
  .aid-feature-card {{ min-height: 238px; padding: 24px; border-radius: 8px; background: white; border: 1px solid #e5e7eb; box-shadow: 0 18px 45px rgba(17,24,39,.08); transition: transform .25s ease, box-shadow .25s ease; }}
  .aid-feature-card:hover {{ transform: translateY(-6px); box-shadow: 0 26px 65px rgba(17,24,39,.13); }}
  .aid-feature-icon {{ width: 46px; height: 46px; display: grid; place-items: center; border-radius: 14px; margin-bottom: 28px; color: {palette['charcoal']}; background: linear-gradient(135deg, {palette['teal']}, {palette['mint']}); font-weight: 900; }}
  .aid-feature-card h3 {{ font-size: 1.08rem; margin-bottom: 10px; }}
  .aid-feature-card p {{ color: #5d6978; line-height: 1.55; }}
  @media (max-width: 980px) {{ .aid-feature-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .aid-section-head {{ display: block; }} .aid-section-head p {{ margin-top: 14px; }} }}
  @media (max-width: 560px) {{ .aid-feature-grid {{ grid-template-columns: 1fr; }} }}
</style>
<section class="aid-features" id="shop">
  <div class="aid-features-wrap">
    <div class="aid-section-head">
      <h2>Everything shoppers expect from a polished store.</h2>
      <p>Built around conversion, confidence, and a sleek teal plus charcoal identity.</p>
    </div>
    <div class="aid-feature-grid">
      <article class="aid-feature-card"><div class="aid-feature-icon">1</div><h3>Curated Collections</h3><p>Editorial product groupings that make browsing feel intentional and premium.</p></article>
      <article class="aid-feature-card"><div class="aid-feature-icon">2</div><h3>Secure Checkout</h3><p>Clear payment signals, cart actions, and reassurance throughout the buying flow.</p></article>
      <article class="aid-feature-card"><div class="aid-feature-icon">3</div><h3>Fast Delivery</h3><p>Shipping and returns messaging placed where buyers need confidence.</p></article>
      <article class="aid-feature-card"><div class="aid-feature-icon">4</div><h3>Loyalty Rewards</h3><p>Repeat purchase prompts for points, drops, and member-only offers.</p></article>
    </div>
  </div>
</section>"""

        return f"""
<style>
  .aid-footer {{ background: {palette['charcoal']}; color: {palette['ink']}; padding: 56px 24px 28px; border-top: 1px solid rgba(20,184,166,.24); }}
  .aid-footer-wrap {{ max-width: 1180px; margin: 0 auto; display: grid; grid-template-columns: 1.3fr repeat(3, 1fr); gap: 36px; }}
  .aid-footer h3 {{ font-size: 1.45rem; margin-bottom: 12px; }}
  .aid-footer p, .aid-footer a {{ color: rgba(236,254,255,.68); line-height: 1.8; }}
  .aid-footer h4 {{ margin-bottom: 14px; color: white; }}
  .aid-footer ul {{ list-style: none; padding: 0; margin: 0; }}
  .aid-newsletter {{ display: flex; gap: 10px; margin-top: 18px; }}
  .aid-newsletter input {{ min-width: 0; flex: 1; border-radius: 999px; border: 1px solid rgba(204,251,241,.2); background: rgba(255,255,255,.08); color: white; padding: 12px 14px; }}
  .aid-newsletter button {{ border-radius: 999px; background: {palette['teal']}; color: {palette['charcoal']}; padding: 12px 16px; font-weight: 850; }}
  .aid-footer-bottom {{ max-width: 1180px; margin: 36px auto 0; padding-top: 22px; border-top: 1px solid rgba(255,255,255,.1); color: rgba(236,254,255,.55); display: flex; justify-content: space-between; gap: 18px; flex-wrap: wrap; }}
  @media (max-width: 800px) {{ .aid-footer-wrap {{ grid-template-columns: 1fr; }} }}
</style>
<footer class="aid-footer">
  <div class="aid-footer-wrap">
    <div><h3>{html.escape(store_name)}</h3><p>Premium gear in bold teal and charcoal tones, designed for everyday momentum.</p><form class="aid-newsletter"><input aria-label="Email" placeholder="Email address" /><button>Join</button></form></div>
    <div><h4>Shop</h4><ul><li><a href="#shop">New Arrivals</a></li><li><a href="#collections">Best Sellers</a></li><li><a href="#deals">Deals</a></li></ul></div>
    <div><h4>Support</h4><ul><li><a href="#shipping">Shipping</a></li><li><a href="#returns">Returns</a></li><li><a href="#contact">Contact</a></li></ul></div>
    <div><h4>Social</h4><ul><li><a href="#instagram">Instagram</a></li><li><a href="#youtube">YouTube</a></li><li><a href="#x">X</a></li></ul></div>
  </div>
  <div class="aid-footer-bottom"><span>&copy; 2026 {html.escape(store_name)}</span><span>Secure checkout &middot; Free returns &middot; Fast delivery</span></div>
</footer>"""

    def _extract_store_name(self, brief):
        match = re.search(r"name\s+(?:is|=|:)\s+([^.\n|]+)", brief, re.IGNORECASE)
        if match:
            name = match.group(1).strip(" *'\"")
            if name:
                return name[:36]
        return "All U Need"

    def _extract_field(self, brief, field):
        pattern = rf"{field}\s*:\s*\*?\*?\s*[“\"]?([^”\"\n|]+)"
        match = re.search(pattern, brief, re.IGNORECASE)
        if match:
            return match.group(1).strip(" *")
        return ""
    
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
