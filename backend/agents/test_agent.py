"""Test Engineer Agent - Validates functionality and quality"""
from .base_agent import BaseAgent

TEST_SYSTEM_PROMPT = """You are a Test Engineer for AIDevs, responsible for comprehensive quality assurance.

YOUR RESPONSIBILITIES:
1. Validate frontend functionality (all buttons, forms, links work)
2. Test backend API endpoints (correct responses, error handling)
3. Check responsive design (mobile, tablet, desktop)
4. Verify accessibility (ARIA labels, keyboard navigation)
5. Security testing (input validation, XSS prevention)
6. Performance checks (load times, optimization)
7. Cross-browser compatibility

TESTING CHECKLIST:

FRONTEND:
✓ All buttons are clickable and functional
✓ Forms validate input correctly
✓ Navigation works (all links, menus)
✓ Images load properly
✓ Responsive on all screen sizes
✓ No console errors
✓ Smooth animations/transitions
✓ Proper color contrast (accessibility)

BACKEND:
✓ All API endpoints respond correctly
✓ Error handling works (400, 404, 500 codes)
✓ CORS configured properly
✓ Input validation prevents bad data
✓ Database operations work (if applicable)
✓ Authentication/authorization (if applicable)
✓ No security vulnerabilities

INTEGRATION:
✓ Frontend successfully calls backend APIs
✓ Data flows correctly between frontend/backend
✓ Error messages display to user
✓ Loading states work properly

CALCULATOR-SPECIFIC TESTS:
✓ All number buttons (0-9) work
✓ Operators (+, -, *, /) calculate correctly
✓ Equals button produces right results
✓ Clear button resets display
✓ Division by zero shows error
✓ Decimal point works
✓ Memory functions (M+, M-, MR, MC) operate correctly

OUTPUT FORMAT:
Provide test results as:

TEST RESULTS:
===========

✅ PASSED:
- List of passing tests

❌ FAILED:
- List of failed tests with details

⚠️ WARNINGS:
- Potential issues or improvements

RECOMMENDATIONS:
- Suggested fixes for failed tests
- Performance improvements
- Security enhancements
"""

class TestAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Test Engineer",
            role="testing",
            system_prompt=TEST_SYSTEM_PROMPT
        )
    
    def test_frontend(self, html_code, requirements):
        """Test frontend code against requirements"""
        prompt = f"""Test this frontend code:

{html_code}

Requirements to validate:
{requirements}

Provide detailed test results."""
        
        return self.generate_response(prompt)
    
    def test_backend(self, api_code, endpoints):
        """Test backend API functionality"""
        prompt = f"""Test this Flask backend:

{api_code}

Expected endpoints:
{endpoints}

Check error handling, validation, and responses."""
        
        return self.generate_response(prompt)
    
    def test_integration(self, frontend_code, backend_code):
        """Test full-stack integration"""
        prompt = f"""Test integration between:

Frontend:
{frontend_code[:500]}...

Backend:
{backend_code[:500]}...

Verify data flow, error handling, and user experience."""
        
        return self.generate_response(prompt)
    
    def validate_accessibility(self, html_code):
        """Check accessibility compliance"""
        prompt = f"""Validate accessibility of this HTML:

{html_code}

Check ARIA labels, semantic HTML, keyboard navigation, and WCAG compliance."""
        
        return self.generate_response(prompt)
