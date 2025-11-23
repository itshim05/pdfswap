"""
WSGI configuration for PythonAnywhere deployment (Flask version)
"""

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/YOUR_USERNAME/PDF'  # UPDATE THIS with your PythonAnywhere username
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import the Flask app
from backend.main_sync import app as application
