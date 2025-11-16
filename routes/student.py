from flask import Blueprint, request, jsonify
from db import SessionLocal
from models import Session, Response as StudentResponse, Student, Classroom
from sockets import socketio

student_bp = Blueprint("student", __name__)

# -------------------------------------------------
# CHECK SESSION VALIDITY (for student join)
# -------------------------------------------------
@student_bp.post("/check-session")
def check_session():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()

    if not code:
        return jsonify({"success": False, "error": "missing code"}), 400

    db = SessionLocal()
    try:
        s = db.query(Session).filter_by(code=code).first()
        if not s:
            return jsonify({"success": False, "error": "no session with this code exists"}), 404

        # Get teacher name through classroom relationship
        teacher_name = "Teacher"
        if s.classroom and s.classroom.teacher:
            teacher_name = s.classroom.teacher.full_name

        # allow join even if inactive - submission will be blocked later
        return jsonify({
            "success": True, 
            "title": f"Word Cloud – {teacher_name}",
            "is_active": s.is_active
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


# -------------------------------------------------
# SUBMIT WORD
# -------------------------------------------------
@student_bp.post("/submit")
def submit_word():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()
    name = (data.get("name") or "").strip()
    word = (data.get("word") or "").strip()

    if not code or not word:
        return jsonify({"success": False, "error": "missing fields"}), 400

    db = SessionLocal()
    try:
        s = db.query(Session).filter_by(code=code).first()
        if not s:
            return jsonify({"success": False, "error": "invalid session"}), 404

        # block submission if session is inactive
        if not s.is_active:
            return jsonify({"success": False, "error": "session is not active"}), 403

        # Get or create student in the class
        if not s.classroom:
            return jsonify({"success": False, "error": "session has no associated class"}), 400

        student = db.query(Student).filter_by(
            class_id=s.classroom.id,
            full_name=name or "Anonymous"
        ).first()

        if not student:
            # Create student if doesn't exist
            student = Student(
                full_name=name or "Anonymous",
                class_id=s.classroom.id
            )
            db.add(student)
            db.flush()  # Get the student ID without committing

        # enforce word limit per student
        count = (
            db.query(StudentResponse)
            .filter_by(session_id=s.id, student_id=student.id)
            .count()
        )
        if count >= s.word_limit:
            return jsonify({"success": False, "error": "limit reached"}), 403

        # save response
        r = StudentResponse(
            student_id=student.id,
            word=word,
            session_id=s.id,
        )
        db.add(r)
        db.commit()

        # broadcast to teacher dashboard in real time
        socketio.emit(
            "new_word",
            {"word": word, "name": name or "Anonymous"},
            room=code,
        )

        return jsonify({"success": True, "message": "word submitted successfully"})
    except Exception as e:
        db.rollback()
        print("[ERROR]", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()
