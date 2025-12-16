# AIDevs - Production-Ready Authentication System

## 🎉 What's New

AIDevs now features a **complete authentication system** with:

- ✅ User registration with Three.js animated pages
- ✅ JWT-based login/logout
- ✅ Personal OpenRouter API key management
- ✅ Secure password hashing (bcrypt)
- ✅ Encrypted API key storage
- ✅ Protected chatbot routes
- ✅ Session persistence across logins

## 🚀 Quick Start

### 1. Install Dependencies

**Backend:**

```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**

```bash
cd react-version
npm install
```

### 2. Configure Environment

Create `backend/.env`:

```env
# OpenRouter API Key (fallback for testing)
OPENROUTER_API_KEY=your-default-key-here

# JWT Secret (CHANGE IN PRODUCTION!)
JWT_SECRET_KEY=your-super-secret-jwt-key-here

# Encryption Key (Auto-generated on first run)
ENCRYPTION_KEY=
```

### 3. Run the Application

**Terminal 1 - Backend:**

```bash
cd backend
python app.py
```

**Terminal 2 - Frontend:**

```bash
cd react-version
npm start
```

## 🔐 Authentication Flow

### Registration (`/register`)

1. **Navigate to** `http://localhost:3000/register`
2. **Fill in the form:**

   - First Name (required, min 2 chars)
   - Middle Name (optional)
   - Last Name (required, min 2 chars)
   - Password with real-time validation:
     - ✓ First letter uppercase
     - ✓ Minimum 8 characters
     - ✓ Contains number
     - ✓ Contains special character
   - OpenRouter API Key (starts with "sk-", min 20 chars)

3. **Username auto-generated:** `firstname.lastname`
4. **On success:** JWT token created → redirect to `/chatbot`

### Login (Homepage Modal)

1. **Click "Login"** button in header
2. **Enter credentials:**

   - Username (firstname.lastname)
   - Password

3. **On success:** "Login successful!" → redirect to `/chatbot`

### Chatbot Usage (Protected Route)

- **Requires:** Valid JWT token
- **Features:**
  - Uses YOUR OpenRouter API key for all LLM calls
  - Session ID format: `username_session`
  - Conversation history linked to your account
  - Download websites as: `aidevs_username_website.zip`

## 🛡️ Security Features

### Password Security

- **Hashing:** bcrypt with salt
- **Storage:** Only password hash stored, never plain text
- **Validation:** Enforced strong password requirements

### API Key Security

- **Encryption:** Fernet symmetric encryption
- **Storage:** Encrypted in ChromaDB
- **Decryption:** Only when making LLM calls
- **Display:** Masked as `sk-****...****`

### JWT Authentication

- **Algorithm:** HS256
- **Expiration:** 24 hours
- **Storage:** localStorage (client-side)
- **Validation:** Required for all chatbot endpoints

### Protected Endpoints

```
POST /api/chat         - Requires JWT
POST /api/preview      - Requires JWT
POST /api/download     - Requires JWT
POST /api/reset        - Requires JWT
```

### Public Endpoints

```
POST /api/auth/register           - Create account
POST /api/auth/login              - Authenticate user
POST /api/auth/validate-password  - Real-time validation
GET  /api/health                  - Health check
```

## 📊 Database Schema (ChromaDB)

### Users Collection

```python
{
    'username': 'john.doe',
    'first_name': 'John',
    'middle_name': '',
    'last_name': 'Doe',
    'password_hash': 'bcrypt_hash_here',
    'api_key_encrypted': 'fernet_encrypted_key',
    'registered_at': '2025-12-12T10:30:00',
    'last_login': '2025-12-12T14:45:00'
}
```

### Conversations Collection

```python
{
    'session_id': 'john.doe_session',
    'agent': 'lead',
    'stage': 'hero',
    'message': 'User message',
    'response': 'Agent response',
    'timestamp': '2025-12-12T14:46:00'
}
```

## 🎨 UI/UX Features

### Three.js Registration Page

- **Background:** Animated particles + geometric shapes
- **Design:** Glassmorphism with black backdrop
- **Validation:** Real-time password strength indicator
- **Responsive:** Mobile-friendly design

### Login Modal

- **Trigger:** "Login" button in header (right side)
- **Animation:** Slide-up with Three.js background
- **Features:**
  - Close button (top-right)
  - Link to registration
  - Error handling with user-friendly messages

### Header Updates

- **Logged Out:** Shows "Login" + "Get Started" buttons
- **Logged In:** Shows "Hi, [firstname]" + "Logout" + "Get Started"
- **Smart Redirect:**
  - If not logged in → "Get Started" → `/register`
  - If logged in → "Get Started" → `/chatbot`

## 🔧 API Usage Examples

### Register New User

```javascript
const response = await fetch("http://localhost:5000/api/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    firstName: "John",
    middleName: "",
    lastName: "Doe",
    password: "SecurePass123!",
    apiKey: "sk-or-v1-your-openrouter-key",
  }),
});

const data = await response.json();
// Returns: { success: true, username: 'john.doe', token: 'jwt_token', message: '...' }
```

### Login User

```javascript
const response = await fetch("http://localhost:5000/api/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    username: "john.doe",
    password: "SecurePass123!",
  }),
});

const data = await response.json();
// Returns: { success: true, username: 'john.doe', firstName: 'John', token: 'jwt_token' }
```

### Send Chat Message (Protected)

```javascript
const token = localStorage.getItem("aidevs_token");

const response = await fetch("http://localhost:5000/api/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({
    message: "Build me a portfolio website",
  }),
});
```

## 🏗️ Architecture Updates

### Multi-Agent System with User API Keys

```
User Login
    ↓
JWT Token Generated
    ↓
User's Encrypted API Key Retrieved
    ↓
Orchestrator Uses User's Key for All Agent Calls
    ↓
Lead Agent → Frontend Agent → Backend Agent → Test Agent
    ↓
All use SAME USER's OpenRouter API Key
```

### Benefits

1. **Cost Control:** Each user pays for their own API usage
2. **Privacy:** User's API key never shared
3. **Scalability:** No central API key rate limits
4. **Transparency:** Users see their own API usage on OpenRouter

## 🎯 Production Checklist

Before deploying to production:

### Security

- [ ] Change `JWT_SECRET_KEY` to strong random string
- [ ] Generate unique `ENCRYPTION_KEY` (Fernet.generate_key())
- [ ] Use HTTPS for all API calls
- [ ] Implement rate limiting on auth endpoints
- [ ] Add CORS whitelist for production domain

### Database

- [ ] Set up persistent ChromaDB storage
- [ ] Implement backup strategy
- [ ] Add indexes for faster queries

### Frontend

- [ ] Build React app: `npm run build`
- [ ] Serve static files with Nginx/Apache
- [ ] Update API URLs from localhost to production domain

### Backend

- [ ] Use production WSGI server (Gunicorn/uWSGI)
- [ ] Set Flask `ENV=production`
- [ ] Implement logging and monitoring
- [ ] Set up error tracking (Sentry, etc.)

### Optional Enhancements

- [ ] Add password reset via email
- [ ] Implement 2FA authentication
- [ ] Add session timeout warnings
- [ ] Profile page to update API key
- [ ] Usage analytics dashboard

## 🐛 Troubleshooting

### "Invalid username or password"

- Ensure username is lowercase: `firstname.lastname`
- Check password meets all requirements
- Verify user is registered

### "User API key not found"

- User must be logged in
- JWT token must be valid
- Check localStorage for `aidevs_token`

### JWT Errors

- Token expired (24hr limit) → Login again
- Invalid token → Clear localStorage and re-login
- Missing Authorization header → Check fetch headers

### Three.js Not Rendering

- Check browser console for errors
- Ensure Three.js is installed: `npm install three`
- WebGL must be enabled in browser

## 📝 Notes

- **Username Format:** Always `firstname.lastname` (auto-generated, lowercase)
- **API Key Masking:** Displayed as `sk-****...****` for security
- **Session Persistence:** Login persists across page refreshes
- **Logout:** Clears tokens and redirects to homepage
- **Password Requirements:** Strictly enforced on both frontend and backend

## 🎓 Educational Value

This authentication system demonstrates:

1. **Full-stack authentication** (JWT + bcrypt)
2. **Secure credential storage** (encryption)
3. **Protected API routes** with middleware
4. **Real-time form validation** with React
5. **Three.js integration** for stunning visuals
6. **localStorage management** for session persistence
7. **RESTful API design** for auth flows

---

**Built with:** Python Flask, React, Three.js, JWT, bcrypt, ChromaDB, OpenRouter API

**Ready for production!** 🚀
