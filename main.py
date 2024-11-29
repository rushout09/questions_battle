# Questions Battle Game - Comicstaan - https://www.youtube.com/watch?v=3umAFqj6EBg

# 2 player Game.
# Each person has to communicate to other person via questions only.
# We will create an Voice AI agent to play this game with AI

# Backend:  OpenAI GPT APIs - credits. - chat completions API / realtime voice API. FastAPI (async version of Flask) - Python library.
# Frontend: Basic Chat Interface with both text and voice option. 


# 8 Nov, 2024.
# Frontend make changes to add realtime voice.
# Backend changes to support real time voice.
# Backend improve prompt to play properly.
# Deploy: AWS EC2 - server 2gb.


# Text input -> Audio output Done.

# Audio input -> audio output

# Send entire list of messages to properly generate response instead of just last message.
# Also create common api for audio and text input

import os
import json
import base64
import random
import string
import aioredis
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import AsyncOpenAI
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from elevenlabs.client import AsyncElevenLabs
from elevenlabs import Voice, VoiceSettings
from enum import Enum

class GameStatus(Enum):
    CREATED = "Created"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"

class PlayerStatus(Enum):
    PLAYING = "Playing"
    FINISHED = "Finished"

load_dotenv()
app = FastAPI()
# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
eleven_client = AsyncElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
redis_client = aioredis.from_url("redis://localhost")

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

class ChatMessage(BaseModel):
    message: str
    game_code: str
    #audio: bool
    #audio_base64: str


async def game_stream(game_code: str):
    while True:
        # Get the game data from Redis
        game_data = await redis_client.get(f"game:{game_code}")
        if game_data:
            game_data = json.loads(game_data)
            # Check if there is no lock before modifying the game data
            if game_data.get("game_status") is GameStatus.IN_PROGRESS.value:
                if game_data["timer"] > 0:
                    game_data["timer"] -= 1
                else:
                    # Change the status of the current player to finished if they run out of time
                    game_data["player_status"][game_data["current_turn"]] = PlayerStatus.FINISHED.value

                    # Check if only one player is left playing
                    if game_data["player_status"].count(PlayerStatus.PLAYING.value) == 1:
                        winner_index = game_data["player_status"].index(PlayerStatus.PLAYING.value)
                        game_data["winner"] = game_data["players"][winner_index]
                        game_data["game_status"] = GameStatus.COMPLETED.value
                    else:
                        # Find the next player who is still playing
                        player_count = len(game_data["players"])
                        next_turn = (game_data["current_turn"] + 1) % player_count
                        while game_data["player_status"][next_turn] == PlayerStatus.FINISHED.value:
                            next_turn = (next_turn + 1) % player_count
                        game_data["current_turn"] = next_turn
                        game_data["timer"] = 30  # Reset timer for the next turn

                await redis_client.set(f"game:{game_code}", json.dumps(game_data))
        else:
            game_data = {"error": "Game not found"}
        
        yield f"data: {json.dumps(game_data)}\n\n"
        await asyncio.sleep(1)

@app.get("/sse/game/{game_code}")
async def sse_game_endpoint(game_code: str):
    return StreamingResponse(game_stream(game_code), media_type="text/event-stream")

async def generate_game_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

class CreateGameRequest(BaseModel):
    player_name: str

@app.post('/api/create-game')
async def create_game(request: CreateGameRequest):
    while True:
        game_code = await generate_game_code()
        existing_game = await redis_client.get(f"game:{game_code}")
        if not existing_game:
            break

    game_data = {
        "players": [request.player_name],
        "current_turn": 0,
        "admin": request.player_name,
        "game_status": GameStatus.CREATED.value,
        "player_status": [PlayerStatus.PLAYING.value],
        "timer": 30,
    }
    await redis_client.set(f"game:{game_code}", json.dumps(game_data))
    return {"game_code": game_code}

class JoinGameRequest(BaseModel):
    player_name: str
    game_code: str

@app.post('/api/join-game')
async def join_game(request: JoinGameRequest):
    game_data = await redis_client.get(f"game:{request.game_code}")
    if not game_data:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game_data = json.loads(game_data)
    
    if game_data["game_status"] != GameStatus.CREATED.value:
        raise HTTPException(status_code=400, detail="Cannot join game. Game is not in 'Created' status.")
    
    if len(game_data["players"]) >= 5:
        raise HTTPException(status_code=400, detail="Game is full")
    
    game_data["players"].append(request.player_name)
    game_data["player_status"].append(PlayerStatus.PLAYING.value)
    await redis_client.set(f"game:{request.game_code}", json.dumps(game_data))
    return {"message": f"{request.player_name} joined the game"}


class StartGameRequest(BaseModel):
    game_code: str

@app.post('/api/start-game')
async def start_game(request: StartGameRequest):
    print("start")
    game_key = f"game:{request.game_code}"
    game_data = await redis_client.get(game_key)
    print(game_data)
    
    if not game_data:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game_data = json.loads(game_data)
    
    if len(game_data.get("players", [])) < 2:
        raise HTTPException(status_code=400, detail="At least two players are required to start the game")
    
    # Mark the game status as started
    game_data["game_status"] = GameStatus.IN_PROGRESS.value
    await redis_client.set(f"game:{request.game_code}", json.dumps(game_data))
    return {"message": "Game started successfully"}

class EndGameRequest(BaseModel):
    game_code: str

@app.post('/api/end-game')
async def end_game(request: EndGameRequest):
    game_key = f"game:{request.game_code}"
    game_data = await redis_client.get(game_key)
    
    if not game_data:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game_data = json.loads(game_data)
    
    # if game_data["game_status"] != GameStatus.IN_PROGRESS.value:
    #     raise HTTPException(status_code=400, detail="Cannot end game. Game is not in 'In Progress' status.")
    
    # Mark the game status as completed
    game_data["game_status"] = GameStatus.COMPLETED.value
    await redis_client.set(f"game:{request.game_code}", json.dumps(game_data))
    return {"message": "Game ended successfully"}


@app.get("/sse/chat/{game_code}")
async def sse_chat_endpoint(game_code: str):
    async def chat_stream(game_code: str):
        last_message_index = -1
        while True:
            conversation_key = f"conversation:{game_code}"
            conversation_data = await redis_client.get(conversation_key)
            
            if conversation_data:
                messages = json.loads(conversation_data)
                if len(messages) > last_message_index + 1:
                    last_message_index = len(messages) - 1
                    last_message = messages[last_message_index]
                    yield f"data: {json.dumps(last_message)}\n\n"
            
            await asyncio.sleep(1)

    return StreamingResponse(chat_stream(game_code), media_type="text/event-stream")


class ResponseFormat(BaseModel):
    question: str
    is_statement: bool



@app.post('/api/chat')
async def handle_chat(chat_message: ChatMessage):

    # Take a lock on the game to prevent concurrent modifications
    game_key = f"game:{chat_message.game_code}"
    game_data = await redis_client.get(game_key)
    
    if not game_data:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game_data = json.loads(game_data)

    # Retrieve previous messages from Redis
    conversation_key = f"conversation:{chat_message.game_code}"
    conversation_data = await redis_client.get(conversation_key)
    
    if conversation_data:
        messages = json.loads(conversation_data)
    else:
        messages = [{"role": "system", "content": prompt}]

    # Add the current user message to the messages list
    messages.append({"role": "user", "content": chat_message.message, "name": game_data["players"][game_data["current_turn"]]})

    # Process the chat message and generate a response
    response = await openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=messages,
        response_format=ResponseFormat
    )
    gpt_response = response.choices[0].message.parsed.question
    is_statement = response.choices[0].message.parsed.is_statement

    if is_statement:
        game_data["player_status"][current_turn] = PlayerStatus.FINISHED.value
    
    print(response)
    print(gpt_response)

    audio_chunks = []
    async for chunk in await eleven_client.generate(
        text=gpt_response,
        voice=Voice(
            voice_id='84cO64I8bJTfJxsMe9py',
            settings=VoiceSettings(stability=0.71, similarity_boost=0.5, style=0.5, use_speaker_boost=True),
        ),
        model="eleven_multilingual_v2"):

        audio_chunks.append(chunk)

    # Combine all audio chunks into a single bytes object
    audio_data = b''.join(audio_chunks)

    # Convert the audio data to a base64-encoded string
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        # Append the assistant's response to the messages list
    messages.append({"role": "assistant", "content": gpt_response, "audio": audio_base64})

    # Store the updated conversation in Redis
    await redis_client.set(conversation_key, json.dumps(messages))

    # Increment the current player to the next player who is not finished
    current_turn = game_data["current_turn"]
    total_players = len(game_data["players"])
    finished_players = game_data.get("finished_players", [])

    # Find the next player who is not finished
    next_turn = (current_turn + 1) % total_players
    while next_turn in finished_players:
        next_turn = (next_turn + 1) % total_players

    game_data["current_turn"] = next_turn

    # Set the updated game data back to Redis
    await redis_client.set(game_key, json.dumps(game_data))


    return {
        "transcription": gpt_response,
        "audio": audio_base64
    }

# HTML file endpoint
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

# HTML file endpoint
@app.get("/health-check")
async def health_check():
    return {"status": "healthy", "message": "Service is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





"""
Let's make this game multiplayer. One should be able to create a game and add up to 5 friends. 
Friends can join using a code to the same game. So it will be 5 friends against AI. 
Each friend will get a chance to ask a question. Whoever is able to survive till last will win the game.
"""


"""
1. User lands on the main page -> enters his name.
2. User can start a game or join a game.
3. If user starts a game: he gets a game code which he should be able to copy and share with other frinds via whatsapp.
4. if user joins a game: he enters a game code and clicks join.
5. users should be able to see other players joining the game in the lobby.
6. admin can click on start game to start the game after min two players are present.
7. admin is the first to send a messsage. next player can send the message next. other player should not be allowed to send message.
8. 

"""