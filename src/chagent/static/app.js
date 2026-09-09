const chatContainer = document.getElementById('chat-container');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const statusDiv = document.getElementById('connection-status');
const modelSelect = document.getElementById('model-select');

let ws = null;
let currentInfoElement = null;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);

    ws.onopen = () => {
        statusDiv.classList.remove('testing');
        statusDiv.classList.add('connected');
        statusDiv.title = 'Connected';
        fetchModels();
    };

    ws.onclose = () => {
        statusDiv.classList.remove('connected');
        statusDiv.title = 'Disconnected';
        setTimeout(connectWebSocket, 3000); // Reconnect after 3s
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleAgentEvent(data);
    };
}

async function fetchModels() {
    try {
        const res = await fetch('/api/models');
        const data = await res.json();
        
        if (data.models && data.models.length > 0) {
            modelSelect.innerHTML = '';
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = JSON.stringify({ provider_name: m.provider, model_name: m.model });
                opt.textContent = `${m.provider}: ${m.model}`;
                if (data.current_model === m.model) {
                    opt.selected = true;
                }
                modelSelect.appendChild(opt);
            });
            modelSelect.style.display = 'inline-block';
        }
    } catch (e) {
        console.error("Failed to fetch models", e);
    }
}

if (modelSelect) {
    modelSelect.addEventListener('change', async (e) => {
        const val = JSON.parse(e.target.value);
        modelSelect.disabled = true;
        statusDiv.classList.remove('connected');
        statusDiv.classList.remove('error');
        statusDiv.classList.add('testing');
        statusDiv.title = 'Testing...';
        try {
            const res = await fetch('/api/models/switch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(val)
            });
            const data = await res.json();
            statusDiv.classList.remove('testing');
            if (!data.success) {
                statusDiv.classList.remove('connected');
                statusDiv.title = 'Model Error';
                messageInput.disabled = true;
                document.getElementById('send-button').disabled = true;
                document.getElementById('send-button').style.opacity = '0.5';
            } else {
                statusDiv.classList.add('connected');
                statusDiv.title = 'Connected';
                messageInput.disabled = false;
                document.getElementById('send-button').disabled = false;
                document.getElementById('send-button').style.opacity = '1';
            }
        } catch (err) {
            console.error(err);
            statusDiv.classList.remove('testing');
            statusDiv.classList.remove('connected');
            statusDiv.title = 'Model Error';
            messageInput.disabled = true;
            document.getElementById('send-button').disabled = true;
            document.getElementById('send-button').style.opacity = '0.5';
        } finally {
            modelSelect.disabled = false;
        }
    });
}

// Copy dialog functionality
const copyBtn = document.getElementById('copy-dialog-btn');
if (copyBtn) {
    copyBtn.addEventListener('click', () => {
        let log = "";
        const children = chatContainer.children;
        for (let child of children) {
            if (child.classList.contains('message') && child.classList.contains('user')) {
                log += `\nПользователь: ${child.innerText.trim()}\n\n`;
            } else if (child.classList.contains('message') && child.classList.contains('ai')) {
                const modelInfo = child.dataset.model ? ` [${child.dataset.model}]` : '';
                log += `Модель${modelInfo}: ${child.innerText.trim()}\n\n`;
            } else if (child.classList.contains('tool-event')) {
                log += `Инструмент:\n${child.innerText.trim()}\n\n`;
            } else if (child.classList.contains('harness-logs-container')) {
                const toggle = document.getElementById('toggle-harness-logs');
                if (toggle && toggle.checked) {
                    for (let logNode of child.children) {
                        if (logNode.classList.contains('harness-log')) {
                            log += `${logNode.innerText.trim()}\n`;
                        }
                    }
                }
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

const toggleHarnessLogs = document.getElementById('toggle-harness-logs');
if (toggleHarnessLogs) {
    toggleHarnessLogs.addEventListener('change', (e) => {
        if (e.target.checked) {
            chatContainer.classList.remove('hide-harness');
        } else {
            chatContainer.classList.add('hide-harness');
        }
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
        if (event.model && event.provider) {
            msgEl.dataset.model = `${event.provider}/${event.model}`;
        }
        
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
    else if (event.type === 'tool_result') {
        removeInfoElement();
        const resEl = document.createElement('div');
        resEl.className = 'tool-event tool-result';
        resEl.style.backgroundColor = 'rgba(16, 185, 129, 0.15)';
        resEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        resEl.style.color = '#10b981';
        
        resEl.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" style="flex-shrink:0"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
            <div style="flex:1; overflow-x: hidden;">
                Результат инструмента:
                <pre>${event.content}</pre>
            </div>
        `;
        chatContainer.appendChild(resEl);
        scrollToBottom();
    }
    else if (event.type === 'finish') {
        removeInfoElement();
    }
    else if (event.type === 'harness_log') {
        let container = chatContainer.lastElementChild;
        if (!container || !container.classList.contains('harness-logs-container')) {
            container = document.createElement('div');
            container.className = 'harness-logs-container';
            chatContainer.appendChild(container);
        }
        const logEl = document.createElement('div');
        logEl.className = 'harness-log';
        logEl.textContent = event.content;
        container.appendChild(logEl);
        scrollToBottom();
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
