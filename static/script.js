const chatMessages = document.querySelector('.chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');

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
        addMessageToChat(message, 'user');
        await sendMessageToBackend(message);
    }
}

async function sendMessageToBackend(message) {
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        const data = await response.json();
        console.log(data);
        addMessageToChat(data.transcription, 'assistant', data.audio);
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
