import asyncio
import websockets
import json
import uuid
from config import Config
from bson import json_util

class NoteClient:
    def __init__(self):
        self.websocket = None
        self.current_user = None
        self.client_id = str(uuid.uuid4())
        self.uri = f"ws://{Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_PORT}"
    
    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            # Відправляємо ініціалізаційне повідомлення
            await self.websocket.send(json.dumps({
                "action": "init",
                "client_id": self.client_id
            }))
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    async def send_request(self, action, data=None):
        if data is None:
            data = {}
        
        if not self.websocket:
            if not await self.connect():
                return {"status": "error", "message": "Failed to connect to server"}
        
        try:
            request = {"action": action, **data}
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            # Використовуємо json_util для десеріалізації
            return json_util.loads(response)
        except websockets.exceptions.ConnectionClosed:
            return {"status": "error", "message": "Connection to server lost"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def login(self, email, password):
        response = await self.send_request("login", {
            "email": email,
            "password": password
        })
        if response["status"] == "success":
            self.current_user = response["user"]
        return response
    
    async def register(self, username, email, password):
        return await self.send_request("register", {
            "username": username,
            "email": email,
            "password": password
        })
    
    async def create_note(self, title, content, note_type="text", encrypt=False):
        if not self.current_user:
            return {"status": "error", "message": "You need to login first"}
        
        return await self.send_request("create_note", {
            "user_id": self.current_user["id"],
            "title": title,
            "content": content,
            "note_type": note_type,
            "encrypt": encrypt
        })
    
    async def get_notes(self):
        if not self.current_user:
            return {"status": "error", "message": "You need to login first"}
        
        return await self.send_request("get_notes", {
            "user_id": self.current_user["id"]
        })
    
    async def close(self):
        if self.websocket:
            await self.websocket.close()

class ConsoleInterface:
    def __init__(self):
        self.client = NoteClient()
    
    async def run(self):
        connected = await self.client.connect()
        if not connected:
            print("Failed to connect to server. Please start the server first.")
            return
        
        while True:
            print("\n1. Login")
            print("2. Register")
            print("3. Create Note")
            print("4. View Notes")
            print("5. Exit")
            
            choice = input("Select an option: ")
            
            try:
                if choice == "1":
                    await self.handle_login()
                elif choice == "2":
                    await self.handle_register()
                elif choice == "3":
                    await self.handle_create_note()
                elif choice == "4":
                    await self.handle_view_notes()
                elif choice == "5":
                    await self.client.close()
                    break
                else:
                    print("Invalid option")
            except Exception as e:
                print(f"Error: {e}")
    
    async def handle_login(self):
        email = input("Email: ")
        password = input("Password: ")
        response = await self.client.login(email, password)
        print(response["message"])
    
    async def handle_register(self):
        username = input("Username: ")
        email = input("Email: ")
        password = input("Password: ")
        response = await self.client.register(username, email, password)
        print(response["message"])
    
    async def handle_create_note(self):
        if not self.client.current_user:
            print("You need to login first")
            return
        
        title = input("Note title: ")
        content = input("Note content: ")
        print("Note types: 1. Text 2. Voice 3. Image")
        note_type_choice = input("Select note type (1-3): ")
        note_types = {1: "text", 2: "voice", 3: "image"}
        note_type = note_types.get(int(note_type_choice), "text")
        
        encrypt = input("Encrypt note? (y/n): ").lower() == "y"
        
        response = await self.client.create_note(title, content, note_type, encrypt)
        print(response["message"])
    
    async def handle_view_notes(self):
        if not self.client.current_user:
            print("You need to login first")
            return
        
        response = await self.client.get_notes()
        if response["status"] == "success":
            notes = response.get("notes", [])
            if not notes:
                print("No notes found")
                return
            
            print("\nYour Notes:")
            for idx, note in enumerate(notes, 1):
                print(f"{idx}. {note['title']} ({note['note_type']})")
            
            note_choice = input("Enter note number to view details or 0 to go back: ")
            if note_choice.isdigit() and 0 < int(note_choice) <= len(notes):
                selected_note = notes[int(note_choice)-1]
                print(f"\nTitle: {selected_note['title']}")
                print(f"Type: {selected_note['note_type']}")
                print(f"Created: {selected_note['time_creation']}")
                print(f"Updated: {selected_note.get('time_update', 'N/A')}")
                print(f"Encrypted: {'Yes' if selected_note.get('is_encrypted') else 'No'}")
                print(f"\nContent:\n{selected_note['content']}")
                input("\nPress Enter to continue...")
        else:
            print(response["message"])

if __name__ == "__main__":
    interface = ConsoleInterface()
    asyncio.get_event_loop().run_until_complete(interface.run())