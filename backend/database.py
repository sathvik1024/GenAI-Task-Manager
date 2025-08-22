"""
Database configuration and initialization for the GenAI Task Manager.
Uses SQLite for local development with SQLAlchemy ORM.
"""

from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import os

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def init_database(app: Flask):
    """
    Initialize database with Flask app.
    Creates SQLite database file if it doesn't exist.
    """
    # Configure SQLite database
    basedir = os.path.abspath(os.path.dirname(__file__))
    database_url = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(basedir, "tasks.db")}')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database with app
    db.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
        print("Database initialized successfully!")

def get_db():
    """
    Get database instance for use in other modules.
    """
    return db
