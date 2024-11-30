import json
from fastapi import WebSocket
from typing import Dict, Set, List, Optional
import aioredis

class ChatManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.message_storage = MessageStorage()
        
    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, room_id: str):
        self.rooms[room_id].remove(websocket)
        if len(self.rooms[room_id]) == 0:
            del self.rooms[room_id]
    
    async def broadcast_to_room(self, message: str, room_id: str, sender: str, audio: Optional[str] = None):
        if room_id in self.rooms:

            await self.message_storage.add_message(room_id, message, sender)

            message_data = {
                "message": message,
                "sender": sender,
                "room_id": room_id,
                "audio": audio
            }
            for connection in self.rooms[room_id]:
                await connection.send_json(message_data)

class MessageStorage:
    def __init__(self):
            self.redis = aioredis.from_url("redis://localhost", decode_responses=True)
    
    async def add_message(self, room_id: str, message: str, sender: str):
        message_data = {
            "role": "assistant" if sender == "assistant" else "user",
            "content": message,
            "name": sender
        }
        
        await self.redis.rpush(f"room:{room_id}:messages", json.dumps(message_data))
        # Optionally limit history size
        await self.redis.ltrim(f"room:{room_id}:messages", -50, -1)  # Keep last 50 messages
    
    async def get_messages(self, room_id: str) -> List[Dict]:
        messages_json = await self.redis.lrange(f"room:{room_id}:messages", 0, -1)
        return [json.loads(msg) for msg in messages_json]
    
    async def get_messages_for_openai(self, room_id: str) -> List[Dict]:
        messages = await self.get_messages(room_id)
        messages.insert(0, {"role": "system", "content": prompt})
        return messages


prompt = f"""
    You are Samay Raina, playing 'Questions Battle' with the user. Here's how it works:

The user will ask you a question or hello, and you must always respond with another question on the same topic.
The game ends when either you or the user responds with a statement (instead of a question).
If the user ends with a statement (and not a question) than always respond with <GAME OVER! YOU LOSE!!!>

Example:

User: Will you join us tomorrow?
Sam: At what time?

User: When are you free?
Sam: Would the evening work?

User: Let's meet at 7.
Sam: <GAME OVER! YOU LOSE!!!>


----------------THE GAME STARTS NOW--------------
    """
