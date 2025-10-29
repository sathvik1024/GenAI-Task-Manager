"""
Authentication routes for user signup and login.
Handles JWT token generation and user session management.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models_mongo import User
from datetime import timedelta
import re

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__)

# --- Helpers -----------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+\d{10,15}$")

def normalize_whatsapp_number(number: str) -> str:
    """
    Keep only leading '+' and digits; collapse spaces/dashes.
    Ensures format like +919876543210.
    """
    number = number.strip().replace(" ", "").replace("-", "")
    # If someone pasted like "++91..." keep just one plus
    number = "+" + "".join(ch for ch in number if ch.isdigit())
    return number

# --- Routes ------------------------------------------------------------------

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    Register a new user account.

    Expected JSON:
    {
        "username": "string",
        "email": "string",
        "password": "string",
        "whatsapp_number": "string (+91XXXXXXXXXX)"
    }
    """
    try:
        data = request.get_json() or {}

        # Validate required fields
        required_fields = ['username', 'email', 'password', 'whatsapp_number']
        if not all(k in data for k in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        whatsapp_number = normalize_whatsapp_number(data.get('whatsapp_number') or '')

        # ---- Validations ----
        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters long'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400

        if not EMAIL_RE.match(email):
            return jsonify({'error': 'Invalid email format'}), 400

        if not PHONE_RE.match(whatsapp_number):
            return jsonify({
                'error': 'Invalid WhatsApp number format. Include country code, e.g., +919876543210'
            }), 400

        # ---- Check for existing users ----
        if User.find_by_username(username):
            return jsonify({'error': 'Username already exists'}), 409

        if User.find_by_email(email):
            return jsonify({'error': 'Email already registered'}), 409

        # Optional: prevent duplicate WhatsApp numbers
        existing_by_phone = User.find_by_whatsapp(whatsapp_number)
        if existing_by_phone:
            return jsonify({'error': 'WhatsApp number already in use'}), 409

        # ---- Create and save new user ----
        user = User(
            username=username,
            email=email,
            password=password,
            whatsapp_number=whatsapp_number
        )
        user.save()

        # ---- Generate JWT token ----
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=7)
        )

        return jsonify({
            'message': 'User registered successfully!',
            'access_token': access_token,
            'user': user.to_dict()
        }), 201

    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token.

    Expected JSON:
    {
        "username": "string (username or email)",
        "password": "string"
    }
    """
    try:
        data = request.get_json() or {}

        if not all(k in data for k in ('username', 'password')):
            return jsonify({'error': 'Missing username or password'}), 400

        username_or_email = (data.get('username') or '').strip()
        password = data.get('password') or ''

        # ---- Find user by username or email ----
        user = User.find_by_username(username_or_email)
        if not user:
            user = User.find_by_email(username_or_email)

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        # ---- Generate new JWT token ----
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=7)
        )

        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get current user profile information.
    Requires valid JWT token in Authorization header.
    """
    try:
        user_id = int(get_jwt_identity())  # keep consistent with other routes
        user = User.find_by_id(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'user': user.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500


@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """
    Verify if the current JWT token is valid.
    Returns user info if token is valid.
    """
    try:
        user_id = int(get_jwt_identity())  # keep consistent with other routes
        user = User.find_by_id(user_id)

        if not user:
            return jsonify({'error': 'Invalid token'}), 401

        return jsonify({
            'valid': True,
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': f'Token verification failed: {str(e)}'}), 401
