const chatMessages = document.querySelector('.chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');

// Store WebSocket connections
let chatSocket = null;
let gameSocket = null;

window.addEventListener('beforeunload', function (event) {
    if (chatSocket) chatSocket.close();
    if (gameSocket) gameSocket.close();
    sessionStorage.clear();
});

document.getElementById('play-audio-button').addEventListener('click', function() {
    const audio = document.getElementById('intro-music');
    if (audio.paused) {
        audio.play();
    } else {
        audio.pause();
    }
});

// Create game event handler
document.getElementById('create-game-button').addEventListener('click', async () => {
    let playerName = '';
    while (!playerName) {
        playerName = prompt("Enter your name:");
        if (!playerName) {
            alert("Player name cannot be empty. Please enter your name.");
            break;
        }
    }
    if (!playerName) {
        return;
    }
    // Generate a random alphanumeric uppercase room ID
    const roomId = Math.random().toString(36).substring(2, 8).toUpperCase().replace(/[^A-Z0-9]/g, '');
    sessionStorage.setItem('room_id', roomId);
    sessionStorage.setItem('player_name', playerName);

    // Display room name and player name
    document.getElementById('room-name-display').textContent = `Room ID: ${roomId}`;
    document.getElementById('player-name-display').textContent = `Player Name: ${playerName}`;

    // Play intro music
    const audio = document.getElementById('intro-music');
    if (audio.paused) {
        audio.play();
    }

    // Initialize WebSocket connections
    initializeWebSockets(roomId, playerName);
    
    // Send create game event
    gameSocket.addEventListener('open', () => {
        gameSocket.send(JSON.stringify({
            type: 'create_game'
        }));
    });

    document.getElementById('game-dialog').style.display = 'none';
    document.getElementById('game-interface').style.display = 'block';
    document.getElementById('start-game-button').style.display = 'block';
    document.getElementById('question-list').style.display = 'block';
    
    // Show the room ID to share
    alert(`Game created! Your room code is: ${roomId}`);
});

// Join game event handler
document.getElementById('join-game-button').addEventListener('click', async () => {
    const roomId = document.getElementById('join-game-code').value.trim();
    if (!roomId) {
        alert('Please enter a room code.');
        return;
    }

    let playerName = '';
    while (!playerName) {
        playerName = prompt("Enter your name:");
        if (!playerName) {
            alert("Player name cannot be empty. Please enter your name.");
            break;
        }
    }
    if (!playerName) {
        return;
    }
    sessionStorage.setItem('room_id', roomId);
    sessionStorage.setItem('player_name', playerName);

    // Display room name and player name
    document.getElementById('room-name-display').textContent = `Room ID: ${roomId}`;
    document.getElementById('player-name-display').textContent = `Player Name: ${playerName}`;

    // Play intro music
    const audio = document.getElementById('intro-music');
    if (audio.paused) {
        audio.play();
    }

    // Initialize WebSocket connections
    initializeWebSockets(roomId, playerName);

    // Send join game event
    gameSocket.addEventListener('open', () => {
        gameSocket.send(JSON.stringify({
            type: 'join_game'
        }));
    });

    document.getElementById('game-dialog').style.display = 'none';
    document.getElementById('game-interface').style.display = 'block';
});

// Start game event handler
document.getElementById('start-game-button').addEventListener('click', () => {
    const roomId = sessionStorage.getItem('room_id');
    if (!roomId) {
        alert('Room code is missing. Please join a game first.');
        return;
    }

    gameSocket.send(JSON.stringify({
        type: 'start_game'
    }));
    document.getElementById('start-game-button').style.display = 'none';
});

// Chat event handlers
sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

function sendMessage() {
    const message = chatInput.value.trim();
    const gameStatus = sessionStorage.getItem('game_status'); 
    if (gameStatus !== "started") {
        alert('The game has not started yet. Please wait for the game to start.');
        return;
    }
    const currentPlayer = sessionStorage.getItem('current_player');
    const playerName = sessionStorage.getItem('player_name');
    if (currentPlayer !== playerName) {
        alert('Wait for your turn.');
        return;
    }
    
    if (message && chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(message);
        chatInput.value = '';
    }
}

function initializeWebSockets(roomId, playerName) {
    // Initialize chat WebSocket
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsBase = window.location.hostname + (window.location.port ? ':' + window.location.port : '');
    
    chatSocket = new WebSocket(`${wsProtocol}//${wsBase}/ws/chat/${roomId}/${playerName}`);
    gameSocket = new WebSocket(`${wsProtocol}//${wsBase}/ws/game/${roomId}/${playerName}`);

    // Chat WebSocket event handlers
    chatSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        addMessageToChat(data.message, data.sender, data.audio);
    };

    chatSocket.onerror = (error) => {
        console.error('Chat WebSocket error:', error);
        addMessageToChat('Error: Could not connect to chat server', 'system');
    };

    // Game WebSocket event handlers
    gameSocket.onmessage = (event) => {
        const gameData = JSON.parse(event.data);
        if (gameData.type === 'alert') {
            alert(gameData.message);
        }
        else {
            sessionStorage.setItem('game_status', gameData.data.game_status);
            sessionStorage.setItem('current_player', gameData.data.current_player);
            updateGameDataUI(gameData);
        }
    };

    gameSocket.onerror = (error) => {
        console.error('Game WebSocket error:', error);
        addMessageToChat('Error: Could not connect to game server', 'system');
    };
}

function addMessageToChat(message, sender, audioBase64 = null) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message', sender);
    messageElement.textContent = `${sender}: ${message}`;
    chatMessages.appendChild(messageElement);

    if (audioBase64) {
        const audioElement = document.createElement('audio');
        audioElement.controls = true;
        audioElement.src = `data:audio/mp3;base64,${audioBase64}`;
        chatMessages.appendChild(audioElement);
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateGameDataUI(gameData) {
    const gameDataElement = document.getElementById('game-data');
    gameDataElement.textContent = JSON.stringify(gameData, null, 2);
}

// Initialize question suggestions
document.addEventListener('DOMContentLoaded', () => {
    const questions = [
        "What's your favorite color?",
        "How do you spend your weekends?",
        "Have you ever traveled abroad?",
        "What's your favorite movie genre?",
        "Do you enjoy reading books?",
        "What's your favorite cuisine?",
        "Have you ever tried skydiving?",
        "What's your dream job?",
        "Do you like playing video games?",
        "What's your favorite season?"
    ];

    // Shuffle the questions array
    questions.sort(() => Math.random() - 0.5);

    const questionList = document.getElementById('question-list');
    questions.forEach(question => {
        const questionItem = document.createElement('div');
        questionItem.className = 'question-item';
        questionItem.textContent = question;
        questionItem.addEventListener('click', () => {
            if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
                chatInput.value = question; // Add the question to the message box
                questionList.style.display = 'none';
            }
        });
        questionList.appendChild(questionItem);
    });
});