"""
Flask application entry point for GenAI Task Manager.
Configures the Flask app, database, JWT, CORS, mail, and all routes.
"""

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os
import sys

# Load environment variables early
load_dotenv()

# ----------------------------
# Create app (initial config)
# ----------------------------
def create_app() -> Flask:
    app = Flask(__name__)

    # ----------------------------
    # Core Configuration
    # ----------------------------
    app.config["SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    # NOTE: set a timedelta in production
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

    # ----------------------------
    # Email Configuration
    # ----------------------------
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "False").lower() == "true"
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", app.config["MAIL_USERNAME"])

    # ----------------------------
    # Disable automatic slash redirection (CORS fix)
    # ----------------------------
    app.url_map.strict_slashes = False

    # ----------------------------
    # Initialize JWT
    # ----------------------------
    JWTManager(app)

    # ----------------------------
    # Enable CORS
    # ----------------------------
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ]
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ALLOWED_ORIGINS,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True,
            }
        },
    )

    return app


# ----------------------------
# Initialize app and DB early
# ----------------------------
app = create_app()

# Initialize DB (must happen BEFORE importing routes that may use models)
from database_mongo import init_mongo, check_database_health

try:
    mongo = init_mongo(app)
    if mongo is None:
        raise RuntimeError("init_mongo returned None (failed to connect). Check MONGODB_URI, network, and Atlas settings.")
except Exception as e:
    print(f"[Fatal] MongoDB initialization failed: {e}")
    print("→ Ensure MONGODB_URI is set and Atlas network access allows this IP.")
    # Stop application so you don't get NoneType errors later.
    sys.exit(1)

ok, msg = check_database_health()
print(f"[MongoDB] {msg}")


# After DB is initialized, import blueprints/routes (so imports can safely query DB if needed)
from routes.auth_routes import auth_bp
from routes.task_routes import task_bp
from routes.ai_routes import ai_bp

# Import services AFTER DB ready
from services.scheduler import task_scheduler  # noqa: F401 (ensures scheduler loads)
from services.reminder_service import start_scheduler


# Register Blueprints with explicit API prefixes
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(task_bp, url_prefix='/api/tasks')
app.register_blueprint(ai_bp, url_prefix='/api/ai')


# ----------------------------
# Error Handlers & helpers
# ----------------------------
@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(_):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(400)
def bad_request(_):
    return jsonify({"error": "Bad request (invalid JSON or parameters)"}), 400


# JWT hooks (using default JWTManager() callbacks)
from flask_jwt_extended import JWTManager as _JWTManager
_jwt = _JWTManager(app)

@_jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token has expired"}), 401

@_jwt.invalid_token_loader
def invalid_token_callback(reason):
    return jsonify({"error": "Invalid token", "detail": reason}), 401

@_jwt.unauthorized_loader
def missing_token_callback(reason):
    return jsonify({"error": "Authorization token required", "detail": reason}), 401


# ----------------------------
# Health & config endpoints
# ----------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    """Basic health check endpoint."""
    from services.scheduler import task_scheduler as _ts  # local import to avoid circulars
    return jsonify({
        "status": "healthy",
        "message": "GenAI Task Manager API is running",
        "scheduler_status": _ts.get_scheduler_status(),
    }), 200

@app.route("/api/config", methods=["GET"])
def config_echo():
    return jsonify({
        "mail_configured": bool(app.config.get("MAIL_USERNAME") and app.config.get("MAIL_PASSWORD")),
        "twilio_configured": bool(
            os.getenv("TWILIO_ACCOUNT_SID")
            and os.getenv("TWILIO_AUTH_TOKEN")
            and os.getenv("TWILIO_WHATSAPP_FROM")
        ),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }), 200


# Preflight handler
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        origin = request.headers.get("Origin")
        resp = make_response()
        resp.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        resp.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        resp.headers.add("Access-Control-Allow-Credentials", "true")
        if origin:
            resp.headers.add("Access-Control-Allow-Origin", origin)
        return resp


# Root endpoint
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "GenAI Task Manager API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "tasks": "/api/tasks",
            "ai": "/api/ai",
            "health": "/api/health",
        },
    }), 200


# ----------------------------
# Start scheduler & run
# ----------------------------
# Start the Reminder + WhatsApp Scheduler safely
try:
    start_scheduler(app)
except Exception as e:
    print(f"[Scheduler] Failed to start: {e}")

if __name__ == "__main__":
    print("🚀 Starting GenAI Task Manager Backend...")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
