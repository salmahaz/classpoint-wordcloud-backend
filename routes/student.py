from flask import Blueprint, request, jsonify
from flask import Response
from db import SessionLocal
from models import Teacher, Session
from utils import hash_password, verify_password, generate_code

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
            return jsonify({"success": False, "error": "invalid session"}), 404

        # ensure session is active before allowing join
        if not s.is_active:
            return jsonify({"success": False, "error": "session is not active"}), 403

        return jsonify({"success": True, "title": f"Word Cloud – {s.teacher.full_name}"})
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

        # enforce word limit per student
        count = db.query(Response).filter_by(session_id=s.id, student_name=name).count()
        if count >= s.word_limit:
            return jsonify({"success": False, "error": "limit reached"}), 403

        # save response
        r = Response(student_name=name or "Anonymous", word=word, session_id=s.id)
        db.add(r)
        db.commit()

        # broadcast to teacher dashboard in real time
        socketio.emit("new_word", {"word": word, "name": name or "Anonymous"}, room=code)

        return jsonify({"success": True, "message": "word submitted successfully"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()
