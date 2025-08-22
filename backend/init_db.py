#!/usr/bin/env python3
"""
Manual database initialization script.
Run this if the database isn't being created automatically.
"""

import os
from flask import Flask
from database import init_database
from models import User, Task

def create_database():
    """Create the database and tables manually"""
    app = Flask(__name__)
    
    # Configure the app
    app.config['SECRET_KEY'] = 'dev-secret-key'
    app.config['JWT_SECRET_KEY'] = 'dev-secret-key'
    
    # Initialize database
    init_database(app)
    
    print("✅ Database created successfully!")
    print(f"📁 Database file location: {os.path.abspath('tasks.db')}")

if __name__ == "__main__":
    create_database()
