from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies
)
from extensions import db, bcrypt
from models import User, UserRole

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}

    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role_str = (data.get("role") or "user").strip().lower()

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if role_str not in ("organizer", "user"):
        return jsonify({"error": "role must be 'organizer' or 'user'"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(
        name=name,
        email=email,
        password=hashed_pw,
        role=UserRole[role_str],
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Account created successfully", "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role.value, "name": user.name}
    )

    response = make_response(jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": user.to_dict(),
    }))

    response.set_cookie(
        "access_token_cookie", access_token,
        httponly=True, samesite="Lax", max_age=28800
    )
    return response, 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    response = make_response(jsonify({"message": "Logged out"}))
    unset_jwt_cookies(response)
    return response, 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200
