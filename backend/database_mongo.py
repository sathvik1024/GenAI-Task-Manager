"""
MongoDB database configuration and connection management.
Handles MongoDB connection, collections, and database operations.
"""

import os
from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import datetime
import logging

# Global PyMongo instance
mongo = None

def init_mongo(app):
    """Initialize MongoDB with Flask app."""
    global mongo

    # MongoDB configuration
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/genai_task_manager')
    app.config['MONGO_URI'] = mongo_uri

    print(f"🔗 Connecting to MongoDB: {mongo_uri}")

    try:
        # For local MongoDB (Compass), use simple connection
        if 'localhost' in mongo_uri:
            mongo = PyMongo(app)

            # Test the connection
            mongo.cx.admin.command('ping')
            print("MongoDB local connection successful!")

        else:
            # For Atlas or other cloud providers
            app.config['MONGO_CONNECT'] = False
            app.config['MONGO_MAXPOOLSIZE'] = 50
            mongo = PyMongo(app)

            # Test the connection with timeout
            mongo.cx.admin.command('ping', maxTimeMS=5000)
            print("MongoDB cloud connection successful!")

        # Create indexes for better performance
        create_indexes()

        return mongo

    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        print("Make sure MongoDB is running (check MongoDB Compass)")
        return None

def create_indexes():
    """Create database indexes for better performance."""
    try:
        # User collection indexes
        mongo.db.users.create_index("username", unique=True)
        mongo.db.users.create_index("email", unique=True)
        
        # Task collection indexes
        mongo.db.tasks.create_index("user_id")
        mongo.db.tasks.create_index("status")
        mongo.db.tasks.create_index("priority")
        mongo.db.tasks.create_index("deadline")
        mongo.db.tasks.create_index("created_at")
        
        print("Database indexes created successfully!")
    except Exception as e:
        print(f"Warning: Could not create indexes: {e}")

def get_mongo():
    """Get the MongoDB instance."""
    return mongo

class MongoDBManager:
    """Helper class for MongoDB operations."""
    
    @staticmethod
    def get_collection(collection_name):
        """Get a MongoDB collection."""
        if mongo is None:
            raise Exception("MongoDB not initialized")
        return mongo.db[collection_name]
    
    @staticmethod
    def insert_document(collection_name, document):
        """Insert a document into a collection."""
        collection = MongoDBManager.get_collection(collection_name)
        document['created_at'] = datetime.utcnow()
        document['updated_at'] = datetime.utcnow()
        result = collection.insert_one(document)
        return result.inserted_id
    
    @staticmethod
    def find_document(collection_name, query):
        """Find a single document in a collection."""
        collection = MongoDBManager.get_collection(collection_name)
        return collection.find_one(query)
    
    @staticmethod
    def find_documents(collection_name, query=None, sort=None, limit=None):
        """Find multiple documents in a collection."""
        collection = MongoDBManager.get_collection(collection_name)
        cursor = collection.find(query or {})
        
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
            
        return list(cursor)
    
    @staticmethod
    def update_document(collection_name, query, update_data):
        """Update a document in a collection."""
        collection = MongoDBManager.get_collection(collection_name)
        update_data['updated_at'] = datetime.utcnow()
        result = collection.update_one(query, {'$set': update_data})
        return result.modified_count > 0
    
    @staticmethod
    def delete_document(collection_name, query):
        """Delete a document from a collection."""
        collection = MongoDBManager.get_collection(collection_name)
        result = collection.delete_one(query)
        return result.deleted_count > 0
    
    @staticmethod
    def count_documents(collection_name, query=None):
        """Count documents in a collection."""
        collection = MongoDBManager.get_collection(collection_name)
        return collection.count_documents(query or {})
    
    @staticmethod
    def aggregate(collection_name, pipeline):
        """Perform aggregation on a collection."""
        collection = MongoDBManager.get_collection(collection_name)
        return list(collection.aggregate(pipeline))

# Database health check
def check_database_health():
    """Check if database connection is healthy."""
    try:
        if mongo is None:
            return False, "MongoDB not initialized"
        
        # Ping the database
        mongo.cx.admin.command('ping')
        return True, "MongoDB connection healthy"
    except Exception as e:
        return False, f"MongoDB connection error: {e}"

# Utility functions for common operations
def get_next_sequence_value(sequence_name):
    """Get next sequence value for auto-incrementing IDs."""
    collection = MongoDBManager.get_collection('counters')
    result = collection.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=True
    )
    return result['sequence_value']
