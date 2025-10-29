# ...existing code...
"""
Flask application entry point for GenAI Task Manager.
Configures the Flask app, database, JWT, CORS, mail, and all routes.
"""

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import MongoDB database
from database_mongo import init_mongo, check_database_health

# Import route blueprints
from routes.auth_routes import auth_bp
from routes.task_routes import task_bp
from routes.ai_routes import ai_bp

# Import services
from services.scheduler import task_scheduler  # noqa: F401 (ensures scheduler class loads)
from services.reminder_service import start_scheduler


# Allowed origins for frontend communication
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
]


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # ----------------------------
    # Core Configuration
    # ----------------------------
    app.config["SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # Use timedelta(days=7) in production

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
    jwt = JWTManager(app)

    # ----------------------------
    # Enable CORS
    # ----------------------------
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

    # ----------------------------
    # Initialize MongoDB
    # ----------------------------
    init_mongo(app)
    ok, msg = check_database_health()
    print(f"[MongoDB] {msg}")

    # ----------------------------
    # Register Blueprints
    # ----------------------------
    # Register with explicit API prefixes expected by the frontend.
    # If any blueprint file already defines a url_prefix, remove the url_prefix here to avoid double prefixing.
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(task_bp, url_prefix='/api/tasks')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')

    # ----------------------------
    # Error Handlers
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

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return jsonify({"error": "Invalid token", "detail": reason}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        return jsonify({"error": "Authorization token required", "detail": reason}), 401

    # ----------------------------
    # Health Check Endpoint
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

    # ----------------------------
    # Config Echo (useful for frontend/env sanity)
    # ----------------------------
    @app.route("/api/config", methods=["GET"])
    def config_echo():
        return jsonify({
            "cors_allowed": ALLOWED_ORIGINS,
            "mail_configured": bool(app.config.get("MAIL_USERNAME") and app.config.get("MAIL_PASSWORD")),
            "twilio_configured": bool(
                os.getenv("TWILIO_ACCOUNT_SID")
                and os.getenv("TWILIO_AUTH_TOKEN")
                and os.getenv("TWILIO_WHATSAPP_FROM")
            ),
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        }), 200

    # ----------------------------
    # Preflight CORS Handler
    # ----------------------------
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get("Origin")
            resp = make_response()
            if origin in ALLOWED_ORIGINS:
                resp.headers.add("Access-Control-Allow-Origin", origin)
            resp.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            resp.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
            resp.headers.add("Access-Control-Allow-Credentials", "true")
            return resp

    # ----------------------------
    # Root Endpoint
    # ----------------------------
    @app.route("/", methods=["GET"])
    def root():
        """Root endpoint providing API overview."""
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

    return app


# ----------------------------
# Application Entry Point
# ----------------------------
app = create_app()

# Start the Reminder + WhatsApp Scheduler safely
try:
    start_scheduler(app)
except Exception as e:
    print(f"[Scheduler] Failed to start: {e}")

if __name__ == "__main__":
    print("🚀 Starting GenAI Task Manager Backend...")
    print("Frontend Dashboard: http://localhost:3000")
    print("API Base URL:       http://localhost:5000/api")
    print("Make sure your .env file contains:")
    print(" - OPENAI_API_KEY")
    print(" - MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER")
    print(" - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM")
    print("=" * 70)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True,
    )
# ...existing code...