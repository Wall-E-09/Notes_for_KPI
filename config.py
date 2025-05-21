class Config:
    MONGO_URI = "mongodb://localhost:27017/"
    DB_NAME = "notes_app"
    WEBSOCKET_HOST = "127.0.0.1"  # Використовуємо IP замість localhost для надійності
    WEBSOCKET_PORT = 8765
    ENCRYPTION_KEY = "my_super_secret_key_123"  # У реальному додатку використовуйте безпечний ключ
    RECONNECT_DELAY = 3  # секунди між спробами перепідключення
    PING_INTERVAL = 30  # інтервал ping для підтримки з'єднання