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
import base64
import json
from pathlib import Path
from openai import AsyncOpenAI
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from elevenlabs.client import AsyncElevenLabs
from elevenlabs import Voice, VoiceSettings
import random
import string

load_dotenv()

app = FastAPI()
# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

games = {}

# Set up OpenAI client
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
eleven_client = AsyncElevenLabs(
  api_key=os.getenv("ELEVEN_API_KEY"), # Defaults to ELEVEN_API_KEY
)

class ChatMessage(BaseModel):
    message: str
    conversation_id: str
    #audio: bool
    #audio_base64: str

def generate_game_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.post('/api/create-game')
async def create_game():
    game_code = generate_game_code()
    games[game_code] = {
        "players": [],
        "current_turn": 0,
        "messages": []
    }
    return {"game_code": game_code}


@app.post('/api/join-game')
async def join_game(game_code: str, player_name: str):
    if game_code not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if len(games[game_code]["players"]) >= 5:
        raise HTTPException(status_code=400, detail="Game is full")
    
    games[game_code]["players"].append(player_name)
    return {"message": f"{player_name} joined the game"}


@app.post('/api/chat')
async def handle_chat(request: Request, chat_message: ChatMessage):
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

    # Define the file path based on conversation_id
    conversation_file = Path(f"conversation_{chat_message.conversation_id}.jsonl")

    # Check if the conversation file exists and load previous messages
    if conversation_file.exists():
        messages = []
        with conversation_file.open("r") as file:
            for line in file:
                messages.append(json.loads(line))
    else:
        messages = [{"role": "system", "content": prompt}]

    # Add the current user message to the messages list
    messages.append({"role": "user", "content": chat_message.message})

    # Process the chat message and generate a response
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    gpt_response = response.choices[0].message.content

    # Append the assistant's response to the messages list
    messages.append({"role": "assistant", "content": gpt_response})

    # Rewrite the conversation file with the updated messages
    with conversation_file.open("w") as file:
        for message in messages:
            file.write(json.dumps(message) + "\n")
    
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
    
    # Store the audio data as an audio file
    audio_file_path = "output_audio.mp3"
    with open(audio_file_path, "wb") as audio_file:
        audio_file.write(audio_data)
    
    print(f"Audio file saved at: {audio_file_path}")

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
