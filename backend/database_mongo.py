"""
MongoDB database configuration and connection management.
Handles MongoDB connection, collections, and database operations.
"""

import os
from datetime import datetime
from flask_pymongo import PyMongo
from pymongo import ReturnDocument

# Global PyMongo instance
mongo: PyMongo | None = None


def init_mongo(app):
    """Initialize MongoDB with Flask app."""
    global mongo

    # MongoDB configuration
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/genai_task_manager")
    app.config["MONGO_URI"] = mongo_uri

    print(f"[Mongo] Connecting to: {mongo_uri}")

    try:
        # Optional: pool size for cloud/Atlas
        if "localhost" not in mongo_uri and "127.0.0.1" not in mongo_uri:
            app.config["MONGO_CONNECT"] = False
            app.config["MONGO_MAXPOOLSIZE"] = int(os.getenv("MONGO_MAXPOOLSIZE", "50"))

        mongo = PyMongo(app)

        # Test the connection
        mongo.cx.admin.command("ping")
        print("[Mongo] Connection successful!")

        create_indexes()
        return mongo

    except Exception as e:
        print(f"[Mongo] Connection failed: {e}")
        print("Make sure MongoDB is running (check MongoDB/Compass) and your URI is correct.")
        return None


def create_indexes():
    """Create database indexes for better performance (idempotent)."""
    if mongo is None:
        print("[Mongo] Skipping index creation: mongo not initialized.")
        return

    try:
        # Users
        mongo.db.users.create_index("username", unique=True)
        mongo.db.users.create_index("email", unique=True)

        # Tasks – single-field
        mongo.db.tasks.create_index("user_id")
        mongo.db.tasks.create_index("status")
        mongo.db.tasks.create_index("priority")
        mongo.db.tasks.create_index("deadline")
        mongo.db.tasks.create_index("created_at")

        # Optional: compound/sort-friendly index (deadline asc, created_at desc)
        try:
            mongo.db.tasks.create_index([("deadline", 1), ("created_at", -1)])
        except Exception:
            pass

        # Optional: text index for search (used by title/description filters)
        try:
            mongo.db.tasks.create_index([("title", "text"), ("description", "text")])
        except Exception:
            pass

        # ✅ Do NOT create an index on _id (MongoDB already enforces it).
        # Ensure the 'counters' collection exists (used for auto-increment IDs).
        if "counters" not in mongo.db.list_collection_names():
            mongo.db.create_collection("counters")

        print("[Mongo] Indexes created/verified successfully.")
    except Exception as e:
        print(f"[Mongo] Warning: Could not create indexes: {e}")


def get_mongo() -> PyMongo | None:
    """Get the MongoDB instance."""
    return mongo


class MongoDBManager:
    """Helper class for MongoDB operations."""

    @staticmethod
    def get_collection(collection_name):
        if mongo is None:
            raise RuntimeError("MongoDB not initialized. Call init_mongo(app) first.")
        return mongo.db[collection_name]

    @staticmethod
    def insert_document(collection_name, document: dict):
        """Insert a document into a collection."""
        col = MongoDBManager.get_collection(collection_name)
        now = datetime.utcnow()
        document.setdefault("created_at", now)
        document["updated_at"] = now
        result = col.insert_one(document)
        return result.inserted_id

    @staticmethod
    def find_document(collection_name, query: dict):
        """Find a single document in a collection."""
        col = MongoDBManager.get_collection(collection_name)
        return col.find_one(query)

    @staticmethod
    def find_documents(collection_name, query: dict | None = None, sort=None, limit: int | None = None):
        """Find multiple documents in a collection."""
        col = MongoDBManager.get_collection(collection_name)
        cursor = col.find(query or {})
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    @staticmethod
    def update_document(collection_name, query: dict, update_data: dict) -> bool:
        """Update a document (sets updated_at automatically)."""
        col = MongoDBManager.get_collection(collection_name)
        update_data = dict(update_data or {})
        update_data["updated_at"] = datetime.utcnow()
        result = col.update_one(query, {"$set": update_data})
        return result.modified_count > 0

    @staticmethod
    def delete_document(collection_name, query: dict) -> bool:
        """Delete a document."""
        col = MongoDBManager.get_collection(collection_name)
        result = col.delete_one(query)
        return result.deleted_count > 0

    @staticmethod
    def count_documents(collection_name, query: dict | None = None) -> int:
        """Count documents in a collection."""
        col = MongoDBManager.get_collection(collection_name)
        return col.count_documents(query or {})

    @staticmethod
    def aggregate(collection_name, pipeline: list):
        """Run an aggregation pipeline and return a list."""
        col = MongoDBManager.get_collection(collection_name)
        return list(col.aggregate(pipeline))


def check_database_health():
    """Check if database connection is healthy."""
    try:
        if mongo is None:
            return False, "MongoDB not initialized"
        mongo.cx.admin.command("ping")
        return True, "MongoDB connection healthy"
    except Exception as e:
        return False, f"MongoDB connection error: {e}"


def get_next_sequence_value(sequence_name: str) -> int:
    """
    Atomically get the next integer in a named counter.
    Creates the counter document if it doesn't exist.
    Result is the value AFTER increment.
    """
    col = MongoDBManager.get_collection("counters")
    doc = col.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"sequence_value": 1}},   # upsert will create sequence_value=1 if missing
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc.get("sequence_value", 1))
