# """
# Authentication routes for user signup and login.
# Fully supports MongoDB User model methods.
# """

# from flask import Blueprint, request, jsonify
# from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
# from datetime import timedelta
# import re

# # ✅ Correct MongoDB Import
# from models_mongo import User

# auth_bp = Blueprint('auth', __name__)

# # ----------------- Validators -----------------
# EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# PHONE_RE = re.compile(r"^\+\d{10,15}$")


# def normalize_whatsapp_number(number: str) -> str:
#     """Normalize number => +<digits> format"""
#     number = (number or "").strip().replace(" ", "").replace("-", "")
#     digits = "".join(ch for ch in number if ch.isdigit())
#     return f"+{digits}" if digits else ""


# # ----------------- SIGNUP -----------------
# @auth_bp.route('/signup', methods=['POST'])
# def signup():
#     try:
#         data = request.get_json() or {}

#         username = (data.get('username') or '').strip()
#         email = (data.get('email') or '').strip().lower()
#         password = data.get('password') or ''
#         whatsapp_number = normalize_whatsapp_number(data.get('whatsapp_number') or "")

#         # Required fields validation
#         if not username or not email or not password or not whatsapp_number:
#             return jsonify({"error": "All fields are required"}), 400

#         if len(username) < 3:
#             return jsonify({"error": "Username must be at least 3 characters"}), 400

#         if len(password) < 6:
#             return jsonify({"error": "Password must be at least 6 characters"}), 400

#         if not EMAIL_RE.match(email):
#             return jsonify({"error": "Invalid email format"}), 400

#         if not PHONE_RE.match(whatsapp_number):
#             return jsonify({"error": "Invalid WhatsApp number format"}), 400

#         # ✅ Check for duplicates
#         if User.find_by_username(username):
#             return jsonify({"error": "Username already exists"}), 409

#         if User.find_by_email(email):
#             return jsonify({"error": "Email already registered"}), 409

#         if User.find_by_whatsapp(whatsapp_number):
#             return jsonify({"error": "WhatsApp number already registered"}), 409

#         # ✅ Create user
#         user = User(
#             username=username,
#             email=email,
#             password=password,  # password gets hashed automatically
#             whatsapp_number=whatsapp_number
#         )
#         user.save()

#         # ✅ JWT Token
#         token = create_access_token(
#             identity=str(user.id),
#             expires_delta=timedelta(days=7)
#         )

#         return jsonify({
#             "message": "Signup successful",
#             "access_token": token,
#             "user": user.to_dict()
#         }), 201

#     except Exception as e:
#         print("[Signup Error]", e)
#         return jsonify({"error": f"Registration failed: {str(e)}"}), 500


# # ----------------- LOGIN -----------------
# @auth_bp.route('/login', methods=['POST'])
# def login():
#     try:
#         data = request.get_json() or {}

#         username_or_email = (data.get('username') or '').strip().lower()
#         password = data.get('password') or ''

#         if not username_or_email or not password:
#             return jsonify({"error": "Missing username or password"}), 400

#         # ✅ Check username first, then email
#         user = User.find_by_username(username_or_email)
#         if not user:
#             user = User.find_by_email(username_or_email)

#         if not user or not user.check_password(password):
#             return jsonify({"error": "Invalid credentials"}), 401

#         token = create_access_token(
#             identity=str(user.id),
#             expires_delta=timedelta(days=7)
#         )

#         return jsonify({
#             "message": "Login successful",
#             "access_token": token,
#             "user": user.to_dict()
#         }), 200

#     except Exception as e:
#         print("[Login Error]", e)
#         return jsonify({"error": f"Login failed: {str(e)}"}), 500


# # ----------------- PROFILE -----------------
# @auth_bp.route('/profile', methods=['GET'])
# @jwt_required()
# def profile():
#     try:
#         user_id = int(get_jwt_identity())
#         user = User.find_by_id(user_id)

#         if not user:
#             return jsonify({"error": "User not found"}), 404

#         return jsonify({"user": user.to_dict()}), 200

#     except Exception as e:
#         return jsonify({"error": f"Failed to load profile: {str(e)}"}), 500


# # ----------------- VERIFY TOKEN -----------------
# @auth_bp.route('/verify', methods=['GET'])
# @jwt_required()
# def verify_token():
#     try:
#         user_id = int(get_jwt_identity())
#         user = User.find_by_id(user_id)

#         if not user:
#             return jsonify({"valid": False}), 401

#         return jsonify({"valid": True, "user": user.to_dict()}), 200

#     except Exception:
#         return jsonify({"valid": False}), 401


# ...existing code...
"""
Authentication routes for user signup and login.
Fully supports MongoDB User model methods.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
import re
import traceback

# ✅ Correct MongoDB Import
from models_mongo import User

auth_bp = Blueprint('auth', __name__)

# ----------------- Validators -----------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+\d{10,15}$")


def normalize_whatsapp_number(number: str) -> str:
    """Normalize number => +<digits> format"""
    number = (number or "").strip().replace(" ", "").replace("-", "")
    digits = "".join(ch for ch in number if ch.isdigit())
    return f"+{digits}" if digits else ""


# ----------------- SIGNUP -----------------
@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        # Robust JSON/form parsing
        data = None
        if request.is_json:
            data = request.get_json(silent=True)
        if data is None:
            # fallback to form-encoded payloads
            try:
                data = request.form.to_dict() or {}
            except Exception:
                data = {}

        if not isinstance(data, dict) or not data:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        # Debug/log incoming payload for easier diagnosis
        print("[Signup payload]", data)

        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        whatsapp_number = normalize_whatsapp_number(data.get('whatsapp_number') or "")

        # Required fields validation
        if not username or not email or not password or not whatsapp_number:
            return jsonify({"error": "All fields are required"}), 400

        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        if not EMAIL_RE.match(email):
            return jsonify({"error": "Invalid email format"}), 400

        if not PHONE_RE.match(whatsapp_number):
            return jsonify({"error": "Invalid WhatsApp number format"}), 400

        # ✅ Check for duplicates
        if User.find_by_username(username):
            return jsonify({"error": "Username already exists"}), 409

        if User.find_by_email(email):
            return jsonify({"error": "Email already registered"}), 409

        if User.find_by_whatsapp(whatsapp_number):
            return jsonify({"error": "WhatsApp number already registered"}), 409

        # ✅ Create user
        user = User(
            username=username,
            email=email,
            password=password,  # password gets hashed automatically
            whatsapp_number=whatsapp_number
        )
        user.save()

        # ✅ JWT Token
        token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=7)
        )

        return jsonify({
            "message": "Signup successful",
            "access_token": token,
            "user": user.to_dict()
        }), 201

    except Exception as e:
        # Print full traceback to help identify where 'NoneType' arose
        print("[Signup Error]", e)
        print(traceback.format_exc())
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


# ----------------- LOGIN -----------------
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = None
        if request.is_json:
            data = request.get_json(silent=True)
        if data is None:
            try:
                data = request.form.to_dict() or {}
            except Exception:
                data = {}

        if not isinstance(data, dict):
            return jsonify({"error": "Invalid request payload"}), 400

        username_or_email = (data.get('username') or '').strip().lower()
        password = data.get('password') or ''

        if not username_or_email or not password:
            return jsonify({"error": "Missing username or password"}), 400

        # ✅ Check username first, then email
        user = User.find_by_username(username_or_email)
        if not user:
            user = User.find_by_email(username_or_email)

        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid credentials"}), 401

        token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=7)
        )

        return jsonify({
            "message": "Login successful",
            "access_token": token,
            "user": user.to_dict()
        }), 200

    except Exception as e:
        print("[Login Error]", e)
        print(traceback.format_exc())
        return jsonify({"error": f"Login failed: {str(e)}"}), 500


# ----------------- PROFILE -----------------
@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    try:
        # Do not force-cast identity to int; accept whatever form the User model expects
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"user": user.to_dict()}), 200

    except Exception as e:
        print("[Profile Error]", e)
        print(traceback.format_exc())
        return jsonify({"error": f"Failed to load profile: {str(e)}"}), 500


# ----------------- VERIFY TOKEN -----------------
@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    try:
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)

        if not user:
            return jsonify({"valid": False}), 401

        return jsonify({"valid": True, "user": user.to_dict()}), 200

    except Exception:
        print("[Verify Error]", traceback.format_exc())
        return jsonify({"valid": False}), 401
# ...existing code...