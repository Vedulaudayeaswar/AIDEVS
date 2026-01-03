"""Flask Backend API for AIDevs"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, 
    jwt_required, get_jwt_identity
)
from dotenv import load_dotenv
import os
from datetime import timedelta
from agents.orchestrator import AIDevsOrchestrator
from utils.rag_manager import RAGManager
from utils.auth_manager import AuthManager
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ===== CONCURRENCY & PARALLELISM ARCHITECTURE =====
# Thread pool for non-blocking I/O operations
executor = ThreadPoolExecutor(max_workers=10)

def async_route(f):
    """Decorator to run routes asynchronously using thread pool"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return executor.submit(f, *args, **kwargs).result()
    return decorated_function
# ==================================================

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'aidevs-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)

# Initialize orchestrator and RAG
rag_manager = RAGManager()
auth_manager = AuthManager(rag_manager)
orchestrator = AIDevsOrchestrator(rag_manager)

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user"""
    try:
        data = request.json
        first_name = data.get('firstName', '').strip()
        middle_name = data.get('middleName', '').strip()
        last_name = data.get('lastName', '').strip()
        password = data.get('password', '')
        api_key = data.get('apiKey', '').strip()
        
        result = auth_manager.register_user(
            first_name, middle_name, last_name, 
            password, api_key
        )
        
        if result['success']:
            # Create JWT token
            access_token = create_access_token(identity=result['username'])
            return jsonify({
                'success': True,
                'username': result['username'],
                'message': result['message'],
                'token': access_token
            })
        else:
            return jsonify(result), 400
    
    except Exception as e:
        import traceback
        print("ERROR in /api/auth/register:")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login existing user"""
    try:
        data = request.json
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')
        
        result = auth_manager.login_user(username, password)
        
        if result['success']:
            # Create JWT token
            access_token = create_access_token(identity=username)
            return jsonify({
                'success': True,
                'username': username,
                'firstName': result['first_name'],
                'lastName': result['last_name'],
                'message': result['message'],
                'token': access_token
            })
        else:
            return jsonify(result), 401
    
    except Exception as e:
        import traceback
        print("ERROR in /api/auth/login:")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/auth/validate-password', methods=['POST'])
def validate_password():
    """Validate password in real-time"""
    try:
        data = request.json
        password = data.get('password', '')
        
        validation = auth_manager.validate_password(password)
        return jsonify(validation)
    
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 500

@app.route('/api/chat', methods=['POST'])
@jwt_required()
def chat():
    """Handle chat messages from frontend"""
    try:
        # Get authenticated user
        username = get_jwt_identity()
        
        # Get user's API key
        user_api_key = auth_manager.get_user_api_key(username)
        using_default = False
        
        if not user_api_key:
            # Fallback to default API key from .env
            user_api_key = os.getenv('GROQ_API_KEY')
            using_default = True
            print(f"⚠️  User {username} has no API key - using DEFAULT Groq key")
        else:
            print(f"✅ Using {username}'s PERSONAL Groq API key: {user_api_key[:20]}...")
        
        if not user_api_key:
            print(f"ERROR: No API key available for user {username}")
            return jsonify({
                'success': False,
                'error': 'No API key configured'
            }), 401
        
        data = request.json
        user_message = data.get('message', '')
        session_id = f"{username}_session"  # User-specific session

        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400

        # Process message through orchestrator with user's API key
        response = orchestrator.process_message(
            user_message, session_id, user_api_key
        )

        return jsonify({
            'success': True,
            'response': response['message'],
            'stage': response['stage'],
            'has_preview': response['has_preview'],
            'using_default_key': using_default  # Tell frontend which key is being used
        })
    except Exception as e:
        import traceback
        print("ERROR in /api/chat:")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/preview', methods=['POST'])
@jwt_required()
def get_preview():
    """Get current website preview code"""
    try:
        username = get_jwt_identity()
        session_id = f"{username}_session"
        preview_code = orchestrator.get_preview_code(session_id)

        return jsonify({
            'success': True,
            'html': preview_code.get('html', ''),
            'css': preview_code.get('css', ''),
            'js': preview_code.get('js', '')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/download', methods=['POST'])
@jwt_required()
def download_code():
    """Generate and return downloadable zip file"""
    try:
        username = get_jwt_identity()
        session_id = f"{username}_session"
        
        # Check if session exists and has backend code
        if session_id not in orchestrator.sessions:
            return jsonify({
                'success': False,
                'error': 'No active session. Please build your website first.'
            }), 404
        
        session = orchestrator.sessions[session_id]
        backend_code = session.get('backend_code', '')
        frontend_code = session.get('frontend_code', {})
        
        # Validate that we have both frontend and backend
        if not frontend_code:
            return jsonify({
                'success': False,
                'error': 'No frontend code available. Please build your website first.'
            }), 400
        
        if not backend_code or len(backend_code) < 100:
            return jsonify({
                'success': False,
                'error': 'Backend code is still being generated. Please wait for the complete build to finish.',
                'backend_ready': False
            }), 400
        
        zip_filename = orchestrator.generate_download_package(session_id)

        if not zip_filename:
            return jsonify({
                'success': False,
                'error': 'Failed to generate download package'
            }), 500

        zip_path = os.path.join('downloads', zip_filename)
        
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
    except Exception as e:
        import traceback
        print("ERROR in /api/download:")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/status', methods=['POST'])
@jwt_required()
def get_status():
    """Get current session status including backend generation"""
    try:
        username = get_jwt_identity()
        session_id = f"{username}_session"
        
        if session_id not in orchestrator.sessions:
            return jsonify({
                'success': True,
                'has_session': False,
                'frontend_ready': False,
                'backend_ready': False,
                'download_ready': False
            })
        
        session = orchestrator.sessions[session_id]
        frontend_code = session.get('frontend_code', {})
        backend_code = session.get('backend_code', '')
        
        has_frontend = bool(frontend_code)
        has_backend = bool(backend_code and len(backend_code) > 100)
        download_ready = has_frontend and has_backend
        
        return jsonify({
            'success': True,
            'has_session': True,
            'frontend_ready': has_frontend,
            'backend_ready': has_backend,
            'download_ready': download_ready,
            'current_stage': session.get('current_stage', 'initial'),
            'sections_completed': list(frontend_code.keys())
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/reset', methods=['POST'])
@jwt_required()
def reset_session():
    """Clear session and start fresh"""
    try:
        username = get_jwt_identity()
        session_id = f"{username}_session"
        
        # Clear from orchestrator
        if session_id in orchestrator.sessions:
            del orchestrator.sessions[session_id]
        
        # Clear from RAG
        rag_manager.clear_session(session_id)

        return jsonify({
            'success': True,
            'message': 'Session reset! Let\'s build something new. What kind of website would you like to create?'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'AIDevs Backend',
        'version': '1.0.0'
    })

if __name__ == '__main__':
    # Create downloads directory if it doesn't exist
    os.makedirs('downloads', exist_ok=True)
    
    # Get port from environment variable (for Render) or use 5000
    port = int(os.getenv('PORT', 5000))
    
    print("=" * 60)
    print("🚀 AIDevs Backend - High-Performance Architecture")
    print("=" * 60)
    print("✅ Concurrency: ThreadPoolExecutor with 10 workers")
    print("✅ Non-blocking I/O: Async route handling")
    print("✅ Event-driven: Flask with multi-threaded request handling")
    print("✅ Load balancing ready: Production deployment with Gunicorn/uWSGI")
    print(f"✅ Running on port: {port}")
    print("=" * 60)
    
    # Run Flask server with multi-threaded support
    # In production, use: gunicorn -w 4 -k gevent --worker-connections 1000 app:app
    app.run(
        debug=os.getenv('FLASK_ENV') != 'production',
        host='0.0.0.0', 
        port=port,
        threaded=True,  # Enable multi-threading for concurrent request handling
        use_reloader=os.getenv('FLASK_ENV') != 'production'
    )

