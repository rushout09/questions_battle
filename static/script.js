const chatMessages = document.querySelector('.chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');

window.addEventListener('beforeunload', function (event) {
    // Perform actions before the page is reloaded
    // You can show a confirmation dialog or save data here
    if (gameEventSource) gameEventSource.close();
    if (chatEventSource) chatEventSource.close();
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


document.getElementById('create-game-button').addEventListener('click', async () => {
    let playerName = '';
    while (!playerName) {
        playerName = prompt("Enter your name:");
        if (!playerName) {
            alert("Player name cannot be empty. Please enter your name.");
        }
    }
    const response = await fetch('/api/create-game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_name: playerName })
    });
    const data = await response.json();
    sessionStorage.setItem('game_code', data.game_code); // Store game_code in session storage
    alert(`Game created! Your game code is: ${data.game_code}`);
    document.getElementById('game-dialog').style.display = 'none';
    document.getElementById('game-interface').style.display = 'block'
    streamGameData(data.game_code); // Start streaming game data
    streamChatMessages(data.game_code);
});

document.getElementById('join-game-button').addEventListener('click', async () => {
    const game_code = document.getElementById('join-game-code').value.trim();
    if (!game_code) {
        alert('Please enter a game code.');
        return;
    }
    let playerName = '';
    while (!playerName) {
        playerName = prompt("Enter your name:");
        if (!playerName) {
            alert("Player name cannot be empty. Please enter your name.");
        }
    }
    const response = await fetch('/api/join-game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_code: game_code, player_name: playerName })
    });

    if (response.status === 404) {
        alert('Error: Game not found. Please check the game code and try again.');
        return;
    } else if (response.status === 400) {
        const errorData = await response.json();
        alert(`Error: ${errorData.detail}`);
        return;
    }

    const data = await response.json();
    sessionStorage.setItem('game_code', game_code); // Store game_code in session storage
    alert(data.message);
    document.getElementById('game-dialog').style.display = 'none';
    document.getElementById('game-interface').style.display = 'block'
    streamGameData(game_code); // Start streaming game data
    streamChatMessages(game_code);
});

// Add event listener to the "Start Game" button
document.getElementById('start-game-button').addEventListener('click', async () => {
    const game_code = sessionStorage.getItem('game_code');
    console.log(game_code);
    if (!game_code) {
        alert('Game code is missing. Please join a game first.');
        return;
    }
    try {
        const response = await fetch('/api/start-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_code: game_code })
        });

        if (response.status === 400) {
            const errorData = await response.json();
            alert(`Error: ${errorData.detail}`);
        } else {
            const data = await response.json();
            alert(data.message);
        }
    } catch (error) {
        console.error('Error starting game:', error);
        alert('An unexpected error occurred. Please try again later.');
    }
});


// Add event listener to the "End Game" button
document.getElementById('end-game-button').addEventListener('click', () => {
    const game_code = sessionStorage.getItem('game_code');
    if (!game_code) {
        alert('Game code is missing. Please join a game first.');
        return;
    }
    try {
        const response = fetch('/api/end-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_code: game_code })
        });

        if (response.status === 404) {
            alert('Error: Game not found.');
        } else {
            const data = response.json();
            alert(data.message);
        }
    } catch (error) {
        console.error('Error ending game:', error);
        alert('An unexpected error occurred. Please try again later.');
    }
    if (gameEventSource || chatEventSource) {
        
        if (gameEventSource) gameEventSource.close();
        if (chatEventSource) chatEventSource.close();
        sessionStorage.clear();

        alert('Game and chat streams have been closed.');
    } else {
        alert('No active game to end.');
    }
});


sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

async function sendMessage() {
    const message = chatInput.value.trim();
    if (message) {
        chatInput.value = '';
        await sendMessageToBackend(message);
    }
}

async function sendMessageToBackend(message) {
    try {
        // Check if the UUID is already stored in localStorage
        let game_code = sessionStorage.getItem('game_code');

        // If there is no game_code, do not proceed with sending the message
        if (!game_code) {
            console.error('No game code available. Cannot send message.');
            return;
        }
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message: message, 
                game_code: game_code 
            })
        });

        const data = await response.json();
        console.log(data);
    } catch (error) {
        console.error('Error sending message:', error);
    }
}


let chatEventSource;
function streamChatMessages(game_code) {
    chatEventSource = new EventSource(`/sse/chat/${game_code}`);
    chatEventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.error) {
            console.error(data.error);
        } else {
            addMessageToChat(data.content, data.role, data.audio);
        }
    };
}

function addMessageToChat(message, sender, audioBase64 = null) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message', sender);
    console.log(message);
    messageElement.textContent = message;
    chatMessages.insertAdjacentElement('beforeend', messageElement);
    if (audioBase64) {
        const audioElement = document.createElement('audio');
        audioElement.controls = true;
        audioElement.src = `data:audio/mp3;base64,${audioBase64}`;
        chatMessages.insertAdjacentElement('beforeend', audioElement);
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

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
        "What's your favorite season?",
        "Have you ever been to a concert?",
        "What's your favorite hobby?",
        "Do you enjoy cooking?",
        "What's your favorite animal?",
        "Have you ever gone camping?",
        "What's your favorite sport?",
        "Do you like watching TV shows?",
        "What's your favorite holiday destination?",
        "Have you ever learned a musical instrument?",
        "What's your favorite type of music?"
    ];

    // Shuffle the questions array
    questions.sort(() => Math.random() - 0.5);

    const questionList = document.getElementById('question-list');
    questions.forEach(question => {
        const questionItem = document.createElement('div');
        questionItem.className = 'question-item';
        questionItem.textContent = question;
        questionItem.addEventListener('click', () => {
            sendMessageToBackend(question);
            questionList.style.display = 'none'; // Hide the question list after the first question is asked
        });
        questionList.appendChild(questionItem);
    });
});



let gameEventSource;
// Function to stream game data
function streamGameData(game_code) {
    gameEventSource = new EventSource(`/sse/game/${game_code}`);
    gameEventSource.onmessage = function(event) {
        const gameData = JSON.parse(event.data);
        if (gameData.error) {
            console.error(gameData.error);
        } else {
            updateGameDataUI(gameData);
        }
    };
}
// Function to update the UI with game data
function updateGameDataUI(gameData) {
    const gameDataElement = document.getElementById('game-data');
    gameDataElement.textContent = JSON.stringify(gameData, null, 2);
}
