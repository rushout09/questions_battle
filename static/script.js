const chatMessages = document.querySelector('.chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');

sendButton.addEventListener('click', sendMessage);

window.addEventListener('beforeunload', function (event) {
    // Perform actions before the page is reloaded
    // You can show a confirmation dialog or save data here

    // The following line clears session storage.
    sessionStorage.clear();
});

chatInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

async function sendMessage() {
    const message = chatInput.value.trim();
    if (message) {
        chatInput.value = '';
        addMessageToChat(message, 'user');
        await sendMessageToBackend(message);
    }
}

async function sendMessageToBackend(message) {
    try {
        const typingIndicator = document.createElement('div');
        typingIndicator.classList.add('chat-message', 'assistant');
        typingIndicator.textContent = 'Typing...';
        chatMessages.insertAdjacentElement('beforeend', typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        // Check if the UUID is already stored in localStorage
        let conversationId = sessionStorage.getItem('conversationId');

        // If the UUID is not in localStorage, generate a new one and store it
        if (!conversationId) {
            conversationId = Math.random().toString(36).substring(2, 9);
            sessionStorage.setItem('conversationId', conversationId);
        }
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message: message, 
                conversation_id: conversationId 
            })
        });

        // Remove typing indicator
        typingIndicator.remove();
        const data = await response.json();
        console.log(data);
        addMessageToChat(data.transcription, 'assistant', data.audio                                                                                            );
    } catch (error) {
        console.error('Error sending message:', error);
    }
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
            addMessageToChat(question, 'user');
            sendMessageToBackend(question);
            questionList.style.display = 'none'; // Hide the question list after the first question is asked
        });
        questionList.appendChild(questionItem);
    });
});

document.getElementById('play-audio-button').addEventListener('click', function() {
    const audio = document.getElementById('intro-music');
    if (audio.paused) {
        audio.play();
    } else {
        audio.pause();
    }
});

const createGameButton = document.getElementById('create-game-button');
const joinGameButton = document.getElementById('join-game-button');
const joinGameCodeInput = document.getElementById('join-game-code');

createGameButton.addEventListener('click', async () => {
    const response = await fetch('/api/create-game', { method: 'POST' });
    const data = await response.json();
    alert(`Game created! Your game code is: ${data.game_code}`);
});

joinGameButton.addEventListener('click', async () => {
    const gameCode = joinGameCodeInput.value.trim();
    const playerName = prompt("Enter your name:");
    const response = await fetch('/api/join-game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_code: gameCode, player_name: playerName })
    });
    const data = await response.json();
    alert(data.message);
});