import asyncio
import websockets
import json
from database import Database
from utils import Encryption
from datetime import datetime
from bson import json_util
from config import Config

class NoteServer:
    def __init__(self):
        self.db = Database()
        self.clients = {}
    
    async def handle_client(self, websocket, path=None):
        client_id = None
        try:
            # Отримуємо ініціалізаційне повідомлення
            init_message = await websocket.recv()
            data = json.loads(init_message)
            client_id = data.get("client_id", str(datetime.now().timestamp()))
            
            self.clients[client_id] = websocket
            print(f"Client {client_id} connected")

            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self.process_message(data)
                    # Використовуємо json_util для коректної серіалізації
                    await websocket.send(json_util.dumps(response))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Invalid JSON"
                    }))
                except Exception as e:
                    print(f"Processing error: {e}")
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Internal server error"
                    }))
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {client_id} disconnected")
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            if client_id:
                self.clients.pop(client_id, None)
                print(f"Client {client_id} removed")

    async def process_message(self, data):
        try:
            action = data.get("action")
            
            if action == "login":
                return await self.handle_login(data)
            elif action == "register":
                return await self.handle_register(data)
            elif action == "create_note":
                return await self.handle_create_note(data)
            elif action == "get_notes":
                return await self.handle_get_notes(data)
            else:
                return {"status": "error", "message": "Unknown action"}
        except Exception as e:
            print(f"Server error: {e}")
            return {"status": "error", "message": "Internal server error"}

    async def handle_login(self, data):
        email = data.get("email")
        password = data.get("password")
        
        user = self.db.get_user_by_email(email)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        if user["password"] != password:
            return {"status": "error", "message": "Invalid password"}
        
        return {
            "status": "success",
            "message": "Login successful",
            "user": {
                "id": str(user["_id"]),
                "username": user["username"],
                "email": user["email"]
            }
        }

    async def handle_register(self, data):
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        
        try:
            result = self.db.create_user(username, email, password)
            return {
                "status": "success",
                "message": "User created successfully",
                "user_id": str(result.inserted_id)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_create_note(self, data):
        user_id = data.get("user_id")
        title = data.get("title")
        content = data.get("content")
        note_type = data.get("note_type", "text")
        encrypt = data.get("encrypt", False)
        
        if encrypt:
            content = Encryption.encrypt(content)
        
        try:
            result = self.db.create_note(user_id, title, content, note_type, encrypt)
            return {
                "status": "success",
                "message": "Note created successfully",
                "note_id": str(result.inserted_id)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_get_notes(self, data):
        user_id = data.get("user_id")
        notes = self.db.get_user_notes(user_id)
        
        notes_list = []
        for note in notes:
            note["_id"] = str(note["_id"])
            if note.get("is_encrypted"):
                note["content"] = Encryption.decrypt(note["content"])
            # Конвертуємо datetime в рядок
            note["time_creation"] = note["time_creation"].isoformat()
            note["time_update"] = note["time_update"].isoformat()
            notes_list.append(note)
        
        return {
            "status": "success",
            "notes": notes_list
        }

    async def run(self):
        start_server = websockets.serve(
            self.handle_client,
            Config.WEBSOCKET_HOST,
            Config.WEBSOCKET_PORT
        )
        server = await start_server
        print(f"Server started on ws://{Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_PORT}")
        
        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            print("Server shutting down...")
            server.close()
            await server.wait_closed()

if __name__ == "__main__":
    server = NoteServer()
    asyncio.get_event_loop().run_until_complete(server.run())