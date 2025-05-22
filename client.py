import asyncio
import websockets
import json
import uuid
from datetime import datetime
from bson import json_util
from config import Config

class NoteClient:
    def __init__(self):
        self.websocket = None
        self.current_user = None
        self.client_id = str(uuid.uuid4())
        self.uri = f"ws://{Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_PORT}"
        self._active = True
        self._connection_task = None
        self._connection_lock = asyncio.Lock()

    async def _connect(self):
        async with self._connection_lock:
            try:
                print(f"Connecting to {self.uri}...")
                self.websocket = await websockets.connect(
                    self.uri,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=1
                )
                
                init_data = {
                    "client_id": self.client_id,
                    "action": "init"
                }
                if self.current_user:
                    init_data["action"] = "restore_session"
                    init_data["user_id"] = self.current_user["id"]
                
                await self.websocket.send(json.dumps(init_data))
                response = json_util.loads(await self.websocket.recv())
                
                if response.get("status") != "connected":
                    raise ConnectionError("Connection not acknowledged")
                
                print("Connection established successfully")
                return True
                
            except Exception as e:
                print(f"Connection failed: {str(e)}")
                if self.websocket:
                    await self.websocket.close()
                    self.websocket = None
                return False

    def _is_connected(self):
        try:
            return self.websocket is not None and not self.websocket.closed
        except:
            return False

    async def _connection_manager(self):
        while self._active:
            try:
                if not self._is_connected():
                    if not await self._connect():
                        await asyncio.sleep(Config.RECONNECT_DELAY)
                        continue
                
                await asyncio.sleep(Config.PING_INTERVAL)
                if self._is_connected():
                    try:
                        await self.websocket.ping()
                    except:
                        print("Connection check failed, reconnecting...")
                        await self._connect()

            except Exception as e:
                print(f"Connection manager error: {str(e)}")
                await asyncio.sleep(1)

    async def send_request(self, action, data=None):
        if data is None:
            data = {}

        if not self._is_connected():
            if not await self._connect():
                return {"status": "error", "message": "Could not connect to server"}

        try:
            request = {
                "action": action,
                "request_id": str(uuid.uuid4()),
                **data
            }
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            return json_util.loads(response)
            
        except websockets.exceptions.ConnectionClosed:
            print("Connection lost, reconnecting...")
            if await self._connect():
                return await self.send_request(action, data)
            return {"status": "error", "message": "Connection lost"}
        except Exception as e:
            print(f"Request failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def start(self):
        if not await self._connect():
            return False
        
        self._connection_task = asyncio.create_task(self._connection_manager())
        return True

    async def stop(self):
        self._active = False
        if self._connection_task:
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass

        if self.websocket is not None:
            try:
                await self.websocket.close()
            except:
                pass
            finally:
                self.websocket = None

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

    async def update_note(self, note_id, title=None, content=None, encrypt=None):
        if not self.current_user:
            return {"status": "error", "message": "You need to login first"}
        
        update_data = {}
        if title: update_data["title"] = title
        if content: update_data["content"] = content
        if encrypt is not None: update_data["encrypt"] = encrypt
        
        return await self.send_request("update_note", {
            "user_id": self.current_user["id"],
            "note_id": note_id,
            "update_data": update_data
        })

    async def delete_note(self, note_id):
        if not self.current_user:
            return {"status": "error", "message": "You need to login first"}
        
        return await self.send_request("delete_note", {
            "user_id": self.current_user["id"],
            "note_id": note_id
        })

    async def search_notes(self, query):
        if not self.current_user:
            return {"status": "error", "message": "You need to login first"}
        
        return await self.send_request("search_notes", {
            "user_id": self.current_user["id"],
            "query": query
        })

    async def logout(self):
        if not self.current_user:
            return {"status": "error", "message": "Not logged in"}
        
        response = await self.send_request("logout", {
            "user_id": self.current_user["id"]
        })
        
        if response["status"] == "success":
            self.current_user = None
        
        return response

class ConsoleInterface:
    def __init__(self):
        self.client = NoteClient()
        self._running = False

    async def run(self):
        if not await self.client.start():
            print("\nFailed to connect to server. Please check:")
            print(f"1. Сервер запущений на {Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_PORT}")
            print("2. Фаєрвол не блокує з'єднання")
            print("3. MongoDB запущений (команда 'mongod')")
            return

        self._running = True
        while self._running:
            try:
                print("\n1. Login")
                print("2. Register")
                print("3. Create Note")
                print("4. View Notes")
                print("5. Update Note")
                print("6. Delete Note")
                print("7. Search Notes")
                print("8. Logout")
                print("9. Exit")
                
                choice = input("Select an option: ").strip()
                
                if choice == "1":
                    await self.handle_login()
                elif choice == "2":
                    await self.handle_register()
                elif choice == "3":
                    await self.handle_create_note()
                elif choice == "4":
                    await self.handle_view_notes()
                elif choice == "5":
                    await self.handle_update_note()
                elif choice == "6":
                    await self.handle_delete_note()
                elif choice == "7":
                    await self.handle_search_notes()
                elif choice == "8":
                    await self.handle_logout()
                elif choice == "9":
                    self._running = False
                else:
                    print("Invalid option")
            except KeyboardInterrupt:
                print("\nExiting...")
                self._running = False
            except Exception as e:
                print(f"Error: {str(e)}")
        
        await self.client.stop()

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

    async def handle_update_note(self):
        if not self.client.current_user:
            print("You need to login first")
            return
        
        response = await self.client.get_notes()
        if response["status"] != "success":
            print(response["message"])
            return
        
        notes = response.get("notes", [])
        if not notes:
            print("No notes found")
            return
        
        print("\nYour Notes:")
        for idx, note in enumerate(notes, 1):
            print(f"{idx}. {note['title']} ({note['note_type']})")
        
        note_choice = input("Enter note number to update or 0 to go back: ")
        if note_choice.isdigit() and 0 < int(note_choice) <= len(notes):
            selected_note = notes[int(note_choice)-1]
            
            title = input(f"New title ({selected_note['title']}): ").strip()
            content = input(f"New content ({selected_note['content'][:20]}...): ").strip()
            encrypt = input(f"Encrypt note? (y/n, current: {'Yes' if selected_note.get('is_encrypted') else 'No'}): ").lower().strip()
            
            update_data = {}
            if title: update_data["title"] = title
            if content: update_data["content"] = content
            if encrypt: update_data["encrypt"] = encrypt == "y"
            
            response = await self.client.update_note(selected_note["_id"], **update_data)
            print(response["message"])

    async def handle_delete_note(self):
        if not self.client.current_user:
            print("You need to login first")
            return
        
        response = await self.client.get_notes()
        if response["status"] != "success":
            print(response["message"])
            return
        
        notes = response.get("notes", [])
        if not notes:
            print("No notes found")
            return
        
        print("\nYour Notes:")
        for idx, note in enumerate(notes, 1):
            print(f"{idx}. {note['title']} ({note['note_type']})")
        
        note_choice = input("Enter note number to delete or 0 to go back: ")
        if note_choice.isdigit() and 0 < int(note_choice) <= len(notes):
            confirm = input(f"Are you sure you want to delete '{notes[int(note_choice)-1]['title']}'? (y/n): ")
            if confirm.lower() == "y":
                response = await self.client.delete_note(notes[int(note_choice)-1]["_id"])
                print(response["message"])

    async def handle_search_notes(self):
        if not self.client.current_user:
            print("You need to login first")
            return
        
        query = input("Enter search query: ")
        response = await self.client.search_notes(query)
        
        if response["status"] == "success":
            notes = response.get("notes", [])
            if not notes:
                print("No matching notes found")
                return
            
            print("\nSearch Results:")
            for idx, note in enumerate(notes, 1):
                print(f"{idx}. {note['title']} ({note['note_type']})")
            
            note_choice = input("Enter note number to view or 0 to go back: ")
            if note_choice.isdigit() and 0 < int(note_choice) <= len(notes):
                selected_note = notes[int(note_choice)-1]
                print(f"\nTitle: {selected_note['title']}")
                print(f"Content:\n{selected_note['content']}")
                input("\nPress Enter to continue...")
        else:
            print(response["message"])

    async def handle_logout(self):
        response = await self.client.logout()
        print(response["message"])

if __name__ == "__main__":
    interface = ConsoleInterface()
    try:
        asyncio.get_event_loop().run_until_complete(interface.run())
    except KeyboardInterrupt:
        print("\nApplication terminated")
    except Exception as e:
        print(f"Fatal error: {str(e)}")