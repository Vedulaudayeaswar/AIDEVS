#!/bin/bash

# AIDevs - Render Deployment Helper Script

echo "🚀 AIDevs Render Deployment Helper"
echo "===================================="
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "📦 Initializing Git repository..."
    git init
    echo "✅ Git initialized"
else
    echo "✅ Git already initialized"
fi

# Check if .env exists in backend
if [ ! -f backend/.env ]; then
    echo ""
    echo "⚠️  WARNING: backend/.env not found!"
    echo "Creating from .env.example..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env - Please edit it with your API keys"
    echo ""
fi

# Generate encryption key
echo ""
echo "🔑 Generating Encryption Key..."
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo ""
echo "📋 COPY THIS ENCRYPTION KEY:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ENCRYPTION_KEY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚡ You'll need this for Render environment variables!"
echo ""

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo "📝 Files to commit:"
    git status -s
    echo ""
    read -p "Commit changes? (y/n): " commit_choice
    
    if [ "$commit_choice" = "y" ]; then
        git add .
        read -p "Commit message (or press Enter for default): " commit_msg
        
        if [ -z "$commit_msg" ]; then
            commit_msg="Ready for Render deployment"
        fi
        
        git commit -m "$commit_msg"
        echo "✅ Changes committed"
    fi
fi

# Check if remote exists
if ! git remote | grep -q origin; then
    echo ""
    echo "🔗 No Git remote found!"
    read -p "Enter your GitHub repository URL: " repo_url
    git remote add origin "$repo_url"
    echo "✅ Remote added"
fi

# Push to GitHub
echo ""
read -p "Push to GitHub? (y/n): " push_choice

if [ "$push_choice" = "y" ]; then
    git branch -M main
    git push -u origin main
    echo "✅ Pushed to GitHub"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Pre-deployment complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next Steps:"
echo "1. Go to https://dashboard.render.com"
echo "2. Create Web Service for backend (react-version/backend)"
echo "3. Create Static Site for frontend (react-version)"
echo "4. Set environment variables (see DEPLOYMENT_CHECKLIST.md)"
echo ""
echo "📚 Full guide: QUICK_START_RENDER.md"
echo ""
