"""Authentication Manager with JWT + bcrypt"""
import bcrypt
import re
from datetime import datetime
from cryptography.fernet import Fernet
import os

class AuthManager:
    def __init__(self, rag_manager):
        self.rag_manager = rag_manager
        # Get encryption key from environment
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY not set in .env file")
        self.cipher = Fernet(encryption_key.encode())
    
    def validate_password(self, password):
        """Validate password requirements"""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        
        if not password[0].isupper():
            errors.append("First letter must be uppercase")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'checks': {
                'first_uppercase': password[0].isupper() if password else False,
                'min_length': len(password) >= 8,
                'has_number': bool(re.search(r'\d', password)),
                'has_special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
            }
        }
    
    def validate_api_key(self, api_key):
        """Validate Groq API key format"""
        if not api_key.startswith('gsk_'):
            return False, "API key must start with 'gsk_'"
        
        if len(api_key) < 30:
            return False, "API key must be at least 30 characters"
        
        return True, "Valid API key"
    
    def validate_name(self, name, field_name):
        """Validate name fields"""
        if not name or len(name.strip()) < 2:
            return False, f"{field_name} must be at least 2 characters"
        
        if not re.match(r'^[a-zA-Z\s]+$', name):
            return False, f"{field_name} can only contain letters"
        
        return True, "Valid"
    
    def hash_password(self, password):
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    
    def encrypt_api_key(self, api_key):
        """Encrypt API key for storage"""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key):
        """Decrypt API key for use"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
    
    def generate_username(self, first_name, last_name):
        """Generate username as firstname.lastname"""
        username = f"{first_name.lower()}.{last_name.lower()}"
        # Remove spaces and special chars
        username = re.sub(r'[^a-z.]', '', username)
        return username
    
    def register_user(self, first_name, middle_name, last_name, password, api_key):
        """Register new user"""
        # Validate first name
        valid, msg = self.validate_name(first_name, "First name")
        if not valid:
            return {'success': False, 'error': msg}
        
        # Validate last name
        valid, msg = self.validate_name(last_name, "Last name")
        if not valid:
            return {'success': False, 'error': msg}
        
        # Validate middle name if provided
        if middle_name:
            valid, msg = self.validate_name(middle_name, "Middle name")
            if not valid:
                return {'success': False, 'error': msg}
        
        # Validate password
        pwd_validation = self.validate_password(password)
        if not pwd_validation['valid']:
            return {'success': False, 'error': pwd_validation['errors'][0]}
        
        # Validate API key
        valid, msg = self.validate_api_key(api_key)
        if not valid:
            return {'success': False, 'error': msg}
        
        # Generate username
        username = self.generate_username(first_name, last_name)
        
        # Check if user exists
        existing_user = self.rag_manager.get_user(username)
        if existing_user:
            return {'success': False, 'error': 'User already exists. Please login.'}
        
        # Hash password and encrypt API key
        hashed_password = self.hash_password(password)
        encrypted_api_key = self.encrypt_api_key(api_key)
        
        # Store user in ChromaDB
        user_data = {
            'username': username,
            'first_name': first_name.strip(),
            'middle_name': middle_name.strip() if middle_name else '',
            'last_name': last_name.strip(),
            'password_hash': hashed_password,
            'api_key_encrypted': encrypted_api_key,
            'registered_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat()
        }
        
        self.rag_manager.store_user(user_data)
        
        return {
            'success': True,
            'username': username,
            'message': 'Registration successful!'
        }
    
    def login_user(self, username, password):
        """Authenticate user login"""
        # Get user from database
        user = self.rag_manager.get_user(username)
        
        if not user:
            return {'success': False, 'error': 'Invalid username or password'}
        
        # Verify password
        if not self.verify_password(password, user['password_hash']):
            return {'success': False, 'error': 'Invalid username or password'}
        
        # Update last login
        self.rag_manager.update_last_login(username)
        
        return {
            'success': True,
            'username': username,
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'message': 'Login successful!'
        }
    
    def get_user_api_key(self, username):
        """Get decrypted API key for user"""
        user = self.rag_manager.get_user(username)
        if not user:
            return None
        
        return self.decrypt_api_key(user['api_key_encrypted'])
    
    def mask_api_key(self, api_key):
        """Mask API key for display (sk-****...****)"""
        if len(api_key) < 10:
            return api_key
        
        return f"{api_key[:3]}{'*' * (len(api_key) - 7)}{api_key[-4:]}"
