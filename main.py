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
    conversation_id: str
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
    response = await client.chat.completions.create(
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

    return {
        "transcription": gpt_response,
        "audio": None
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






# Add samay raina voice either through play.ht or eleven labs.
# Add intro music.
# Have some flashy CSS.
# Add limit to 15 questions.
# Add rules:
#   1. You have 15 questions to defeat gpt.
#   2. You loose if you dont ask a question or if you cannot get an answer in 15 questions.
# Deploy this.