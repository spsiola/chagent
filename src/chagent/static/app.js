const chatContainer = document.getElementById('chat-container');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const statusDiv = document.getElementById('connection-status');
const statusText = statusDiv.querySelector('.status-text');

let ws = null;
let currentInfoElement = null;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);

    ws.onopen = () => {
        statusDiv.classList.add('connected');
        statusText.textContent = 'Connected';
    };

    ws.onclose = () => {
        statusDiv.classList.remove('connected');
        statusText.textContent = 'Disconnected';
        setTimeout(connectWebSocket, 3000); // Reconnect after 3s
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleAgentEvent(data);
    };
}

// Copy dialog functionality
const copyBtn = document.getElementById('copy-dialog-btn');
if (copyBtn) {
    copyBtn.addEventListener('click', () => {
        let log = "";
        const children = chatContainer.children;
        for (let child of children) {
            if (child.classList.contains('message') && child.classList.contains('user')) {
                log += `Пользователь: ${child.innerText.trim()}\n\n`;
            } else if (child.classList.contains('message') && child.classList.contains('ai')) {
                log += `Модель: ${child.innerText.trim()}\n\n`;
            } else if (child.classList.contains('tool-event')) {
                log += `Инструмент:\n${child.innerText.trim()}\n\n`;
            }
        }
        
        navigator.clipboard.writeText(log.trim()).then(() => {
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="#10b981" stroke-width="2" fill="none"><polyline points="20 6 9 17 4 12"></polyline></svg> Скопировано';
            setTimeout(() => { copyBtn.innerHTML = originalHTML; }, 2000);
        }).catch(err => {
            console.error('Copy failed', err);
            alert('Не удалось скопировать лог');
        });
    });
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeInfoElement() {
    if (currentInfoElement) {
        currentInfoElement.remove();
        currentInfoElement = null;
    }
}

function handleAgentEvent(event) {
    if (event.type === 'info') {
        removeInfoElement();
        const infoEl = document.createElement('div');
        infoEl.className = 'info-event';
        infoEl.textContent = event.content;
        chatContainer.appendChild(infoEl);
        currentInfoElement = infoEl;
        scrollToBottom();
    } 
    else if (event.type === 'message') {
        removeInfoElement();
        const msgEl = document.createElement('div');
        msgEl.className = 'message ai';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        // Basic markdown-like handling (newlines to br)
        let formatted = event.content.replace(/\n/g, '<br>');
        // Code block formatting
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre style="background:rgba(0,0,0,0.3);padding:10px;border-radius:8px;margin-top:8px;"><code>$1</code></pre>');
        
        bubble.innerHTML = formatted;
        msgEl.appendChild(bubble);
        chatContainer.appendChild(msgEl);
        scrollToBottom();
    }
    else if (event.type === 'tool_call') {
        removeInfoElement();
        const toolEl = document.createElement('div');
        toolEl.className = 'tool-event';
        
        let argsStr = '';
        try { argsStr = JSON.stringify(event.args, null, 2); } catch(e) { argsStr = event.args; }
        
        toolEl.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" style="flex-shrink:0"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
            <div style="flex:1">
                Вызов инструмента: <strong>${event.name}</strong>
                <pre>${argsStr}</pre>
            </div>
        `;
        chatContainer.appendChild(toolEl);
        scrollToBottom();
    }
    else if (event.type === 'finish') {
        removeInfoElement();
    }
    else if (event.type === 'error') {
        removeInfoElement();
        const infoEl = document.createElement('div');
        infoEl.className = 'info-event';
        infoEl.style.color = '#ef4444';
        infoEl.textContent = `Ошибка: ${event.content}`;
        chatContainer.appendChild(infoEl);
        scrollToBottom();
    }
}

chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text || ws.readyState !== WebSocket.OPEN) return;
    
    // Remove welcome message if present
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) welcomeMsg.remove();

    // Add user message to UI
    const msgEl = document.createElement('div');
    msgEl.className = 'message user';
    msgEl.innerHTML = `<div class="message-bubble">${text}</div>`;
    chatContainer.appendChild(msgEl);
    
    // Send to server
    ws.send(JSON.stringify({ text }));
    
    messageInput.value = '';
    scrollToBottom();
});

// Init
connectWebSocket();
