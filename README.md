# 🤖 AIDevs - AI-Powered Full-Stack Website Builder

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-000000.svg)
![Python](https://img.shields.io/badge/Python-3.8+-3776ab.svg)

> Transform your ideas into production-ready websites through conversational AI. No coding required.

[Live Demo](#) | [Documentation](#documentation) | [Report Bug](#) | [Request Feature](#)

---

## 📋 Table of Contents

- [About The Project](#about-the-project)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Setup](#environment-setup)
- [Usage](#usage)
- [Deployment](#deployment)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## 🎯 About The Project

**AIDevs** is an intelligent web development platform that uses multi-agent AI to build complete full-stack websites through natural conversation. Simply describe your vision, and our AI agents guide you through creating professional-grade websites with modern designs, backend APIs, and comprehensive tests.

### **How It Works:**

1. **Register** with your Groq API key (securely encrypted and stored)
2. **Chat** with AI agents about your website idea
3. **Build** sections step-by-step (Header → Hero → Features → Footer)
4. **Preview** your website in real-time
5. **Download** complete full-stack project (HTML/CSS/JS + Flask backend + Tests)
6. **Deploy** with included instructions

---

## ✨ Features

### **🤖 AI-Powered Generation**

- **Multi-Agent System**: Lead, Frontend, Backend, and Test agents work together
- **Conversational UI**: Natural language interactions with contextual suggestions
- **Intelligent Design**: Framer.ai-quality aesthetics with glassmorphism, gradients, animations
- **RAG Context**: Uses conversation history for personalized recommendations

### **🔐 Secure Authentication**

- JWT token-based authentication (24-hour sessions)
- bcrypt password hashing
- Fernet-encrypted API key storage
- Per-user API key management

### **⚡ High Performance**

- ThreadPoolExecutor with 10 concurrent workers
- Multi-threaded request handling
- Event-driven architecture (Gunicorn + Gevent)
- Handles 1000+ concurrent connections

### **🎨 Modern Frontend**

- React 18 with Three.js animations
- Responsive, mobile-first design
- Real-time preview panel
- Glassmorphism and gradient effects

### **📦 Complete Project Output**

- Production-ready HTML/CSS/JavaScript
- Flask backend with RESTful API
- Contact/Subscribe endpoints
- Comprehensive test suite
- Deployment instructions

---

## 🛠️ Tech Stack

### **Frontend**

- [React 18](https://react.dev/) - Component-based UI library
- [Three.js](https://threejs.org/) - 3D graphics and animations
- Modern CSS3 - Glassmorphism, gradients, scroll effects
- Responsive Design - Mobile-first approach

### **Backend**

- [Flask 3.0](https://flask.palletsprojects.com/) - Python web framework
- [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/) - Authentication
- [Flask-CORS](https://flask-cors.readthedocs.io/) - Cross-origin support
- [Gunicorn](https://gunicorn.org/) + [Gevent](http://www.gevent.org/) - Production server

### **AI/ML**

- [Groq API](https://groq.com/) - Ultra-fast LLM inference
- Llama 3.3 70B Versatile - High-quality conversational model
- [ChromaDB](https://www.trychroma.com/) - Vector database for RAG
- [Sentence Transformers](https://www.sbert.net/) - Embedding generation

### **Security**

- [bcrypt](https://github.com/pyca/bcrypt/) - Password hashing
- [Cryptography (Fernet)](https://cryptography.io/) - API key encryption
- JWT - Stateless authentication

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **Node.js 16+** - [Download](https://nodejs.org/)
- **npm or yarn** - Comes with Node.js
- **Groq API Key** - [Get yours free](https://console.groq.com/)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/AIDevs.git
   cd AIDevs
   ```

2. **Backend Setup**

   ```bash
   cd react-version/backend

   # Create virtual environment (recommended)
   python -m venv venv

   # Activate virtual environment
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd ../  # Go back to react-version folder
   npm install
   ```

### Environment Setup

Create a `.env` file in `react-version/backend/`:

```env
# Backend Configuration
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
FLASK_ENV=development

# Database
CHROMA_PERSIST_DIR=./chroma_db

# Encryption Key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
FERNET_KEY=your_fernet_encryption_key_here
```

**Generate Fernet Key:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 💻 Usage

### Development Mode

**1. Start Backend Server**

```bash
cd react-version/backend
python app.py
```

Backend runs on: `http://localhost:5000`

**2. Start Frontend (in new terminal)**

```bash
cd react-version
npm start
```

Frontend runs on: `http://localhost:3000`

**3. Access the Application**

- Open browser: `http://localhost:3000`
- Register with your Groq API key
- Start building your website!

### Production Mode

**Backend (with Gunicorn):**

```bash
cd react-version/backend
bash start_production.sh
# Or manually:
gunicorn -w 4 -k gevent --worker-connections 1000 --bind 0.0.0.0:5000 app:app
```

**Frontend (build):**

```bash
cd react-version
npm run build
# Serve the build folder with your preferred method
```

---

## 🌐 Deployment

### Option 1: Deploy to Vercel (Frontend) + Render (Backend)

**Frontend (Vercel):**

1. Push code to GitHub
2. Go to [Vercel](https://vercel.com/)
3. Import your repository
4. Set build command: `cd react-version && npm run build`
5. Set output directory: `react-version/build`
6. Deploy!

**Backend (Render):**

1. Go to [Render](https://render.com/)
2. Create new Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command**: `cd react-version/backend && pip install -r requirements.txt`
   - **Start Command**: `cd react-version/backend && gunicorn -w 4 -k gevent --bind 0.0.0.0:$PORT app:app`
   - **Environment Variables**: Add `GROQ_API_KEY`, `JWT_SECRET_KEY`, `FERNET_KEY`
5. Deploy!

### Option 2: Deploy to Heroku

```bash
# Install Heroku CLI
# Create Procfile in root:
echo "web: cd react-version/backend && gunicorn -w 4 -k gevent app:app" > Procfile

# Deploy
heroku create your-app-name
heroku config:set GROQ_API_KEY=your_key JWT_SECRET_KEY=your_secret FERNET_KEY=your_fernet_key
git push heroku main
```

### Option 3: Deploy to AWS/GCP/Azure

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed cloud deployment guides.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     User Interface                       │
│              (React + Three.js + CSS3)                   │
└───────────────────────┬─────────────────────────────────┘
                        │ JWT Auth
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   Flask Backend API                      │
│          (ThreadPoolExecutor + Multi-threading)          │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Lead Agent  │  │Frontend Agent│  │Backend Agent │  │
│  │ (Orchestrate)│→ │ (HTML/CSS/JS)│  │  (Flask API) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                                      │         │
│         └──────────── Groq API ────────────────┘         │
│              (Llama 3.3 70B Versatile)                   │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   ChromaDB (Vector DB)                   │
│  • aidevs_users (encrypted credentials)                 │
│  • aidevs_conversations (RAG context)                   │
└─────────────────────────────────────────────────────────┘
```

**Key Components:**

- **Multi-Agent System**: Specialized AI agents for different tasks
- **RAG Pipeline**: Context-aware responses using conversation history
- **Vector Database**: Fast semantic search with embeddings
- **Concurrent Processing**: ThreadPoolExecutor handles parallel requests
- **Secure Storage**: Fernet encryption for sensitive data

For detailed architecture documentation, see [ARCHITECTURE.md](./react-version/backend/ARCHITECTURE.md)

---

## 📖 Documentation

- [Architecture Guide](./react-version/backend/ARCHITECTURE.md) - System design and patterns
- [Authentication Flow](./react-version/AUTHENTICATION_README.md) - JWT and encryption details
- [API Reference](#) - Backend endpoints documentation
- [Agent System](#) - How multi-agent collaboration works

---

## 🤝 Contributing

Contributions are what make the open-source community amazing! Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 📧 Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter) - your.email@example.com

Project Link: [https://github.com/YOUR_USERNAME/AIDevs](https://github.com/YOUR_USERNAME/AIDevs)

---

## 🙏 Acknowledgments

- [Groq](https://groq.com/) - Lightning-fast LLM inference
- [Meta AI](https://ai.meta.com/) - Llama 3.3 model
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Framer](https://www.framer.com/) - Design inspiration
- [Three.js](https://threejs.org/) - 3D graphics library

---

<p align="center">Made with ❤️ by Your Name</p>
<p align="center">⭐ Star this repo if you found it helpful!</p>
