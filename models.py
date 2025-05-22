from datetime import datetime
from pymongo import MongoClient, ASCENDING
from config import Config
from bson import ObjectId

class Model:
    _db = None
    _collection = None
    
    @classmethod
    def _get_db(cls):
        if cls._db is None:
            client = MongoClient(Config.MONGO_URI)
            cls._db = client[Config.DB_NAME]
        return cls._db
    
    @classmethod
    def get_collection(cls):
        if cls._collection is None:
            cls._collection = cls._get_db()[cls.__name__.lower()]
        return cls._collection
    
    @classmethod
    def create_indexes(cls):
        pass
    
    @classmethod
    def find_one(cls, query):
        return cls.get_collection().find_one(query)
    
    @classmethod
    def find(cls, query=None):
        if query is None:
            query = {}
        return cls.get_collection().find(query)
    
    @classmethod
    def insert_one(cls, data):
        return cls.get_collection().insert_one(data)
    
    @classmethod
    def update_one(cls, query, update_data):
        return cls.get_collection().update_one(query, {'$set': update_data})
    
    @classmethod
    def delete_one(cls, query):
        return cls.get_collection().delete_one(query)
    
    @classmethod
    def delete_many(cls, query):
        return cls.get_collection().delete_many(query)


class Users(Model):
    @classmethod
    def create_indexes(cls):
        cls.get_collection().create_index("email", unique=True)
    
    @classmethod
    def create_user(cls, username, email, password):
        user_data = {
            "username": username,
            "email": email,
            "password": password,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return cls.insert_one(user_data)


class Notes(Model):
    NOTE_TYPES = ["text", "voice", "image"]
    
    @classmethod
    def create_indexes(cls):
        cls.get_collection().create_index("user_id")
        cls.get_collection().create_index([("title", ASCENDING)])
    
    @classmethod
    def create_note(cls, user_id, title, content, note_type, is_encrypted=False, attachment=None):
        if note_type not in cls.NOTE_TYPES:
            raise ValueError(f"Invalid note type. Must be one of: {cls.NOTE_TYPES}")
        
        note_data = {
            "user_id": user_id,
            "title": title,
            "content": content,
            "note_type": note_type,
            "time_creation": datetime.now(),
            "time_update": datetime.now(),
            "is_encrypted": is_encrypted,
            "attachment": attachment
        }
        return cls.insert_one(note_data)


class Settings(Model):
    @classmethod
    def create_indexes(cls):
        cls.get_collection().create_index("user_id", unique=True)
    
    @classmethod
    def create_settings(cls, user_id):
        settings_data = {
            "user_id": user_id,
            "auto_save": True,
            "encryption_key": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return cls.insert_one(settings_data)


class Attachments(Model):
    @classmethod
    def create_indexes(cls):
        cls.get_collection().create_index("note_id")
    
    @classmethod
    def create_attachment(cls, note_id, file_type, file_path):
        attachment_data = {
            "note_id": note_id,
            "file_type": file_type,
            "file_path": file_path,
            "created_at": datetime.now()
        }
        return cls.insert_one(attachment_data)


class Admin(Model):
    @classmethod
    def create_indexes(cls):
        cls.get_collection().create_index("user_id", unique=True)
    
    @classmethod
    def create_admin(cls, user_id, permissions):
        admin_data = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": datetime.now()
        }
        return cls.insert_one(admin_data)