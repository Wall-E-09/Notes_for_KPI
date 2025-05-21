from cryptography.fernet import Fernet
from config import Config
import base64
import hashlib

class Encryption:
    @staticmethod
    def _get_cipher(key=None):
        if key is None:
            key = Config.ENCRYPTION_KEY
        key_bytes = hashlib.sha256(key.encode()).digest()
        key_base64 = base64.urlsafe_b64encode(key_bytes)
        return Fernet(key_base64)
    
    @staticmethod
    def encrypt(data, key=None):
        cipher = Encryption._get_cipher(key)
        if isinstance(data, str):
            data = data.encode()
        return cipher.encrypt(data).decode()
    
    @staticmethod
    def decrypt(encrypted_data, key=None):
        cipher = Encryption._get_cipher(key)
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        return cipher.decrypt(encrypted_data).decode()