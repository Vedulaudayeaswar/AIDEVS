@echo off
REM AIDevs - Render Deployment Helper Script (Windows)

echo 🚀 AIDevs Render Deployment Helper
echo ====================================
echo.

REM Check if git is initialized
if not exist .git (
    echo 📦 Initializing Git repository...
    git init
    echo ✅ Git initialized
) else (
    echo ✅ Git already initialized
)

REM Check if .env exists
if not exist backend\.env (
    echo.
    echo ⚠️  WARNING: backend\.env not found!
    echo Creating from .env.example...
    copy backend\.env.example backend\.env
    echo ✅ Created backend\.env - Please edit it with your API keys
    echo.
)

REM Generate encryption key
echo.
echo 🔑 Generating Encryption Key...
python -c "from cryptography.fernet import Fernet; print('\n📋 COPY THIS ENCRYPTION KEY:\n' + '='*50); print(Fernet.generate_key().decode()); print('='*50 + '\n⚡ You will need this for Render environment variables!\n')"

REM Check for changes
echo.
echo 📝 Current Git Status:
git status -s
echo.

set /p commit_choice="Commit changes? (y/n): "
if /i "%commit_choice%"=="y" (
    git add .
    set /p commit_msg="Commit message (or press Enter for default): "
    if "%commit_msg%"=="" set commit_msg=Ready for Render deployment
    git commit -m "%commit_msg%"
    echo ✅ Changes committed
)

REM Check remote
git remote | findstr origin >nul
if errorlevel 1 (
    echo.
    echo 🔗 No Git remote found!
    set /p repo_url="Enter your GitHub repository URL: "
    git remote add origin %repo_url%
    echo ✅ Remote added
)

REM Push option
echo.
set /p push_choice="Push to GitHub? (y/n): "
if /i "%push_choice%"=="y" (
    git branch -M main
    git push -u origin main
    echo ✅ Pushed to GitHub
)

echo.
echo ================================================
echo ✅ Pre-deployment complete!
echo ================================================
echo.
echo 📋 Next Steps:
echo 1. Go to https://dashboard.render.com
echo 2. Create Web Service for backend (react-version/backend)
echo 3. Create Static Site for frontend (react-version)
echo 4. Set environment variables (see DEPLOYMENT_CHECKLIST.md)
echo.
echo 📚 Full guide: QUICK_START_RENDER.md
echo.
pause
