"""Multi-Agent Orchestrator for AIDevs - Simplified version"""
from .lead_agent import LeadAgent
from .frontend_agent import FrontendAgent
from .backend_agent import BackendAgent
from .test_agent import TestAgent

class AIDevsOrchestrator:
    def __init__(self, rag_manager):
        self.rag_manager = rag_manager
        self.frontend_agent = FrontendAgent()
        self.backend_agent = BackendAgent()
        self.test_agent = TestAgent()
        self.sessions = {}
    
    def process_message(self, user_message, session_id, api_key=None):
        try:
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    'current_stage': 'initial',
                    'frontend_code': {},
                    'backend_code': '',
                    'test_results': '',
                    'conversation_history': [],
                    'api_key': api_key,
                    'lead_agent': LeadAgent()  # Each session gets its own lead agent
                }
            
            session = self.sessions[session_id]
            
            # Update API key if provided
            if api_key:
                session['api_key'] = api_key
            
            # Use user's API key for agents
            user_api_key = session.get('api_key')
            
            rag_context = self.rag_manager.retrieve_context(user_message, session_id)
            result = session['lead_agent'].process_request(
                user_message, rag_context, user_api_key
            )
            
            self.rag_manager.store_interaction(
                session_id=session_id,
                agent='lead',
                message=user_message,
                response=result['response'],
                stage=result['stage']
            )
            
            session['current_stage'] = result['stage']
            
            if result['next_agent'] == 'frontend':
                section = self._determine_section(result['stage'])
                print(f"🎨 Generating {section} section...")
                
                frontend_result = self.frontend_agent.generate_section(
                    section,
                    user_message,
                    session['frontend_code'],
                    user_api_key
                )
                
                print(f"📦 Frontend result: {type(frontend_result)}")
                if frontend_result:
                    print(f"   - Has 'code' key: {'code' in frontend_result}")
                    if 'code' in frontend_result:
                        print(f"   - Code keys: {list(frontend_result['code'].keys())}")
                        print(f"   - HTML present: {'html' in frontend_result['code']}")
                        if 'html' in frontend_result['code']:
                            html_length = len(frontend_result['code'].get('html', ''))
                            print(f"   - HTML length: {html_length} characters")
                
                if frontend_result and 'code' in frontend_result:
                    html_code = frontend_result['code'].get('html', '')
                    if html_code:
                        session['frontend_code'][section] = html_code
                        print(f"✅ Stored {section} section ({len(html_code)} chars)")
                    else:
                        print(f"⚠️ No HTML code in {section} section!")
                    
                    self.rag_manager.store_interaction(
                        session_id=session_id,
                        agent='frontend',
                        message=f"Generated {section} section",
                        response=str(frontend_result.get('response', ''))[:500],
                        stage=result['stage']
                    )
                else:
                    print(f"❌ Frontend generation failed for {section}")
                    
                    # Advance lead agent stage after successful frontend build
                    # This triggers the lead agent to ask for the next section
                    next_stage_result = session['lead_agent'].process_request(
                        f"Section {section} complete",
                        rag_context,
                        user_api_key
                    )
                    
                    # Auto-trigger backend and test after footer is complete
                    if result['stage'] == 'footer':
                        print("\n" + "="*60)
                        print("🎉 FOOTER COMPLETED! AUTO-GENERATING BACKEND & TESTS")
                        print("="*60)
                        
                        # Generate backend API
                        combined_html = self.frontend_agent.combine_sections(session['frontend_code'])
                        
                        # Create detailed requirements for backend
                        website_type = session.get('website_type', 'general')
                        backend_requirements = f"""Create a production-ready Flask backend API for this {website_type} website.

FRONTEND STRUCTURE:
{combined_html[:1500]}

REQUIRED FEATURES:
1. Contact form endpoint (POST /api/contact) - validate name, email, message
2. Newsletter subscription (POST /api/subscribe) - validate email
3. CORS configuration for frontend
4. Input validation and error handling
5. JSON responses with proper status codes
6. Health check endpoint (GET /api/health)

Generate COMPLETE, PRODUCTION-READY Flask code that can run immediately."""
                        
                        print("📡 Calling Backend Agent...")
                        backend_response = self.backend_agent.generate_api(
                            frontend_requirements=backend_requirements,
                            context=user_api_key
                        )
                        
                        # Extract code from response
                        if backend_response:
                            session['backend_code'] = backend_response
                            self.rag_manager.store_interaction(
                                session_id=session_id,
                                agent='backend',
                                message="Auto-generated backend after footer completion",
                                response=backend_response[:500],
                                stage='backend_generation'
                            )
                            print(f"✅ Backend API generated: {len(backend_response)} characters")
                            print(f"   Preview: {backend_response[:150]}...")
                        else:
                            print("❌ Backend generation returned empty!")
                        
                        # Run tests
                        print("🧪 Running frontend tests...")
                        test_result = self.test_agent.test_frontend(
                            html_code=combined_html,
                            requirements="Validate responsive design, accessibility, and functionality"
                        )
                        
                        if test_result:
                            session['test_results'] = test_result
                            self.rag_manager.store_interaction(
                                session_id=session_id,
                                agent='test',
                                message="Auto-ran tests after footer completion",
                                response=str(test_result)[:500],
                                stage='testing'
                            )
                            print(f"✅ Tests completed: {len(str(test_result))} characters")
                            print(f"   Preview: {str(test_result)[:150]}...")
                        else:
                            print("❌ Test generation returned empty!")
                        
                        print("="*60)
                        print(f"📊 SUMMARY:")
                        print(f"   Frontend: {len(combined_html)} chars")
                        print(f"   Backend: {len(session.get('backend_code', ''))} chars")
                        print(f"   Tests: {len(str(session.get('test_results', '')))} chars")
                        print("="*60 + "\n")
                        
                        # Use the next stage result message
                        result['response'] = next_stage_result.get('response', result['response'])
                    else:
                        # For non-footer sections, use the next prompt from lead agent
                        result['response'] = next_stage_result.get('response', result['response'])
            
            return {
                'message': result['response'],
                'stage': result['stage'],
                'has_preview': bool(session['frontend_code'])
            }
        except Exception as e:
            import traceback
            print("ERROR in orchestrator.process_message:")
            print(traceback.format_exc())
            raise
    
    def _determine_section(self, stage):
        stage_to_section = {
            'header': 'header',
            'hero': 'hero',
            'features': 'features',
            'footer': 'footer'
        }
        return stage_to_section.get(stage, 'header')
    
    def get_preview_code(self, session_id):
        if session_id not in self.sessions:
            return {'html': '', 'css': '', 'js': ''}
        
        frontend_code = self.sessions[session_id].get('frontend_code', {})
        
        # Debug: Show what sections we have
        print(f"🔍 Preview requested - Available sections: {list(frontend_code.keys())}")
        for section, code in frontend_code.items():
            print(f"   - {section}: {len(code)} characters")
            if len(code) < 50:
                print(f"     ⚠️ Section too short! Content: {code[:100]}")
        
        combined_html = self.frontend_agent.combine_sections(frontend_code)
        print(f"📄 Combined HTML length: {len(combined_html)} characters")
        
        return {'html': combined_html, 'css': '', 'js': ''}
    
    def generate_download_package(self, session_id):
        import zipfile, io, os
        if session_id not in self.sessions:
            return None
        session = self.sessions[session_id]
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add frontend code
            frontend_code = session.get('frontend_code', {})
            combined_html = self.frontend_agent.combine_sections(frontend_code)
            zip_file.writestr('frontend/index.html', combined_html)
            
            # Add backend code if available
            backend_code = session.get('backend_code', '')
            if backend_code:
                zip_file.writestr('backend/app.py', backend_code)
                zip_file.writestr('backend/requirements.txt', 'flask==3.0.0\nflask-cors==4.0.0\n')
                zip_file.writestr('backend/.env.example', '# Add your environment variables here\nFLASK_ENV=development\n')
            
            # Add test results if available
            test_results = session.get('test_results', '')
            if test_results:
                zip_file.writestr('TEST_RESULTS.md', f"""# Test Results

{test_results}

Generated by AIDevs Test Agent
""")
            
            # Create comprehensive README
            readme = """# AIDevs Website Package

## 📁 Project Structure
```
/
├── frontend/
│   └── index.html          # Your complete website
├── backend/
│   ├── app.py              # Flask API server
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment variables template
└── TEST_RESULTS.md         # Quality assurance report

```

## 🚀 Getting Started

### Frontend
1. Open `frontend/index.html` in any web browser
2. Your website is ready to use!

### Backend (if included)
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run the server:
   ```bash
   python app.py
   ```

6. Your API will be available at `http://localhost:5000`

## 📋 Test Results
Check `TEST_RESULTS.md` for comprehensive quality assurance report.

## 🎯 Features
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Modern UI/UX
- ✅ Full-stack ready (if backend included)
- ✅ Production-ready code
- ✅ Comprehensive testing

---
**Generated by AIDevs** - Your AI-powered development assistant
Visit: https://aidevs.example.com
"""
            zip_file.writestr('README.md', readme)
        
        # Save to downloads folder
        zip_filename = f'aidevs_{session_id}.zip'
        zip_path = os.path.join('downloads', zip_filename)
        os.makedirs('downloads', exist_ok=True)
        with open(zip_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        return zip_filename
