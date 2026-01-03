# 🤖 AIDevs - AI-Powered Full-Stack Website Builder

Multi-agent AI system that generates complete websites with both frontend and backend code, automatically integrated and ready to deploy.

## 🌟 Features

- **Multi-Agent Architecture** - Lead agent, frontend, backend, and testing agents work together
- **Full-Stack Generation** - Generates HTML/CSS/JS frontend + Flask backend API
- **User Authentication** - Secure JWT-based auth with bcrypt password hashing
- **Personal API Keys** - Each user can use their own Groq API key
- **Real-time Preview** - See your website as it's being built
- **Downloadable Package** - Get complete ZIP with frontend, backend, and tests
- **Production Ready** - Deploy to Render, Heroku, or any cloud platform

## 🚀 Quick Deploy to Render

**Choose your guide:**

- 🏃 **[Quick Start (10 min)](QUICK_START_RENDER.md)** - Fastest way to deploy
- 📋 **[Deployment Checklist](DEPLOYMENT_CHECKLIST.md)** - Step-by-step with troubleshooting
- 📚 **[Full Documentation](RENDER_DEPLOYMENT.md)** - Complete deployment guide

## 🛠️ Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Groq API key

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your Groq API key
# Generate encryption key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Run backend
python app.py
```

Backend runs on `http://localhost:5000`

### Frontend Setup

```bash
cd react-version

# Install dependencies
npm install

# Run frontend
npm start
```

Frontend runs on `http://localhost:3000`

## 📁 Project Structure

````
react-version/
├── backend/                    # Flask backend
│   ├── app.py                 # Main Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── Procfile              # Render deployment config
│   ├── runtime.txt           # Python version
│   ├── agents/               # AI agent system
│   │   ├── orchestrator.py  # Main orchestrator
│   │   ├── lead_agent.py    # Conversation manager
│   │   ├── frontend_agent.py
│   │   ├── backend_agent.py
│   │   └── test_agent.py
│   └── utils/
│       ├── auth_manager.py   # Authentication
│       └── rag_manager.py    # ChromaDB integration
├── src/                       # React frontend
│   ├── components/
│   │   ├── ChatbotPage.js   # Main chatbot interface
│   │   ├── RegisterPage.js  # User registration
│   │   └── ...
│   └── config.js             # API configuration
├── public/
├── render.yaml               # Render blueprint
└── package.json

## 🔐 Environment Variables

### Backend (.env)

```bash
# Required
GROQ_API_KEY=your-groq-api-key
ENCRYPTION_KEY=your-encryption-key

# Auto-generated (production)
JWT_SECRET_KEY=auto-generated-by-render

# Optional
FLASK_ENV=production
CORS_ORIGINS=https://your-frontend-url.onrender.com
````

### Frontend

```bash
REACT_APP_API_URL=https://your-backend-url.onrender.com
```

## 🎯 How It Works

1. **User describes website** → Lead agent manages conversation
2. **Frontend generation** → Frontend agent creates HTML/CSS/JS sections
3. **Backend generation** → Backend agent creates Flask API automatically
4. **Testing** → Test agent validates responsiveness and functionality
5. **Download** → User gets complete full-stack package

## 📦 Deployment Files

- **`render.yaml`** - Blueprint for deploying all services at once
- **`Procfile`** - Tells Render how to start the backend
- **`runtime.txt`** - Specifies Python version
- **`backend/.env.example`** - Template for environment variables

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd react-version
npm test
```

## 📚 Documentation

- [Quick Start Guide](QUICK_START_RENDER.md) - Get started fast
- [Deployment Checklist](DEPLOYMENT_CHECKLIST.md) - Pre-deployment prep
- [Full Render Guide](RENDER_DEPLOYMENT.md) - Complete deployment documentation
- [Authentication Guide](AUTHENTICATION_README.md) - Auth system details
- [Architecture Guide](backend/ARCHITECTURE.md) - System design

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 💬 Support

- Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/aidevs/issues)
- Discussions: [GitHub Discussions](https://github.com/YOUR_USERNAME/aidevs/discussions)

## 🙏 Acknowledgments

- **Groq** - Fast LLM inference
- **Render** - Easy deployment platform
- **Flask** - Python web framework
- **React** - Frontend framework
- **ChromaDB** - Vector database for RAG

---

**Built with ❤️ by the AIDevs Team**
