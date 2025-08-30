#!/usr/bin/env python3
"""
Test script to verify MongoDB integration is working correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_mongodb_connection():
    """Test MongoDB connection."""
    try:
        from database_mongo import init_mongo, check_database_health
        from flask import Flask
        
        # Create test app
        app = Flask(__name__)
        
        with app.app_context():
            # Initialize MongoDB
            mongo = init_mongo(app)
            
            if mongo is None:
                print("MongoDB initialization failed")
                return False
            
            # Check health
            healthy, message = check_database_health()
            print(f"Database health: {message}")
            
            return healthy
            
    except Exception as e:
        print(f"MongoDB connection test failed: {e}")
        return False

def test_models():
    """Test MongoDB models."""
    try:
        from models_mongo import User, Task
        from flask import Flask
        from database_mongo import init_mongo
        
        # Create test app
        app = Flask(__name__)
        
        with app.app_context():
            # Initialize MongoDB
            mongo = init_mongo(app)
            
            if mongo is None:
                print("Cannot test models - MongoDB not available")
                return False
            
            # Test User model
            print("Testing User model...")
            test_user = User(
                username="test_user_mongo",
                email="test@mongodb.com",
                password="testpass123"
            )
            test_user.save()
            print(f"User created with ID: {test_user.id}")
            
            # Find user
            found_user = User.find_by_username("test_user_mongo")
            if found_user:
                print(f"User found: {found_user.username}")
            else:
                print("User not found")
                return False
            
            # Test Task model
            print("Testing Task model...")
            test_task = Task(
                title="Test MongoDB Task",
                description="Testing MongoDB integration",
                priority="high",
                category="test",
                user_id=test_user.id
            )
            test_task.save()
            print(f"Task created with ID: {test_task.id}")
            
            # Find tasks
            user_tasks = Task.find_by_user_id(test_user.id)
            print(f"Found {len(user_tasks)} tasks for user")
            
            # Get stats
            stats = Task.get_user_stats(test_user.id)
            print(f"User stats: {stats}")
            
            return True
            
    except Exception as e:
        print(f"Model test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing MongoDB Integration...")
    print("=" * 50)
    
    # Test connection
    print("Testing MongoDB connection...")
    if not test_mongodb_connection():
        print("MongoDB connection failed. Please ensure MongoDB is running.")
        return
    
    print("\Testing MongoDB models...")
    if not test_models():
        print("Model tests failed.")
        return
    
    print("\n" + "=" * 50)
    print("All MongoDB tests passed!")
    print("Your application is ready to use MongoDB!")

if __name__ == "__main__":
    main()
