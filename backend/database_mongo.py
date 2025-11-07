"""
MongoDB database configuration and connection management.
Handles MongoDB connection, collections, and database operations.
"""

import os
import sys
from datetime import datetime
from flask_pymongo import PyMongo
from pymongo import ReturnDocument
from urllib.parse import quote_plus

# Global PyMongo instance
mongo: PyMongo | None = None


def _warn_and_exit(msg: str):
    print(f"[Mongo][FATAL] {msg}")
    # Exit so the app doesn't continue in broken state
    sys.exit(1)


def _sanitize_uri(uri: str) -> str:
    """
    Basic checks and helpful messages. Does not modify your password.
    If password placeholder is present, warn.
    """
    if not uri:
        _warn_and_exit("MONGODB_URI not set. Please set the MONGODB_URI environment variable.")
    # If user left literal <password> placeholder
    if "<password>" in uri or "%3Cpassword%3E" in uri:
        _warn_and_exit("MONGODB_URI contains '<password>' placeholder. Replace with your real (URL-encoded) password.")
    return uri


def init_mongo(app):
    """Initialize MongoDB with Flask app. Raises/Exits on fatal failure."""
    global mongo

    # MongoDB configuration
    env_uri = os.getenv("MONGODB_URI", "").strip()
    mongo_uri = _sanitize_uri(env_uri) if env_uri else _sanitize_uri(os.getenv("MONGODB_URI", ""))

    # Helpful hint: if user provided user:pass separate, you could build the URI here
    # but we expect the full URI in env.
    app.config["MONGO_URI"] = mongo_uri

    print(f"[Mongo] Connecting to: {mongo_uri[:120]}{'...' if len(mongo_uri)>120 else ''}")

    try:
        # Optional: adjust pool size for cloud/Atlas
        if "localhost" not in mongo_uri and "127.0.0.1" not in mongo_uri:
            app.config["MONGO_CONNECT"] = False
            app.config["MONGO_MAXPOOLSIZE"] = int(os.getenv("MONGO_MAXPOOLSIZE", "50"))

        mongo = PyMongo(app)

        # Test the connection (this will raise if connection fails)
        mongo.cx.admin.command("ping")
        print("[Mongo] Connection successful!")

        create_indexes()
        return mongo

    except Exception as e:
        # Detailed error so user can fix quickly
        print(f"[Mongo] Connection failed: {e}")
        print("Make sure:")
        print(" - MONGODB_URI is correct and includes the DB name (e.g. ...mongodb.net/your_db_name?retryWrites=true&w=majority)")
        print(" - Your Atlas user credentials are valid and password is URL-encoded if it contains special characters")
        print(" - Network access in Atlas allows your IP (or 0.0.0.0/0 for testing)")
        # Fail fast: exit so app doesn't continue with mongo=None
        _warn_and_exit("MongoDB initialization failed. Exiting.")
        return None  # unreachable but explicit


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
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc.get("sequence_value", 1))
