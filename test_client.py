import asyncio
import websockets
import json
import time

async def test_server():
    try:
        async with websockets.connect("ws://localhost:8765") as websocket:
            # Тест створення нотатки
            note_data = {
                "action": "create_note",
                "type": "text",
                "content": "Test note content",
                "owner": "test_user"
            }
            await websocket.send(json.dumps(note_data))
            response = await websocket.recv()
            print("Create note response:", response)

            # Тест отримання нотаток
            get_notes = {
                "action": "get_notes",
                "owner": "test_user"
            }
            await websocket.send(json.dumps(get_notes))
            response = await websocket.recv()
            print("Get notes response:", json.loads(response))

    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    while True:
        asyncio.get_event_loop().run_until_complete(test_server())
        time.sleep(2)