from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from backend.sockets import socketio
from backend.db import Base, engine
from backend.routes.teacher import teacher_bp
from backend.routes.student import student_bp
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
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

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
Base.metadata.create_all(bind=engine)

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
    return jsonify({"message": "word cloud backend running with Flask + Socket.IO"}), 200

# -------------------------------------------------
# MAIN ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    env = os.getenv("FLASK_ENV", "development")
    print("Flask Word Cloud Backend Starting...")
    print(f"Environment: {env}")
    print(f"Database: {os.getenv('DB_NAME')} on {os.getenv('DB_HOST')}")
    print(f"JWT Secret: {'set' if os.getenv('JWT_SECRET') else 'missing!'}")
    print(f"Allowed Frontend Origins: {ALLOWED_ORIGINS}")
    print(f"Running on http://0.0.0.0:{port}\n")

    socketio.run(app, host="0.0.0.0", port=port)
