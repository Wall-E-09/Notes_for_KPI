from models import Users, Notes, Settings, Attachments, Admin

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
    
    def create_user(self, username, email, password):
        return Users.create_user(username, email, password)
    
    def create_note(self, user_id, title, content, note_type, is_encrypted=False):
        return Notes.create_note(user_id, title, content, note_type, is_encrypted)
    
    def get_user_notes(self, user_id):
        return list(Notes.find({"user_id": user_id}))