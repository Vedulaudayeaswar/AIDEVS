"""Backend Engineer Agent - Generates Flask/Python backend code"""
from .base_agent import BaseAgent

BACKEND_SYSTEM_PROMPT = """You are a Backend Engineer generating production-ready Flask APIs.

CRITICAL: Generate COMPLETE, RUNNABLE code that works immediately.

YOUR OUTPUT MUST BE PURE PYTHON CODE with these components:

1. ALL imports at the top
2. Flask app initialization with CORS
3. ALL route handlers with full implementation
4. Error handling in every endpoint
5. Input validation
6. if __name__ == '__main__' block

TEMPLATE STRUCTURE:
```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/contact', methods=['POST'])
def contact():
    try:
        data = request.json
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()
        
        if not all([name, email, message]):
            return jsonify({'success': False, 'error': 'All fields required'}), 400
        
        # Email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'success': False, 'error': 'Invalid email'}), 400
        
        return jsonify({'success': True, 'message': 'Thank you for contacting us!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

GENERATE ONLY CODE - NO EXPLANATIONS, NO MARKDOWN, JUST RUNNABLE PYTHON.
"""

class BackendAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Backend Engineer",
            role="backend",
            system_prompt=BACKEND_SYSTEM_PROMPT
        )
    
    def generate_api(self, frontend_requirements, context=None):
        """Generate Flask API based on frontend needs"""
        prompt = f"""Generate a complete Flask backend API for this website:

{frontend_requirements}

REQUIRED ENDPOINTS:
- GET /api/health - Health check
- POST /api/contact - Contact form handler
- POST /api/subscribe - Newsletter subscription
- Add any other relevant endpoints based on the website type

Generate COMPLETE, PRODUCTION-READY Flask code that:
1. Includes ALL imports
2. Has CORS enabled
3. Validates all inputs
4. Handles errors properly
5. Returns JSON responses
6. Can run immediately with: python app.py

OUTPUT ONLY THE PYTHON CODE, NO EXPLANATIONS."""
        
        response = self.generate_response(prompt, context)
        
        # Extract code from potential markdown code blocks
        if '```python' in response:
            code_start = response.find('```python') + 9
            code_end = response.find('```', code_start)
            if code_end > code_start:
                response = response[code_start:code_end].strip()
        elif '```' in response:
            code_start = response.find('```') + 3
            code_end = response.find('```', code_start)
            if code_end > code_start:
                response = response[code_start:code_end].strip()
        
        return response
    
    def generate_database_models(self, requirements):
        """Generate SQLAlchemy models"""
        prompt = f"""Create SQLAlchemy database models for:

{requirements}

Include relationships, constraints, and proper field types."""
        
        return self.generate_response(prompt)
    
    def integrate_with_frontend(self, frontend_code, api_code):
        """Generate integration instructions"""
        prompt = f"""Provide integration steps for connecting this frontend:

{frontend_code[:500]}...

With this backend API:

{api_code[:500]}...

Include fetch() examples and CORS setup."""
        
        return self.generate_response(prompt)
