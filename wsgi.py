"""
WSGI configuration for PythonAnywhere deployment
This file is used by PythonAnywhere to run your FastAPI application
"""

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/YOUR_USERNAME/PDF'  # UPDATE THIS with your PythonAnywhere username
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import the FastAPI app from backend/main.py
from backend.main import app

# PythonAnywhere uses WSGI, but FastAPI is ASGI
# We need to wrap it with an ASGI-to-WSGI adapter
from asgiref.wsgi import WsgiToAsgi

application = WsgiToAsgi(app)
