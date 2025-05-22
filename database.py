from models import Users, Notes, Settings, Attachments, Admin
from bson import ObjectId

class Database:
    def __init__(self):
        self.create_indexes()
    
    def create_indexes(self):
        Users.create_indexes()
        Notes.create_indexes()
        Settings.create_indexes()
        Attachments.create_indexes()
        Admin.create_indexes()
    
    def get_user_by_email(self, email):
        return Users.find_one({"email": email})
    
    def get_user_by_id(self, user_id):
        return Users.find_one({"_id": ObjectId(user_id)})
    
    def create_user(self, username, email, password):
        return Users.create_user(username, email, password)
    
    def create_note(self, user_id, title, content, note_type, is_encrypted=False):
        return Notes.create_note(user_id, title, content, note_type, is_encrypted)
    
    def get_user_notes(self, user_id):
        return list(Notes.find({"user_id": user_id}))
    
    def update_note(self, note_id, user_id, update_data):
        return Notes.update_one(
            {"_id": ObjectId(note_id), "user_id": user_id},
            update_data
        )
    
    def delete_note(self, note_id, user_id):
        return Notes.delete_one({"_id": ObjectId(note_id), "user_id": user_id})
    
    def search_notes(self, user_id, query):
        return list(Notes.find({
            "user_id": user_id,
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"content": {"$regex": query, "$options": "i"}}
            ]
        }))
    
    def create_settings(self, user_id):
        return Settings.create_settings(user_id)
    
    def create_attachment(self, note_id, file_type, file_path):
        return Attachments.create_attachment(note_id, file_type, file_path)
    
    def create_admin(self, user_id, permissions):
        return Admin.create_admin(user_id, permissions)
    
    def delete_all_notes(self, user_id):
        return Notes.delete_many({"user_id": user_id})