from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from sockets import socketio
from db import Base, engine
from routes.teacher import teacher_bp
from routes.student import student_bp
# Import models so they register with Base.metadata before create_all()
from models import Teacher, Classroom, Student, Session, Response
import os

# -------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# -------------------------------------------------
load_dotenv()

# -------------------------------------------------
# APP INITIALIZATION
# -------------------------------------------------
app = Flask(__name__)

# -------------------------------------------------
# CORS CONFIGURATION
# -------------------------------------------------
# frontend URLs for both local & deployed versions
# Support multiple URLs: comma-separated in FRONTEND_URL env var
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
FRONTEND_URLS = [url.strip() for url in FRONTEND_URL.split(",") if url.strip()]

ALLOWED_ORIGINS = [
    *FRONTEND_URLS,
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    # Remove duplicates while preserving order
]
# Remove duplicates while preserving order
seen = set()
ALLOWED_ORIGINS = [x for x in ALLOWED_ORIGINS if not (x in seen or seen.add(x))]

CORS(
    app,
    resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
    supports_credentials=True,
)

# -------------------------------------------------
# SOCKET.IO INITIALIZATION
# -------------------------------------------------
socketio.init_app(app, cors_allowed_origins="*")

# -------------------------------------------------
# DATABASE SETUP
# -------------------------------------------------
try:
    Base.metadata.create_all(bind=engine)
    # List all tables that were created/verified
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"[DB] Tables ensured successfully: {', '.join(tables)}")
except Exception as e:
    print(f"[DB] Error creating tables: {e}")
    import traceback
    traceback.print_exc()

# -------------------------------------------------
# BLUEPRINT REGISTRATION
# -------------------------------------------------
app.register_blueprint(teacher_bp, url_prefix="/api/teacher")
app.register_blueprint(student_bp, url_prefix="/api/student")

# -------------------------------------------------
# ROOT ENDPOINT
# -------------------------------------------------
@app.get("/")
def home():
    return jsonify({
        "message": "Word Cloud Backend running with Flask + Socket.IO",
        "environment": os.getenv("FLASK_ENV", "development"),
    }), 200

# -------------------------------------------------
# MAIN ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    env = os.getenv("FLASK_ENV", "development")

    print("\n==========================================")
    print("Flask Word Cloud Backend Starting...")
    print(f"Environment: {env}")
    print(f"Database URL: {os.getenv('DATABASE_URL', 'not set')}")
    print(f"JWT Secret: {'set' if os.getenv('JWT_SECRET') else 'missing!'}")
    print(f"Allowed Frontend Origins: {ALLOWED_ORIGINS}")
    print(f"Running on http://0.0.0.0:{port}")
    print("==========================================\n")

    # Allow Werkzeug for Render
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
