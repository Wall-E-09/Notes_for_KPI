class Config:
    MONGO_URI = "mongodb://localhost:27017/"
    DB_NAME = "notes_app"
    WEBSOCKET_HOST = "127.0.0.1"
    WEBSOCKET_PORT = 8765
    ENCRYPTION_KEY = "ENCRYPTION_KEY"
    RECONNECT_DELAY = 3
    PING_INTERVAL = 30