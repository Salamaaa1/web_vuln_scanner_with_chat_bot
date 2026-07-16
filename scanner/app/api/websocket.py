import socketio

# Setup Socket.IO async server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socketio_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
