import os
import base64
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import AsyncOpenAI
from chat_manager import ChatManager
from game_manager import GameManager
from elevenlabs.client import AsyncElevenLabs
from elevenlabs import Voice, VoiceSettings
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

load_dotenv()
app = FastAPI()
# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
eleven_client = AsyncElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

chat_manager = ChatManager()
game_manager = GameManager()


class ResponseFormat(BaseModel):
    question: str
    is_statement: bool


@app.websocket("/ws/chat/{room_id}/{player_name}")
async def chat_websocket(websocket: WebSocket, room_id: str, player_name: str):
    await chat_manager.connect(websocket, room_id)
    try:
        while True:
            message = await websocket.receive_text()
            # Broadcast the user message to all clients in the room
            await chat_manager.broadcast_to_room(message=message, room_id=room_id, sender=player_name)
            
            # Get AI response
            try:

                # Process the chat message and generate a response
                response = await openai_client.beta.chat.completions.parse(
                    model="gpt-4o",
                    messages=await chat_manager.message_storage.get_messages_for_openai(room_id=room_id),
                    response_format=ResponseFormat
                )
                ai_response = response.choices[0].message.parsed.question
                is_statement = response.choices[0].message.parsed.is_statement

                # if is_statement:
                #     game_data["player_status"][current_turn] = PlayerStatus.FINISHED.value
                
                print(response)
                print(ai_response)
                print(is_statement)

                audio_chunks = []
                async for chunk in await eleven_client.generate(
                    text=ai_response,
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
                await chat_manager.broadcast_to_room(message=ai_response, room_id=room_id, sender="assistant", audio=audio_base64)
                await game_manager.handle_ai_message(room_id, is_statement)
            except Exception as e:
                error_message = f"Error getting AI response: {str(e)}"
                await chat_manager.broadcast_to_room(message=error_message, room_id=room_id, sender="system")
                
    except WebSocketDisconnect:
        await chat_manager.disconnect(websocket, room_id)
        await chat_manager.broadcast_to_room(
            f"Player #{player_name} left the chat",
            room_id,
            "system"
        )


@app.websocket("/ws/game/{room_id}/{player_name}")
async def game_websocket(websocket: WebSocket, room_id: str, player_name: str):
    await game_manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "create_game":
                await game_manager.create_game(room_id, player_name)
            
            elif data["type"] == "join_game":
                await game_manager.join_game(room_id, player_name)
            
            elif data["type"] == "start_game":
                game_message = await game_manager.start_game(room_id, player_name)
                await websocket.send_json({
                    "type": "alert",
                    "message": game_message
                })
            
    except WebSocketDisconnect:
        await game_manager.disconnect(websocket, room_id)

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
