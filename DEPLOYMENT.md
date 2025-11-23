# Git Deployment Instructions

This guide covers deploying your PDF processing application to various platforms using Git.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
  - [PythonAnywhere](#pythonanywhere)
  - [Render](#render)
  - [Railway](#railway)
  - [Vercel (Frontend Only)](#vercel-frontend-only)
- [Environment Setup](#environment-setup)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying, ensure you have:

1. **Git repository initialized** (already done ✓)
2. **Updated requirements.txt** with all dependencies
3. **Committed all changes** to your repository
4. **GitHub/GitLab account** for hosting your repository

### Update Requirements

Your current `requirements.txt` is incomplete. Update it with:

```txt
fastapi
uvicorn[standard]
pymupdf
python-multipart
```

### Commit Your Code

```bash
# Add all files
git add .

# Commit changes
git commit -m "Prepare for deployment"

# Create a GitHub repository and push
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

---

## Deployment Options

### PythonAnywhere

**Best for:** Simple deployments, free tier available

#### Steps:

1. **Create a PythonAnywhere account** at [pythonanywhere.com](https://www.pythonanywhere.com)

2. **Open a Bash console** and clone your repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
   ```

3. **Create a virtual environment**:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 myenv
   pip install -r requirements.txt
   ```

4. **Configure WSGI file**:
   - Go to the **Web** tab
   - Click **Add a new web app**
   - Choose **Manual configuration** (Python 3.10)
   - Edit the WSGI configuration file and replace with:

   ```python
   import sys
   import os
   
   # Add your project directory to the sys.path
   project_home = '/home/YOUR_USERNAME/YOUR_REPO_NAME'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)
   
   # Set environment variable for the app
   os.environ['PYTHONUNBUFFERED'] = '1'
   
   # Import the FastAPI app
   from backend.main import app as application
   ```

5. **Set virtual environment path**:
   - In the Web tab, set virtualenv path: `/home/YOUR_USERNAME/.virtualenvs/myenv`

6. **Configure static files**:
   - URL: `/static/`
   - Directory: `/home/YOUR_USERNAME/YOUR_REPO_NAME/frontend`

7. **Reload your web app** and visit your site!

#### Updating Your Deployment:

```bash
# SSH into PythonAnywhere console
cd YOUR_REPO_NAME
git pull origin main
pip install -r requirements.txt
# Then reload web app from Web tab
```

---

### Render

**Best for:** Modern deployments, automatic deploys from Git

#### Steps:

1. **Create a Render account** at [render.com](https://render.com)

2. **Create a `render.yaml`** file in your project root:

   ```yaml
   services:
     - type: web
       name: pdf-processor
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
       envVars:
         - key: PYTHON_VERSION
           value: 3.10.0
   ```

3. **Push to GitHub**:
   ```bash
   git add render.yaml
   git commit -m "Add Render configuration"
   git push origin main
   ```

4. **Connect to Render**:
   - Click **New +** → **Blueprint**
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml` and deploy

#### Updating Your Deployment:

Render automatically deploys when you push to your main branch:

```bash
git add .
git commit -m "Update application"
git push origin main
```

---

### Railway

**Best for:** Easy deployments with generous free tier

#### Steps:

1. **Create a Railway account** at [railway.app](https://railway.app)

2. **Create a `Procfile`** in your project root:

   ```
   web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```

3. **Create a `runtime.txt`** (optional):

   ```
   python-3.10.0
   ```

4. **Push to GitHub**:
   ```bash
   git add Procfile runtime.txt
   git commit -m "Add Railway configuration"
   git push origin main
   ```

5. **Deploy on Railway**:
   - Click **New Project** → **Deploy from GitHub repo**
   - Select your repository
   - Railway will automatically detect and deploy

#### Updating Your Deployment:

Railway automatically deploys on push:

```bash
git add .
git commit -m "Update application"
git push origin main
```

---

### Vercel (Frontend Only)

**Note:** Vercel is primarily for frontend/serverless. For full-stack, use Render or Railway.

#### Steps:

1. **Install Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **Create `vercel.json`**:

   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "backend/main.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/api/(.*)",
         "dest": "backend/main.py"
       },
       {
         "src": "/(.*)",
         "dest": "frontend/$1"
       }
     ]
   }
   ```

3. **Deploy**:
   ```bash
   vercel --prod
   ```

---

## Environment Setup

### Required Files Checklist

- ✅ `.gitignore` - Already configured
- ✅ `requirements.txt` - **Update with all dependencies**
- ⚠️ `README.md` - Add project description
- ⚠️ Platform-specific config (choose one):
  - `render.yaml` for Render
  - `Procfile` for Railway
  - `vercel.json` for Vercel

### Update Requirements.txt

Replace your current `requirements.txt` with:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pymupdf==1.23.8
python-multipart==0.0.6
```

---

## Troubleshooting

### Common Issues

#### 1. **Module Not Found Errors**

```bash
# Ensure all dependencies are in requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push
```

#### 2. **Static Files Not Loading**

- Ensure `frontend` directory is committed to Git
- Check static file paths in deployment platform settings
- Verify CORS settings in `backend/main.py`

#### 3. **Port Binding Issues**

Most platforms provide a `PORT` environment variable. Ensure your app uses it:

```python
# In backend/main.py
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

#### 4. **File Upload Size Limits**

Add to your FastAPI app:

```python
from fastapi import FastAPI

app = FastAPI()
app.max_request_size = 100 * 1024 * 1024  # 100MB
```

---

## Quick Deploy Commands

### Initial Setup
```bash
# 1. Update requirements
# (Edit requirements.txt with all dependencies)

# 2. Commit everything
git add .
git commit -m "Prepare for deployment"

# 3. Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main

# 4. Choose a platform and follow its specific steps above
```

### Subsequent Updates
```bash
# Make your changes, then:
git add .
git commit -m "Description of changes"
git push origin main

# Most platforms auto-deploy on push!
```

---

## Recommended Platform

For your PDF processing app, I recommend **Render** or **Railway** because:

- ✅ Free tier available
- ✅ Automatic deployments from Git
- ✅ Handles both backend and static files
- ✅ Easy to set up and manage
- ✅ Good performance for FastAPI apps

**PythonAnywhere** is also good if you prefer more manual control and are familiar with traditional hosting.

---

## Next Steps

1. Update `requirements.txt` with all dependencies
2. Choose a deployment platform
3. Create the necessary configuration file(s)
4. Push to GitHub
5. Connect your repository to the platform
6. Deploy! 🚀

For questions or issues, refer to the platform-specific documentation or the troubleshooting section above.
