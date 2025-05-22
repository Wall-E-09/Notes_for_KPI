import asyncio
import websockets
import json
from datetime import datetime
from bson import json_util, ObjectId
from database import Database
from utils import Encryption
from config import Config

class NoteServer:
    def __init__(self):
        self.db = Database()
        self.clients = {}
        self.sessions = {}

    async def handle_client(self, websocket, path=None):
        client_id = None
        try:
            init_data = json.loads(await websocket.recv())
            client_id = init_data.get('client_id', str(datetime.now().timestamp()))
            self.clients[client_id] = websocket
            print(f"Client {client_id} connected")

            await websocket.send(json.dumps({
                "status": "connected",
                "client_id": client_id
            }))

            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self.process_message(data, client_id)
                    await websocket.send(json_util.dumps(response))
                except Exception as e:
                    print(f"Processing error: {e}")
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Invalid request"
                    }))

        except websockets.exceptions.ConnectionClosed:
            print(f"Client {client_id} disconnected")
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            if client_id in self.clients:
                self.clients.pop(client_id)
            print(f"Client {client_id} removed")

    async def process_message(self, data, client_id):
        action = data.get('action')
        
        if action == 'login':
            return await self.handle_login(data, client_id)
        elif action == 'register':
            return await self.handle_register(data)
        elif action == 'create_note':
            return await self.handle_create_note(data)
        elif action == 'get_notes':
            return await self.handle_get_notes(data)
        elif action == 'update_note':
            return await self.handle_update_note(data)
        elif action == 'delete_note':
            return await self.handle_delete_note(data)
        elif action == 'search_notes':
            return await self.handle_search_notes(data)
        elif action == 'logout':
            return await self.handle_logout(data)
        elif action == 'init' or action == 'restore_session':
            return {"status": "connected"}
        elif action == 'delete_all_notes':
            return await self.handle_delete_all_notes(data)
        else:
            return {"status": "error", "message": "Unknown action"}

    async def handle_login(self, data, client_id):
        email = data.get('email')
        password = data.get('password')
        
        user = self.db.get_user_by_email(email)
        if not user:
            return {
                "status": "error",
                "action": "login",
                "message": "User not found"
            }
        
        if user['password'] != password:
            return {
                "status": "error",
                "action": "login",
                "message": "Invalid password"
            }
        
        user_id = str(user['_id'])
        self.sessions[user_id] = client_id
        
        return {
            "status": "success",
            "action": "login",
            "message": "Login successful",
            "user": {
                "id": user_id,
                "username": user['username'],
                "email": user['email']
            }
        }

    async def handle_register(self, data):
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        try:
            result = self.db.create_user(username, email, password)
            self.db.create_settings(str(result.inserted_id))
            return {
                "status": "success",
                "action": "register",
                "message": "User created successfully",
                "user_id": str(result.inserted_id)
            }
        except Exception as e:
            return {
                "status": "error",
                "action": "register",
                "message": str(e)
            }

    async def handle_create_note(self, data):
        user_id = data.get('user_id')  # Can be None for anonymous notes
        title = data.get('title')
        content = data.get('content')
        note_type = data.get('note_type', 'text')
        encrypt = data.get('encrypt', False)
        
        if encrypt:
            content = Encryption.encrypt(content)
        
        try:
            result = self.db.create_note(user_id, title, content, note_type, encrypt)
            return {
                "status": "success",
                "action": "create_note",
                "message": "Note created successfully",
                "note_id": str(result.inserted_id)
            }
        except Exception as e:
            return {
                "status": "error",
                "action": "create_note",
                "message": str(e)
            }

    async def handle_get_notes(self, data):
        user_id = data.get('user_id')
        if not user_id:
            return {
                "status": "error",
                "action": "get_notes",
                "message": "You need to login to view your notes"
            }
        
        notes = self.db.get_user_notes(user_id)
        
        notes_list = []
        for note in notes:
            note_data = {
                "_id": str(note['_id']),
                "user_id": note.get('user_id', ''),
                "title": note.get('title', 'Untitled'),
                "content": note.get('content', ''),
                "note_type": note.get('note_type', 'text'),
                "time_creation": note.get('time_creation', datetime.now()).isoformat(),
                "is_encrypted": note.get('is_encrypted', False)
            }
            
            if note_data['is_encrypted']:
                try:
                    note_data['content'] = Encryption.decrypt(note_data['content'])
                except Exception as e:
                    print(f"Error decrypting note {note_data['_id']}: {str(e)}")
                    note_data['content'] = '[Encrypted content - please edit to view]'
            
            notes_list.append(note_data)
        
        return {
            "status": "success",
            "action": "get_notes",
            "notes": notes_list
        }

    async def handle_update_note(self, data):
        user_id = data.get('user_id')
        note_id = data.get('note_id')
        update_data = data.get('update_data', {})
        
        if not ObjectId.is_valid(note_id):
            return {
                "status": "error",
                "action": "update_note",
                "message": "Invalid note ID"
            }
        
        if 'content' in update_data and update_data.get('encrypt', False):
            update_data['content'] = Encryption.encrypt(update_data['content'])
            update_data['is_encrypted'] = True
        
        update_data['time_update'] = datetime.now()
        
        try:
            result = self.db.update_note(note_id, user_id, update_data)
            if result.modified_count == 0:
                return {
                    "status": "error",
                    "action": "update_note",
                    "message": "Note not found or not updated"
                }
            
            return {
                "status": "success",
                "action": "update_note",
                "message": "Note updated successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "action": "update_note",
                "message": str(e)
            }

    async def handle_delete_note(self, data):
        user_id = data.get('user_id')
        note_id = data.get('note_id')
        
        if not ObjectId.is_valid(note_id):
            return {
                "status": "error",
                "action": "delete_note",
                "message": "Invalid note ID"
            }
        
        try:
            result = self.db.delete_note(note_id, user_id)
            if result.deleted_count == 0:
                return {
                    "status": "error",
                    "action": "delete_note",
                    "message": "Note not found or not deleted"
                }
            
            return {
                "status": "success",
                "action": "delete_note",
                "message": "Note deleted successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "action": "delete_note",
                "message": str(e)
            }

    async def handle_search_notes(self, data):
        user_id = data.get('user_id')
        query = data.get('query', '')
        
        if not user_id:
            return {
                "status": "error",
                "action": "search_notes",
                "message": "You need to login to search notes"
            }
        
        notes = self.db.search_notes(user_id, query)
        
        notes_list = []
        for note in notes:
            note_data = {
                "_id": str(note['_id']),
                "user_id": note.get('user_id', ''),
                "title": note.get('title', 'Untitled'),
                "content": note.get('content', ''),
                "note_type": note.get('note_type', 'text'),
                "time_creation": note.get('time_creation', datetime.now()).isoformat(),
                "is_encrypted": note.get('is_encrypted', False)
            }
            
            if note_data['is_encrypted']:
                try:
                    note_data['content'] = Encryption.decrypt(note_data['content'])
                except:
                    note_data['content'] = '[Encrypted content - please edit to view]'
            
            notes_list.append(note_data)
        
        return {
            "status": "success",
            "action": "search_notes",
            "notes": notes_list
        }

    async def handle_logout(self, data):
        user_id = data.get('user_id')
        if user_id in self.sessions:
            self.sessions.pop(user_id)
        return {
            "status": "success",
            "action": "logout",
            "message": "Logged out"
        }

    async def run(self):
        start_server = websockets.serve(
            self.handle_client,
            Config.WEBSOCKET_HOST,
            Config.WEBSOCKET_PORT,
            ping_interval=None,
            ping_timeout=None
        )
        server = await start_server
        print(f"Server started on ws://{Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_PORT}")
        
        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            print("\nServer shutting down...")
            server.close()
            await server.wait_closed()

    async def handle_delete_all_notes(self, data):
        user_id = data.get('user_id')
        if not user_id:
            return {
                "status": "error",
                "action": "delete_all_notes",
                "message": "You need to login to delete notes"
            }
        
        try:
            result = Notes.delete_many({"user_id": user_id})
            return {
                "status": "success",
                "action": "delete_all_notes",
                "message": f"Deleted {result.deleted_count} notes"
            }
        except Exception as e:
            return {
                "status": "error",
                "action": "delete_all_notes",
                "message": str(e)
            }

if __name__ == "__main__":
    server = NoteServer()
    asyncio.get_event_loop().run_until_complete(server.run())