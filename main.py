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

# Configure CORS with explicit methods and headers
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

# -------------------------------------------------
# SOCKET.IO INITIALIZATION
# -------------------------------------------------
socketio.init_app(app, cors_allowed_origins="*")

# -------------------------------------------------
# DATABASE SETUP
# -------------------------------------------------
def migrate_database():
    """Add missing columns to existing tables"""
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    
    # Check if students table exists and if file_number column is missing
    if 'students' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('students')]
        if 'file_number' not in columns:
            print("[DB] Adding file_number column to students table...")
            try:
                with engine.begin() as conn:
                    # Add file_number column (nullable for existing records, but new records will require it)
                    conn.execute(text("ALTER TABLE students ADD COLUMN file_number VARCHAR(50)"))
                print("[DB] Successfully added file_number column")
            except Exception as e:
                print(f"[DB] Error adding file_number column: {e}")
                import traceback
                traceback.print_exc()
                # Continue anyway - the app might still work if column gets added manually
    
    # Check if sessions table exists and if class_id column is missing
    if 'sessions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('sessions')]
        if 'class_id' not in columns:
            print("[DB] Adding class_id column to sessions table...")
            try:
                with engine.begin() as conn:
                    # Add class_id column (nullable for existing records, but new records will require it)
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN class_id INTEGER"))
                    # Add foreign key constraint if it doesn't exist
                    try:
                        conn.execute(text("ALTER TABLE sessions ADD CONSTRAINT fk_sessions_class_id FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE"))
                    except Exception as fk_err:
                        # Foreign key might already exist or table might not exist yet
                        print(f"[DB] Note: Could not add foreign key constraint (may already exist): {fk_err}")
                print("[DB] Successfully added class_id column to sessions table")
            except Exception as e:
                print(f"[DB] Error adding class_id column: {e}")
                import traceback
                traceback.print_exc()
                # Continue anyway - the app might still work if column gets added manually
    
    # Check if responses table exists and if student_id or session_id columns are missing
    if 'responses' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('responses')]
        
        if 'student_id' not in columns:
            print("[DB] Adding student_id column to responses table...")
            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE responses ADD COLUMN student_id INTEGER"))
                    try:
                        conn.execute(text("ALTER TABLE responses ADD CONSTRAINT fk_responses_student_id FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE"))
                    except Exception as fk_err:
                        print(f"[DB] Note: Could not add student_id foreign key constraint (may already exist): {fk_err}")
                print("[DB] Successfully added student_id column to responses table")
            except Exception as e:
                print(f"[DB] Error adding student_id column: {e}")
                import traceback
                traceback.print_exc()
        
        if 'session_id' not in columns:
            print("[DB] Adding session_id column to responses table...")
            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE responses ADD COLUMN session_id INTEGER"))
                    try:
                        conn.execute(text("ALTER TABLE responses ADD CONSTRAINT fk_responses_session_id FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE"))
                    except Exception as fk_err:
                        print(f"[DB] Note: Could not add session_id foreign key constraint (may already exist): {fk_err}")
                print("[DB] Successfully added session_id column to responses table")
            except Exception as e:
                print(f"[DB] Error adding session_id column: {e}")
                import traceback
                traceback.print_exc()

try:
    Base.metadata.create_all(bind=engine)
    # Run migrations
    migrate_database()
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
        "allowed_origins": ALLOWED_ORIGINS,
    }), 200

# -------------------------------------------------
# HEALTH CHECK ENDPOINT
# -------------------------------------------------
@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "allowed_origins": ALLOWED_ORIGINS,
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
