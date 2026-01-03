# 🚀 Quick Start - Deploy to Render in 10 Minutes

## Prerequisites

- GitHub account
- Groq API key ([get one here](https://console.groq.com))

## Step-by-Step

### 1️⃣ Generate Encryption Key (2 min)

**Windows:**

```bash
cd backend
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Mac/Linux:**

```bash
cd backend
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Save the output** - you'll need it!

### 2️⃣ Push to GitHub (2 min)

```bash
cd "c:\Users\padma\Desktop\AI Devs\react-version"
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/aidevs.git
git push -u origin main
```

### 3️⃣ Deploy Backend (3 min)

1. Go to [render.com/dashboard](https://dashboard.render.com)
2. **New +** → **Web Service**
3. Connect GitHub repo
4. Settings:
   - **Root Directory:** `react-version/backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -w 4 -k gevent --worker-connections 1000 --bind 0.0.0.0:$PORT app:app`
5. Add environment variables:
   ```
   GROQ_API_KEY=your_key_here
   ENCRYPTION_KEY=your_generated_key
   FLASK_ENV=production
   ```
6. Click **Create** and **copy the URL**

### 4️⃣ Deploy Frontend (3 min)

1. **New +** → **Static Site**
2. Connect same repo
3. Settings:
   - **Root Directory:** `react-version`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `build`
4. Add environment variable:
   ```
   REACT_APP_API_URL=YOUR_BACKEND_URL_FROM_STEP_3
   ```
5. Add rewrite rule:
   - Source: `/*`
   - Destination: `/index.html`
   - Action: **Rewrite**
6. Click **Create**

### 5️⃣ Update CORS

1. Go back to backend service
2. **Environment** tab
3. Add:
   ```
   CORS_ORIGINS=YOUR_FRONTEND_URL
   ```
4. Save (auto-redeploys)

## ✅ Done!

Visit your frontend URL and start building websites! 🎉

---

**Need detailed help?** See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) or [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)
