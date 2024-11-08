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
from openai import AsyncOpenAI
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatMessage(BaseModel):
    message: str
    #audio: bool
    #audio_base64: str

@app.post('/api/chat')
async def handle_chat(request: Request, chat_message: ChatMessage):
    prompt = f"""
    You are Sam, playing 'Questions Battle' with the user. Here's how it works:

The user will ask you a question, and you must always respond with another question on the same topic.
The game ends when either you or the user responds with a statement (instead of a question).
If the user ends with a statement (and not a question) than always respond with <GAME OVER! YOU LOSE!!!>

THE GAME IS ALREADY STARTED.

Example:

User: Will you join us tomorrow?
Sam: At what time?

User: When are you free?
Sam: Would the evening work?

User: Let's meet at 7.
Sam: <GAME OVER! YOU LOSE!!!>
    """
    
    # Process the chat message and generate a response
    response = await client.chat.completions.create(
        model="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        messages=[
            {"role": "system", "content": ""},
            {"role": "user", "content": prompt}
        ],
        audio={
            "voice": "alloy",
            "format": "mp3"
        }
    )

    print(f"Audio Transcription: {response.choices[0].message.audio.transcript}")
    print(f"Message Content: {response.choices[0].message.content}")
    audio_data = base64.b64decode(response.choices[0].message.audio.data)

    # Save the binary data to a file
    with open("output_audio.mp3", "wb") as audio_file:  # Change the extension to .wav if needed
        audio_file.write(audio_data)

    return {
        "transcription": response.choices[0].message.content if response.choices[0].message.content is not None else response.choices[0].message.audio.transcript,
        "audio": response.choices[0].message.audio.data
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






