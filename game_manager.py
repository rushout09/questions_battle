from enum import Enum
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import asyncio
import aioredis
from typing import Dict, Set, Optional, Tuple

class GameStatus(Enum):
    CREATED = "created"
    STARTED = "started"
    FINISHED = "finished"

class PlayerStatus(Enum):
    PLAYING = "playing"
    LOST = "lost"

class GameManager:
    def __init__(self):
        self.redis = aioredis.from_url("redis://localhost", decode_responses=True)
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.active_timers: Dict[str, asyncio.Task] = {}

    async def create_game(self, room_id: str, player_name: str):
        game_data = {
            "players": [player_name],
            "current_turn": 0,
            "admin": player_name,
            "game_status": GameStatus.CREATED.value,
            "player_status": [PlayerStatus.PLAYING.value],
            "timer": 10,
            "current_player": player_name,
            "waiting_for_ai": False  # True when waiting for player to ask question
        }
        await self.redis.set(f"game:{room_id}", json.dumps(game_data))
        await self.broadcast_game_update(room_id)
        return game_data

    async def join_game(self, room_id: str, player_name: str) -> bool:
        game_data = await self.get_game_data(room_id)
        if not game_data or game_data["game_status"] != GameStatus.CREATED.value:
            return False
            
        if player_name in game_data["players"]:
            return False
            
        game_data["players"].append(player_name)
        game_data["player_status"].append(PlayerStatus.PLAYING.value)
        await self.redis.set(f"game:{room_id}", json.dumps(game_data))
        await self.broadcast_game_update(room_id)
        return True

    async def start_game(self, room_id: str, player_name: str) -> str:
        game_data = await self.get_game_data(room_id)
        if not game_data or game_data["admin"] != player_name:
            return "Only Admin can start the game"
            
        if len(game_data["players"]) < 2:
            return "Min 2 players required to start the game"
            
        game_data["game_status"] = GameStatus.STARTED.value
        game_data["current_player"] = game_data["players"][0]
        game_data["timer"] = 10
        game_data["waiting_for_ai"] = False
        
        await self.redis.set(f"game:{room_id}", json.dumps(game_data))
        await self.broadcast_game_update(room_id)
        await self.start_turn_timer(room_id)
        return  "Game Started"

    async def start_turn_timer(self, room_id: str):
        # Cancel existing timer if any
        if room_id in self.active_timers:
            self.active_timers[room_id].cancel()
        
        self.active_timers[room_id] = asyncio.create_task(self.timer_countdown(room_id))

    async def timer_countdown(self, room_id: str):
        try:
            game_data = await self.get_game_data(room_id)
            remaining_time = game_data["timer"]

            while remaining_time > -1:
                game_data["timer"] = remaining_time
                await self.redis.set(f"game:{room_id}", json.dumps(game_data))
                await self.broadcast_game_update(room_id)
                await asyncio.sleep(1)
                remaining_time -= 1
                
                # Recheck game data each iteration in case of updates
                game_data = await self.get_game_data(room_id)
                if game_data["game_status"] != GameStatus.STARTED.value:
                    return

            # Time's up - player loses
            await self.handle_player_timeout(room_id)
            
        except asyncio.CancelledError:
            # Timer was cancelled (e.g., player asked question in time)
            pass

    async def handle_player_timeout(self, room_id: str):
        game_data = await self.get_game_data(room_id)
        current_player_index = game_data["current_turn"]
        
        # Mark current player as lost
        game_data["player_status"][current_player_index] = PlayerStatus.LOST.value
        
        # Check if game is over
        playing_players = [i for i, status in enumerate(game_data["player_status"]) 
                         if status == PlayerStatus.PLAYING.value]
        
        if len(playing_players) == 1:
            # Game over - we have a winner
            game_data["game_status"] = GameStatus.FINISHED.value
            game_data["winner"] = game_data["players"][playing_players[0]]
            await self.redis.set(f"game:{room_id}", json.dumps(game_data))
            await self.broadcast_game_update(room_id)
        else:
            await self.redis.set(f"game:{room_id}", json.dumps(game_data))
            await self.broadcast_game_update(room_id)
            # Move to next player
            await self.next_turn(room_id)
        

    async def handle_user_message(self, room_id: str, player_name: str) -> bool:
        """Called when a player asks a question (from chat manager)"""
        game_data = await self.get_game_data(room_id)
        
        if (game_data["game_status"] != GameStatus.STARTED.value or 
            game_data["current_player"] != player_name or game_data["waiting_for_ai"]):
            return False

        # Cancel the timer since player asked in time
        if room_id in self.active_timers:
            self.active_timers[room_id].cancel()

        game_data["waiting_for_ai"] = True
        await self.redis.set(f"game:{room_id}", json.dumps(game_data))
        await self.broadcast_game_update(room_id)
        return True

    async def handle_ai_message(self, room_id: str, player_lost: bool):
        """Called when AI has replied (from chat manager)"""
        game_data = await self.get_game_data(room_id)
        if game_data["game_status"] != GameStatus.STARTED.value:
            return False
        
        game_data["waiting_for_ai"] = False
        if player_lost:
            current_player_index = game_data["current_turn"]
            # Mark current player as lost
            game_data["player_status"][current_player_index] = PlayerStatus.LOST.value

        # Check if game is over
        playing_players = [i for i, status in enumerate(game_data["player_status"]) 
                         if status == PlayerStatus.PLAYING.value]
        
        if len(playing_players) == 1:
            # Game over - we have a winner
            game_data["game_status"] = GameStatus.FINISHED.value
            game_data["winner"] = game_data["players"][playing_players[0]]
            await self.redis.set(f"game:{room_id}", json.dumps(game_data))
            await self.broadcast_game_update(room_id)
        else:
            await self.redis.set(f"game:{room_id}", json.dumps(game_data))
            await self.broadcast_game_update(room_id)
            # Move to next player
            await self.next_turn(room_id)

    async def next_turn(self, room_id: str):
        print("inside next turn")
        game_data = await self.get_game_data(room_id)
        print(game_data)
        current_player_index = game_data["current_turn"]
        print(current_player_index)

        next_index = (current_player_index + 1) % len(game_data["players"])
        while game_data["player_status"][next_index] == PlayerStatus.LOST.value:
            next_index = (next_index + 1) % len(game_data["players"])

        print(next_index)
        
        game_data["current_turn"] = next_index
        game_data["current_player"] = game_data["players"][next_index]
        game_data["timer"] = 10  # Reset timer
        
        await self.redis.set(f"game:{room_id}", json.dumps(game_data))
        await self.broadcast_game_update(room_id)
        await self.start_turn_timer(room_id)

    async def get_game_data(self, room_id: str) -> Optional[Dict]:
        data = await self.redis.get(f"game:{room_id}")
        return json.loads(data) if data else None

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(websocket)
        
        # Send current game state to new connection
        game_data = await self.get_game_data(room_id)
        if game_data:
            await websocket.send_json({
                "type": "game_update",
                "data": game_data
            })

    async def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.rooms:
            self.rooms[room_id].remove(websocket)
            if len(self.rooms[room_id]) == 0:
                del self.rooms[room_id]

    async def broadcast_game_update(self, room_id: str):
        if room_id in self.rooms:
            game_data = await self.get_game_data(room_id)
            for connection in self.rooms[room_id]:
                await connection.send_json({
                    "type": "game_update",
                    "data": game_data
                })