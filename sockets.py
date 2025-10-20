from flask_socketio import SocketIO, join_room, leave_room, emit

socketio = SocketIO(cors_allowed_origins="*")

@socketio.on("join_session")
def handle_join(data):
    code = data.get("code")
    if code:
        join_room(code)
        emit("system", {"message": f"joined session {code}"}, room=code)

@socketio.on("leave_session")
def handle_leave(data):
    code = data.get("code")
    if code:
        leave_room(code)
