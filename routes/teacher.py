from flask import Blueprint, request, jsonify
from db import SessionLocal
from models import Teacher, Session, Classroom, Student
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
    data = request.get_json() or {}
    print(f"[DEBUG] Create session request data: {data}")
    print(f"[DEBUG] Teacher ID: {request.teacher_id}")
    db = SessionLocal()
    try:
        # sanitize word_limit to always be an integer
        word_limit = data.get("word_limit", 3)
        try:
            word_limit = int(word_limit)
        except (ValueError, TypeError):
            word_limit = 3

        # class_id is now required
        class_id = data.get("class_id")
        if not class_id:
            return jsonify({"success": False, "error": "class_id is required"}), 400
        
        # Convert to int if it's a string
        try:
            class_id = int(class_id)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "invalid class_id"}), 400
        
        # Verify class belongs to teacher
        classroom = db.query(Classroom).filter_by(id=class_id, teacher_id=request.teacher_id).first()
        if not classroom:
            return jsonify({"success": False, "error": "class not found or access denied"}), 404

        # Generate unique code (retry if duplicate)
        max_attempts = 10
        code = None
        for attempt in range(max_attempts):
            code = generate_code()
            existing = db.query(Session).filter_by(code=code).first()
            if not existing:
                break
            if attempt == max_attempts - 1:
                return jsonify({"success": False, "error": "failed to generate unique session code"}), 500

        session = Session(
            code=code,
            class_id=class_id,
            word_limit=word_limit,
            is_active=False,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return jsonify({"success": True, "code": code})
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        print(f"[ERROR] Create session error: {error_msg}")
        import traceback
        traceback.print_exc()
        # Return more user-friendly error message
        if "foreign key" in error_msg.lower() or "constraint" in error_msg.lower():
            return jsonify({"success": False, "error": "database constraint error. Please check if the class exists."}), 500
        return jsonify({"success": False, "error": error_msg}), 500
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

        # broadcast to students
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


# -------------------------------------------------
# CLASS MANAGEMENT
# -------------------------------------------------
@teacher_bp.post("/classes")
@require_auth
def create_class():
    data = request.get_json()
    db = SessionLocal()
    try:
        if not data.get("name"):
            return jsonify({"success": False, "error": "class name required"}), 400

        classroom = Classroom(
            name=data["name"],
            teacher_id=request.teacher_id,
        )
        db.add(classroom)
        db.commit()
        return jsonify({"success": True, "class": {"id": classroom.id, "name": classroom.name}})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@teacher_bp.get("/classes")
@require_auth
def list_classes():
    db = SessionLocal()
    try:
        classes = db.query(Classroom).filter_by(teacher_id=request.teacher_id).all()
        return jsonify({
            "success": True,
            "classes": [
                {
                    "id": c.id,
                    "name": c.name,
                    "student_count": len(c.students),
                }
                for c in classes
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@teacher_bp.delete("/classes/<int:class_id>")
@require_auth
def delete_class(class_id):
    db = SessionLocal()
    try:
        classroom = db.query(Classroom).filter_by(id=class_id, teacher_id=request.teacher_id).first()
        if not classroom:
            return jsonify({"success": False, "error": "class not found"}), 404

        db.delete(classroom)
        db.commit()
        return jsonify({"success": True, "message": "class deleted"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


# -------------------------------------------------
# STUDENT MANAGEMENT
# -------------------------------------------------
@teacher_bp.post("/classes/<int:class_id>/students")
@require_auth
def create_student(class_id):
    data = request.get_json()
    db = SessionLocal()
    try:
        classroom = db.query(Classroom).filter_by(id=class_id, teacher_id=request.teacher_id).first()
        if not classroom:
            return jsonify({"success": False, "error": "class not found"}), 404

        if not data.get("full_name"):
            return jsonify({"success": False, "error": "student name required"}), 400
        
        if not data.get("file_number"):
            return jsonify({"success": False, "error": "file number required"}), 400

        # Check if file number already exists in this class
        existing = db.query(Student).filter_by(
            class_id=class_id,
            file_number=data.get("file_number").strip()
        ).first()
        if existing:
            return jsonify({"success": False, "error": "file number already exists in this class"}), 400

        student = Student(
            full_name=data["full_name"],
            file_number=data["file_number"].strip(),
            class_id=class_id,
        )
        db.add(student)
        db.commit()
        return jsonify({"success": True, "student": {"id": student.id, "full_name": student.full_name, "file_number": student.file_number}})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@teacher_bp.get("/classes/<int:class_id>/students")
@require_auth
def list_students(class_id):
    db = SessionLocal()
    try:
        classroom = db.query(Classroom).filter_by(id=class_id, teacher_id=request.teacher_id).first()
        if not classroom:
            return jsonify({"success": False, "error": "class not found"}), 404

        return jsonify({
            "success": True,
            "students": [
                {"id": s.id, "full_name": s.full_name, "file_number": s.file_number}
                for s in classroom.students
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@teacher_bp.delete("/classes/<int:class_id>/students/<int:student_id>")
@require_auth
def delete_student(class_id, student_id):
    db = SessionLocal()
    try:
        classroom = db.query(Classroom).filter_by(id=class_id, teacher_id=request.teacher_id).first()
        if not classroom:
            return jsonify({"success": False, "error": "class not found"}), 404

        student = db.query(Student).filter_by(id=student_id, class_id=class_id).first()
        if not student:
            return jsonify({"success": False, "error": "student not found"}), 404

        db.delete(student)
        db.commit()
        return jsonify({"success": True, "message": "student deleted"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()
