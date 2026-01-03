# 📋 Render Deployment Checklist

Follow these steps to deploy AIDevs to Render successfully.

## ✅ Pre-Deployment Setup

### 1. Generate Encryption Key

Run on your local machine:

**Windows:**

```bash
cd backend
python generate_keys.bat
```

**Mac/Linux:**

```bash
cd backend
chmod +x generate_keys.sh
./generate_keys.sh
```

**Manual generation:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the generated key - you'll need it for Render environment variables.

### 2. Get Your Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Create a new API key
4. Copy the key

### 3. Push to GitHub

```bash
cd "c:\Users\padma\Desktop\AI Devs\react-version"

# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Ready for Render deployment"

# Create GitHub repository and push
git remote add origin https://github.com/YOUR_USERNAME/aidevs.git
git branch -M main
git push -u origin main
```

## 🚀 Deployment Steps

### Step 1: Create Backend Service

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:

   ```
   Name: aidevs-backend
   Region: Oregon (or closest to you)
   Branch: main
   Root Directory: react-version/backend
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn -w 4 -k gevent --worker-connections 1000 --bind 0.0.0.0:$PORT app:app
   ```

5. **Environment Variables** (Click "Advanced" → "Add Environment Variable"):

   ```
   FLASK_ENV=production
   GROQ_API_KEY=your-groq-api-key-here
   ENCRYPTION_KEY=your-generated-encryption-key
   JWT_SECRET_KEY=click-generate
   ```

6. Click **"Create Web Service"**
7. Wait for deployment (5-10 minutes)
8. **Copy the backend URL** (e.g., `https://aidevs-backend.onrender.com`)

### Step 2: Create Frontend Service

1. Back in Render Dashboard, click **"New +"** → **"Static Site"**
2. Connect same GitHub repository
3. Configure:

   ```
   Name: aidevs-frontend
   Region: Oregon
   Branch: main
   Root Directory: react-version
   Build Command: npm install && npm run build
   Publish Directory: build
   ```

4. **Environment Variables**:

   ```
   REACT_APP_API_URL=https://aidevs-backend.onrender.com
   ```

   ⚠️ **Important:** Replace with YOUR actual backend URL from Step 1

5. **Rewrites and Redirects**:

   - Click "Redirects/Rewrites"
   - Add rule:
     ```
     Source: /*
     Destination: /index.html
     Action: Rewrite
     ```

6. Click **"Create Static Site"**
7. Wait for deployment (3-5 minutes)
8. **Copy the frontend URL** (e.g., `https://aidevs-frontend.onrender.com`)

### Step 3: Update CORS Configuration

1. Go back to **aidevs-backend** service
2. Navigate to **Environment** tab
3. Add/Update variable:

   ```
   CORS_ORIGINS=https://aidevs-frontend.onrender.com
   ```

   ⚠️ **Important:** Use YOUR actual frontend URL from Step 2

4. Click **"Save Changes"**
5. Service will automatically redeploy

## 🧪 Testing

### 1. Check Backend Health

Visit: `https://your-backend-url.onrender.com/api/health`

Should return:

```json
{
  "status": "healthy",
  "service": "AIDevs Backend",
  "version": "1.0.0"
}
```

### 2. Test Frontend

1. Visit: `https://your-frontend-url.onrender.com`
2. Click **"Register"**
3. Create a test account
4. Try building a simple website
5. Verify backend code generates
6. Test download functionality

## 🐛 Troubleshooting

### Backend Issues

**Error: Application failed to start**

- Check logs: Dashboard → aidevs-backend → Logs
- Verify all environment variables are set
- Ensure GROQ_API_KEY is valid

**Error: Module not found**

- Check `requirements.txt` is in `backend/` folder
- Verify build command: `pip install -r requirements.txt`

**Error: Port binding failed**

- Ensure start command uses `$PORT` variable
- Correct: `--bind 0.0.0.0:$PORT`

### Frontend Issues

**Blank page or errors**

- Check browser console (F12)
- Verify `REACT_APP_API_URL` is set correctly
- Make sure URL includes `https://` not `http://`

**API calls failing (CORS errors)**

- Check `CORS_ORIGINS` in backend includes frontend URL
- Verify both services are running
- Check backend logs for CORS errors

**404 on page refresh**

- Ensure rewrite rule is added: `/* → /index.html`

### First Load is Slow

- Free tier services spin down after 15 minutes
- First request takes 30-60 seconds to wake up
- **Solution:** Upgrade to paid tier ($7/month) for always-on

## 📊 Monitoring

### View Logs

```
Dashboard → Select Service → Logs
```

### Check Metrics

```
Dashboard → Select Service → Metrics
```

- CPU usage
- Memory usage
- Request count
- Response time

### Health Checks

Backend automatically checks: `/api/health`

## 💰 Cost Breakdown

### Free Tier (Current Setup)

- Static Site: **Free** ✅
- Web Service: **750 hours/month free** ✅
- Limitations:
  - Services spin down after 15 min inactivity
  - Slower cold starts
  - No persistent disk for ChromaDB

### Paid Tier ($7/month per service)

- Always on
- No cold starts
- 512MB RAM (upgradable)
- Persistent disk available
- Custom domains

**Total if upgraded:** $7/month (backend only, frontend stays free)

## 🔐 Security Checklist

- [ ] Strong JWT_SECRET_KEY generated
- [ ] Unique ENCRYPTION_KEY created
- [ ] Valid Groq API key configured
- [ ] CORS properly configured
- [ ] `.env` files NOT committed to git
- [ ] All secrets in Render environment variables

## 🎉 Success!

Your app is now live:

- **Frontend:** `https://your-frontend-url.onrender.com`
- **Backend:** `https://your-backend-url.onrender.com`

### Share Your App

Send the frontend URL to users!

### Next Steps

1. Set up custom domain (optional)
2. Configure monitoring alerts
3. Set up automated backups
4. Add analytics tracking

---

## 📞 Support

**Render Support:**

- Docs: https://render.com/docs
- Community: https://community.render.com
- Email: support@render.com

**Need Help?**
Check logs first, then consult RENDER_DEPLOYMENT.md for detailed guides.
