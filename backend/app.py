"""
Flask application entry point for GenAI Task Manager.
Configures the Flask app, database, JWT, CORS, and all routes.
"""

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from datetime import timedelta
import os

# Load environment variables
load_dotenv()

# Import database and models
from database_mongo import init_mongo, check_database_health
from models_mongo import User, Task

# Import route blueprints
from routes.auth_routes import auth_bp
from routes.task_routes import task_bp
from routes.ai_routes import ai_bp

# Import services
from services.scheduler import task_scheduler
from services.email_service import EmailService

def create_app():
    """
    Create and configure Flask application.
    """
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)  # Tokens expire in 7 days
    app.config['JWT_ALGORITHM'] = 'HS256'

    # Disable automatic slash redirection to avoid CORS issues
    app.url_map.strict_slashes = False
    
    # Initialize extensions
    jwt = JWTManager(app)
    mail = EmailService.init_mail(app)

    # Store mail instance in app context for routes to access
    app.mail = mail
    
    # Enable CORS for frontend communication (permissive for development)
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # Initialize MongoDB
    mongo = init_mongo(app)
    if mongo is None:
        print("⚠️ Warning: MongoDB initialization failed. Please check your MongoDB connection.")
    else:
        print("✅ MongoDB initialized successfully!")
    
    # Add request logging for debugging
    @app.before_request
    def log_request_info():
        if request.path.startswith('/api/'):
            print(f"Request: {request.method} {request.path}")
            auth_header = request.headers.get('Authorization')
            if auth_header:
                print(f"Authorization header: {auth_header[:50]}...")
            else:
                print("No Authorization header found")

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(ai_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        print("JWT Error: Token has expired")
        return jsonify({'error': 'Token has expired', 'valid': False}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        print(f"JWT Error: Invalid token - {error}")
        return jsonify({'error': 'Invalid token', 'valid': False}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        print(f"JWT Error: Missing token - {error}")
        return jsonify({'error': 'Authorization token required', 'valid': False}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        print("JWT Error: Token has been revoked")
        return jsonify({'error': 'Token has been revoked', 'valid': False}), 401
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """
        Basic health check endpoint.
        """
        return jsonify({
            'status': 'healthy',
            'message': 'GenAI Task Manager API is running',
            'scheduler_status': task_scheduler.get_scheduler_status()
        }), 200
    

    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        """
        Root endpoint with API information.
        """
        return jsonify({
            'message': 'GenAI Task Manager API',
            'version': '1.0.0',
            'endpoints': {
                'auth': '/api/auth',
                'tasks': '/api/tasks',
                'ai': '/api/ai',
                'health': '/api/health'
            }
        }), 200
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    print("🚀 Starting GenAI Task Manager Backend...")
    print("📊 Dashboard will be available at: http://localhost:3000")
    print("🔗 API endpoints available at: http://localhost:5000/api")
    print("💡 Make sure to set your OPENAI_API_KEY in .env file")
    print("=" * 50)
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
