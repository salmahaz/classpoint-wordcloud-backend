from flask import Blueprint, request, jsonify
from db import SessionLocal
from models import Teacher, Session
from utils import hash_password, verify_password, generate_code
from datetime import datetime, timedelta
from functools import wraps
import jwt, os
from sockets import socketio

teacher_bp = Blueprint("teacher", __name__)
SECRET_KEY = os.getenv("JWT_SECRET", "devsecret")


# -------------------------------------------------
# AUTH DECORATOR
# -------------------------------------------------
def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"success": False, "error": "missing token"}), 401
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.teacher_id = decoded["teacher_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "error": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "error": "invalid token"}), 401
        return f(*args, **kwargs)
    return wrapper


# -------------------------------------------------
# REGISTER
# -------------------------------------------------
@teacher_bp.post("/register")
def register_teacher():
    data = request.get_json()
    db = SessionLocal()
    try:
        if db.query(Teacher).filter_by(email=data["email"]).first():
            return jsonify({"success": False, "error": "email exists"}), 400

        teacher = Teacher(
            full_name=data["full_name"],
            email=data["email"],
            password_hash=hash_password(data["password"]),
        )
        db.add(teacher)
        db.commit()
        return jsonify({"success": True, "message": "account created successfully"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


# -------------------------------------------------
# LOGIN
# -------------------------------------------------
@teacher_bp.post("/login")
def login_teacher():
    data = request.get_json()
    db = SessionLocal()
    try:
        teacher = db.query(Teacher).filter_by(email=data["email"]).first()
        if not teacher or not verify_password(data["password"], teacher.password_hash):
            return jsonify({"success": False, "error": "invalid credentials"}), 401

        payload = {
            "teacher_id": teacher.id,
            "email": teacher.email,
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "success": True,
                "token": token,
                "teacher_id": teacher.id,
                "name": teacher.full_name,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


# -------------------------------------------------
# VERIFY TOKEN
# -------------------------------------------------
@teacher_bp.get("/verify-token")
@require_auth
def verify_token():
    return jsonify({"success": True, "message": "Token is valid"})


# -------------------------------------------------
# CREATE SESSION
# -------------------------------------------------
@teacher_bp.post("/create-session")
@require_auth
def create_session():
    data = request.get_json()
    db = SessionLocal()
    try:
        code = generate_code()
        session = Session(
            code=code,
            teacher_id=request.teacher_id,
            word_limit=data.get("word_limit", 3),
            is_active=False,
        )
        db.add(session)
        db.commit()
        return jsonify({"success": True, "code": code})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


# -------------------------------------------------
# START SESSION (now supports slide image broadcast)
# -------------------------------------------------
@teacher_bp.post("/start-session")
@require_auth
def start_session():
    data = request.get_json()
    slide_image = data.get("slide_image")  # base64 image string from teacher
    db = SessionLocal()
    try:
        session = db.query(Session).filter_by(code=data["code"]).first()
        if not session:
            return jsonify({"success": False, "error": "session not found"}), 404

        session.is_active = True
        session.start_time = datetime.utcnow()
        db.commit()

        # 🔹 broadcast to students
        socketio.emit(
            "slide_image",
            {"code": session.code, "slide": slide_image},
            room=session.code,
        )

        return jsonify({"success": True, "message": "session started"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


# -------------------------------------------------
# END SESSION
# -------------------------------------------------
@teacher_bp.post("/end-session")
@require_auth
def end_session():
    data = request.get_json()
    db = SessionLocal()
    try:
        session = db.query(Session).filter_by(code=data["code"]).first()
        if not session:
            return jsonify({"success": False, "error": "session not found"}), 404

        session.is_active = False
        session.end_time = datetime.utcnow()
        db.commit()
        return jsonify({"success": True, "message": "session ended"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()
