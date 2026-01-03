"""Base Agent class with Groq integration"""
import os
from groq import Groq

class BaseAgent:
    def __init__(self, name, role, system_prompt):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        
    def generate_response(self, user_message, context=None, api_key=None):
        """Generate response using Llama via Groq (FREE)"""
        # Use provided API key or fallback to .env
        if not api_key:
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                print("ERROR: No API key provided to agent!")
                return "Error: No API key provided. Please register with your Groq API key."
        
        print(f"DEBUG: Agent using Groq API key: {api_key[:20]}...")
        
        # Create Groq client
        client = Groq(api_key=api_key)
        
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add context if available
        if context:
            messages.append({
                "role": "system", 
                "content": f"Context from previous interactions:\n{context}"
            })
        
        messages.append({"role": "user", "content": user_message})
        
        # Use Groq's free models (completely FREE, no credits needed)
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # High-quality model for better conversations
                messages=messages,
                temperature=0.7,
                max_tokens=2000  # Increased for better code generation
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = f"Error calling Groq API: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"API Key used: {api_key[:20]}...")
            return error_msg
    
    def extract_code(self, response):
        """Extract code blocks from response - improved version"""
        code_blocks = {}
        
        # Try to extract HTML with language tag
        if "```html" in response:
            html_start = response.find("```html") + 7
            html_end = response.find("```", html_start)
            if html_end > html_start:
                code_blocks['html'] = response[html_start:html_end].strip()
        # Try generic code blocks if no html tag
        elif "```" in response:
            # Find first code block (might be HTML without tag)
            code_start = response.find("```") + 3
            # Skip newline after ```
            if response[code_start] == '\n':
                code_start += 1
            code_end = response.find("```", code_start)
            if code_end > code_start:
                code_content = response[code_start:code_end].strip()
                # If it looks like HTML, treat it as HTML
                if '<' in code_content and '>' in code_content:
                    code_blocks['html'] = code_content
        # If no code blocks, check if entire response is HTML
        elif '<style>' in response or '<script>' in response or '<section' in response or '<header' in response or '<footer' in response:
            # The entire response is likely HTML code
            code_blocks['html'] = response.strip()
        
        # Extract CSS
        if "```css" in response:
            css_start = response.find("```css") + 6
            css_end = response.find("```", css_start)
            if css_end > css_start:
                code_blocks['css'] = response[css_start:css_end].strip()
        
        # Extract JavaScript
        if "```javascript" in response or "```js" in response:
            js_marker = "```javascript" if "```javascript" in response else "```js"
            js_start = response.find(js_marker) + len(js_marker)
            js_end = response.find("```", js_start)
            if js_end > js_start:
                code_blocks['js'] = response[js_start:js_end].strip()
        
        # Extract Python
        if "```python" in response:
            py_start = response.find("```python") + 9
            py_end = response.find("```", py_start)
            if py_end > py_start:
                code_blocks['python'] = response[py_start:py_end].strip()
        
        # Debug logging
        if code_blocks:
            print(f"✅ Extracted code blocks: {list(code_blocks.keys())}")
            if 'html' in code_blocks:
                print(f"   HTML length: {len(code_blocks['html'])} characters")
        else:
            print(f"⚠️ No code blocks extracted from response")
            print(f"   Response preview: {response[:200]}...")
        
        return code_blocks
