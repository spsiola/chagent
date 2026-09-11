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
        document.getElementById('send-button').disabled = true;
        document.getElementById('send-button').style.opacity = '0.5';
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
                document.getElementById('send-button').disabled = true;
                document.getElementById('send-button').style.opacity = '0.5';
            } else {
                statusDiv.classList.add('connected');
                statusDiv.title = 'Connected';
                document.getElementById('send-button').disabled = false;
                document.getElementById('send-button').style.opacity = '1';
            }
        } catch (err) {
            console.error(err);
            statusDiv.classList.remove('testing');
            statusDiv.classList.remove('connected');
            statusDiv.title = 'Model Error';
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
                const header = child.querySelector('.tool-event-header') ? child.querySelector('.tool-event-header').innerText.trim() : "";
                const content = child.querySelector('.tool-event-content pre') ? child.querySelector('.tool-event-content pre').textContent.trim() : "";
                log += `Инструмент: ${header}\n${content}\n\n`;
            } else if (child.classList.contains('harness-logs-container')) {
                const toggle = document.getElementById('toggle-harness-logs');
                if (toggle && toggle.checked) {
                    for (let logNode of child.children) {
                        if (logNode.classList.contains('harness-log')) {
                            log += `${logNode.innerText.trim()}\n`;
                        }
                    }
                }
            } else if (child.classList.contains('error-event')) {
                log += `${child.innerText.trim()}\n\n`;
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
    if (event.type === 'clear') {
        chatContainer.innerHTML = '';
        currentInfoElement = null;
        return;
    }

    if (event.type === 'history') {
        if (!event.history || event.history.length === 0) return;
        
        const welcomeMsg = document.querySelector('.welcome-message');
        if (welcomeMsg) welcomeMsg.remove();
        
        event.history.forEach(msg => {
            if (msg.role === 'user') {
                const msgEl = document.createElement('div');
                msgEl.className = 'message user';
                msgEl.innerHTML = `<div class="message-bubble">${msg.content}</div>`;
                chatContainer.appendChild(msgEl);
            } else if (msg.role === 'assistant') {
                if (msg.content) {
                    const msgEl = document.createElement('div');
                    msgEl.className = 'message ai';
                    const bubble = document.createElement('div');
                    bubble.className = 'message-bubble';
                    let formatted = msg.content.replace(/\n/g, '<br>');
                    formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre style="background:rgba(0,0,0,0.3);padding:10px;border-radius:8px;margin-top:8px;"><code>$1</code></pre>');
                    bubble.innerHTML = formatted;
                    msgEl.appendChild(bubble);
                    chatContainer.appendChild(msgEl);
                }
                if (msg.tool_calls) {
                    msg.tool_calls.forEach(tc => {
                        const toolEl = document.createElement('div');
                        toolEl.className = 'tool-event';
                        let argsStr = typeof tc.function.arguments === 'string' ? tc.function.arguments : JSON.stringify(tc.function.arguments, null, 2);
                        try {
                            const parsed = JSON.parse(argsStr);
                            argsStr = JSON.stringify(parsed, null, 2);
                        } catch(e) {}
                        
                        const estTokens = Math.ceil(argsStr.length / 4);
                        toolEl.innerHTML = `
                            <div class="tool-event-header">
                                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" style="flex-shrink:0"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                                <span>Вызов инструмента: <strong>${tc.function.name}</strong> (~${estTokens} токенов)</span>
                                <svg class="chevron" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polyline points="6 9 12 15 18 9"></polyline></svg>
                            </div>
                            <div class="tool-event-content">
                                <pre>${argsStr}</pre>
                            </div>
                        `;
                        toolEl.querySelector('.tool-event-header').addEventListener('click', () => toolEl.classList.toggle('expanded'));
                        chatContainer.appendChild(toolEl);
                    });
                }
            } else if (msg.role === 'tool') {
                const resEl = document.createElement('div');
                resEl.className = 'tool-event tool-result';
                resEl.style.backgroundColor = 'rgba(16, 185, 129, 0.15)';
                resEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                resEl.style.color = '#10b981';
                
                const estTokens = msg.content ? Math.ceil(msg.content.length / 4) : 0;
                let formattedContent = msg.content;
                try {
                    const parsed = JSON.parse(msg.content);
                    formattedContent = JSON.stringify(parsed, null, 2);
                } catch(e) {}
                
                resEl.innerHTML = `
                    <div class="tool-event-header">
                        <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" style="flex-shrink:0"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
                        <span>Ответ инструмента${msg.name ? `: <strong>${msg.name}</strong>` : ''} (~${estTokens} токенов)</span>
                        <svg class="chevron" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </div>
                    <div class="tool-event-content">
                        <pre>${formattedContent}</pre>
                    </div>
                `;
                resEl.querySelector('.tool-event-header').addEventListener('click', () => resEl.classList.toggle('expanded'));
                chatContainer.appendChild(resEl);
            }
        });
        scrollToBottom();
        return;
    }

    if (event.type === 'metrics') {
        const metricsEl = document.getElementById('metrics-status');
        const metricsText = document.getElementById('metrics-text');
        if (metricsEl && metricsText) {
            metricsEl.style.display = 'flex';
            metricsText.textContent = `~${event.tokens} tokens`;
        }
        return; // Метрики не должны отображаться в самом чате
    }
    
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
        
        let formatted = event.content.replace(/\n/g, '<br>');
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre style="background:rgba(0,0,0,0.3);padding:10px;border-radius:8px;margin-top:8px;"><code>$1</code></pre>');
        
        bubble.innerHTML = formatted;
        msgEl.appendChild(bubble);
        chatContainer.appendChild(msgEl);
        scrollToBottom();
    }
    else if (event.type === 'message_start') {
        removeInfoElement();
        const msgEl = document.createElement('div');
        msgEl.className = 'message ai';
        if (event.model && event.provider) {
            msgEl.dataset.model = `${event.provider}/${event.model}`;
        }
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.id = 'active-ai-bubble';
        
        msgEl.appendChild(bubble);
        chatContainer.appendChild(msgEl);
        window.activeAiContent = "";
        scrollToBottom();
    }
    else if (event.type === 'message_chunk') {
        window.activeAiContent += event.content;
        const bubble = document.getElementById('active-ai-bubble');
        if (bubble) {
            let formatted = window.activeAiContent.replace(/\n/g, '<br>');
            formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre style="background:rgba(0,0,0,0.3);padding:10px;border-radius:8px;margin-top:8px;"><code>$1</code></pre>');
            bubble.innerHTML = formatted;
            scrollToBottom();
        }
    }
    else if (event.type === 'tool_call') {
        removeInfoElement();
        const toolEl = document.createElement('div');
        toolEl.className = 'tool-event';
        
        let argsStr = '';
        try { argsStr = JSON.stringify(event.args, null, 2); } catch(e) { argsStr = event.args; }
        
        const estTokens = Math.ceil(argsStr.length / 4);
        toolEl.innerHTML = `
            <div class="tool-event-header">
                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" style="flex-shrink:0"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                <span>Вызов инструмента: <strong>${event.name}</strong> (~${estTokens} токенов)</span>
                <svg class="chevron" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </div>
            <div class="tool-event-content">
                <pre>${argsStr}</pre>
            </div>
        `;
        toolEl.querySelector('.tool-event-header').addEventListener('click', () => toolEl.classList.toggle('expanded'));
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
        
        const estTokens = event.content ? Math.ceil(event.content.length / 4) : 0;
        let formattedContent = event.content;
        try {
            const parsed = JSON.parse(event.content);
            formattedContent = JSON.stringify(parsed, null, 2);
        } catch(e) {}
        
        resEl.innerHTML = `
            <div class="tool-event-header">
                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" style="flex-shrink:0"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
                <span>Ответ инструмента${event.name ? `: <strong>${event.name}</strong>` : ''} (~${estTokens} токенов)</span>
                <svg class="chevron" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </div>
            <div class="tool-event-content">
                <pre>${formattedContent}</pre>
            </div>
        `;
        resEl.querySelector('.tool-event-header').addEventListener('click', () => resEl.classList.toggle('expanded'));
        chatContainer.appendChild(resEl);
        scrollToBottom();
    }
    else if (event.type === 'finish') {
        removeInfoElement();
        const bubble = document.getElementById('active-ai-bubble');
        if (bubble) bubble.removeAttribute('id');
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
        infoEl.className = 'info-event error-event';
        infoEl.style.color = '#ef4444';
        infoEl.textContent = `Harness: Ошибка: ${event.content}`;
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

// --- Settings Modal Logic ---
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const closeSettingsBtn = document.getElementById('close-settings-btn');
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

// Settings DOM Elements
const themeSelect = document.getElementById('theme-select');
const timezoneInput = document.getElementById('timezone-input');
const saveSettingsBtn = document.getElementById('save-settings-btn');

// Prompts DOM Elements
const promptContextSelect = document.getElementById('prompt-context-select');
const systemPromptTextarea = document.getElementById('system-prompt-textarea');
const savePromptBtn = document.getElementById('save-prompt-btn');

let currentPromptsData = { default: "", models: {} };

settingsBtn.addEventListener('click', async () => {
    settingsModal.classList.add('show');
    await loadSettingsAndPrompts();
});

closeSettingsBtn.addEventListener('click', () => {
    settingsModal.classList.remove('show');
});

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        settingsModal.classList.remove('show');
    }
});

// Tab switching logic
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    });
});

// Help tab logic
const helpTabBtn = document.querySelector('[data-tab="tab-help"]');
const helpMarkdownContainer = document.getElementById('help-markdown-container');

if (helpTabBtn) {
    helpTabBtn.addEventListener('click', async () => {
        try {
            helpMarkdownContainer.innerHTML = '<p>Загрузка...</p>';
            const res = await fetch('/api/help');
            const data = await res.json();
            helpMarkdownContainer.innerHTML = marked.parse(data.content);
        } catch (e) {
            console.error("Error loading help:", e);
            helpMarkdownContainer.innerHTML = '<p style="color:#ef4444;">Ошибка загрузки справки</p>';
        }
    });
}

// Tools tab logic
const toolsTabBtn = document.querySelector('[data-tab="tab-tools"]');
const toolsMarkdownContainer = document.getElementById('tools-markdown-container');
const toolsViewToggle = document.getElementById('tools-view-toggle');
let currentToolsData = null;

function renderTools() {
    if (!currentToolsData || currentToolsData.length === 0) {
        toolsMarkdownContainer.innerHTML = '<p>Инструменты не загружены (возможно агент еще инициализируется).</p>';
        return;
    }

    if (toolsViewToggle && toolsViewToggle.checked) {
        // Формальный JSON
        const toolsJson = JSON.stringify(currentToolsData, null, 2);
        const markdown = `**Текущий массив \`agent.tools\`:**\n\n\`\`\`json\n${toolsJson}\n\`\`\``;
        toolsMarkdownContainer.innerHTML = marked.parse(markdown);
    } else {
        // Удобный для человека вид
        let markdown = `**Доступные инструменты (${currentToolsData.length}):**\n\n`;
        currentToolsData.forEach(tool => {
            if (tool.type === 'function' && tool.function) {
                markdown += `### 🛠 \`${tool.function.name}\`\n`;
                markdown += `**Описание:** ${tool.function.description || 'Нет описания'}\n\n---\n`;
            } else {
                markdown += `### 🛠 \`Неизвестный тип\`\n\n`;
            }
        });
        toolsMarkdownContainer.innerHTML = marked.parse(markdown);
    }
}

if (toolsViewToggle) {
    toolsViewToggle.addEventListener('change', renderTools);
}

if (toolsTabBtn) {
    toolsTabBtn.addEventListener('click', async () => {
        try {
            toolsMarkdownContainer.innerHTML = '<p>Загрузка...</p>';
            const res = await fetch('/api/tools');
            const data = await res.json();
            currentToolsData = data.tools;
            renderTools();
        } catch (e) {
            console.error("Error loading tools:", e);
            toolsMarkdownContainer.innerHTML = '<p style="color:#ef4444;">Ошибка загрузки списка инструментов</p>';
        }
    });
}

// Stats tab logic
const statsTabBtn = document.querySelector('[data-tab="tab-stats"]');
const refreshStatsBtn = document.getElementById('refresh-stats-btn');
const statsSummaryContainer = document.getElementById('stats-summary-container');
const statsTableBody = document.getElementById('stats-table-body');

async function loadStats() {
    try {
        if (statsTableBody) statsTableBody.innerHTML = '<tr><td colspan="4" style="text-align: center;">Загрузка...</td></tr>';
        const res = await fetch('/api/stats');
        const data = await res.json();
        
        const sessionStats = data.session_stats || [];
        
        if (sessionStats.length === 0) {
            if (statsTableBody) statsTableBody.innerHTML = '<tr><td colspan="4" style="text-align: center;">Нет данных за текущую сессию</td></tr>';
            if (statsSummaryContainer) statsSummaryContainer.innerHTML = '';
            return;
        }
        
        let totalPrompt = 0;
        let totalCompletion = 0;
        let totalTokens = 0;
        
        if (statsTableBody) statsTableBody.innerHTML = '';
        sessionStats.forEach(stat => {
            totalPrompt += stat.prompt_tokens || 0;
            totalCompletion += stat.completion_tokens || 0;
            totalTokens += stat.total_tokens || 0;
            
            const tr = document.createElement('tr');
            // Assuming timestamp is returned in UTC ISO string by sqlite if not formatted, 
            // but standard sqlite returns strings like '2023-10-12 15:30:00'
            const dt = stat.timestamp.includes('Z') ? new Date(stat.timestamp) : new Date(stat.timestamp + 'Z');
            const timeStr = dt.toLocaleTimeString();
            
            tr.innerHTML = `
                <td>${timeStr}</td>
                <td>${stat.provider} / ${stat.model}</td>
                <td><span style="color: #94a3b8;">${stat.prompt_tokens}</span> / <span style="color: #10b981;">${stat.completion_tokens}</span></td>
                <td>${stat.duration_ms}</td>
            `;
            if (statsTableBody) statsTableBody.appendChild(tr);
        });
        
        if (statsSummaryContainer) {
            statsSummaryContainer.innerHTML = `
                <div class="stat-box">
                    <div class="stat-value">${sessionStats.length}</div>
                    <div class="stat-label">Запросов</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${totalTokens}</div>
                    <div class="stat-label">Всего токенов</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" style="color: #10b981;">${totalCompletion}</div>
                    <div class="stat-label">Сгенерировано</div>
                </div>
            `;
        }
    } catch (e) {
        console.error("Error loading stats:", e);
        if (statsTableBody) statsTableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #ef4444;">Ошибка загрузки</td></tr>';
    }
}

if (statsTabBtn) {
    statsTabBtn.addEventListener('click', loadStats);
}

if (refreshStatsBtn) {
    refreshStatsBtn.addEventListener('click', loadStats);
}

async function loadSettingsAndPrompts() {
    try {
        // Load App Settings
        const settingsRes = await fetch('/api/settings');
        const settings = await settingsRes.json();
        if (settings.theme) themeSelect.value = settings.theme;
        if (settings.timezone) timezoneInput.value = settings.timezone;
        applyTheme(settings.theme || 'dark');
        
        // Load Prompts
        const promptsRes = await fetch('/api/memory/prompts');
        currentPromptsData = await promptsRes.json();
        
        if (currentPromptsData.system_template) {
            document.getElementById('system-template-textarea').value = currentPromptsData.system_template;
        }
        if (currentPromptsData.tool_rules) {
            document.getElementById('tool-rules-textarea').value = currentPromptsData.tool_rules;
        }
        
        // Populate model dropdown for prompts (based on currently available models from the header select)
        promptContextSelect.innerHTML = '<option value="default">По умолчанию (все модели)</option>';
        if (modelSelect && modelSelect.options) {
            Array.from(modelSelect.options).forEach(opt => {
                try {
                    const m = JSON.parse(opt.value);
                    const id = `${m.provider_name}/${m.model_name}`;
                    const el = document.createElement('option');
                    el.value = id;
                    el.textContent = `${m.provider_name}: ${m.model_name}`;
                    promptContextSelect.appendChild(el);
                } catch(e) {}
            });
        }
        
        updatePromptTextarea();
    } catch (e) {
        console.error("Error loading settings/prompts:", e);
    }
}

function updatePromptTextarea() {
    const selected = promptContextSelect.value;
    const label = document.getElementById('system-prompt-label');
    
    if (selected === 'default') {
        systemPromptTextarea.value = currentPromptsData.default || '';
        systemPromptTextarea.style.fontStyle = 'normal';
        if (label) label.textContent = 'Системный промпт (По умолчанию)';
    } else {
        const modelPrompt = currentPromptsData.models && currentPromptsData.models[selected];
        if (modelPrompt) {
            systemPromptTextarea.value = modelPrompt;
            systemPromptTextarea.style.fontStyle = 'normal';
            if (label) label.textContent = 'Системный промпт';
        } else {
            // Если для конкретной модели еще не задан, показываем дефолтный
            systemPromptTextarea.value = currentPromptsData.default || '';
            systemPromptTextarea.style.fontStyle = 'italic';
            if (label) label.textContent = 'Системный промпт (пуст, показан дефолтный)';
        }
    }
}

systemPromptTextarea.addEventListener('input', () => {
    systemPromptTextarea.style.fontStyle = 'normal';
    const label = document.getElementById('system-prompt-label');
    if (promptContextSelect.value !== 'default' && label && label.textContent.includes('пуст')) {
        label.textContent = 'Системный промпт (редактируется)';
    }
});

promptContextSelect.addEventListener('change', updatePromptTextarea);

saveSettingsBtn.addEventListener('click', async () => {
    const theme = themeSelect.value;
    const timezone = timezoneInput.value;
    saveSettingsBtn.textContent = 'Сохранение...';
    try {
        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ theme, timezone })
        });
        applyTheme(theme);
        saveSettingsBtn.textContent = 'Сохранено ✓';
        setTimeout(() => saveSettingsBtn.textContent = 'Сохранить настройки', 2000);
    } catch (e) {
        console.error("Save settings error:", e);
        saveSettingsBtn.textContent = 'Ошибка';
        setTimeout(() => saveSettingsBtn.textContent = 'Сохранить настройки', 2000);
    }
});

savePromptBtn.addEventListener('click', async () => {
    const model_id = promptContextSelect.value;
    const prompt = systemPromptTextarea.value;
    savePromptBtn.textContent = 'Сохранение...';
    try {
        await fetch('/api/memory/prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id, prompt })
        });
        
        // Update local cache
        if (model_id === 'default') {
            currentPromptsData.default = prompt;
        } else {
            if (!currentPromptsData.models) currentPromptsData.models = {};
            currentPromptsData.models[model_id] = prompt;
        }
        
        savePromptBtn.textContent = 'Сохранено ✓';
        setTimeout(() => savePromptBtn.textContent = 'Сохранить промпт', 2000);
    } catch (e) {
        console.error("Save prompt error:", e);
        savePromptBtn.textContent = 'Ошибка';
        setTimeout(() => savePromptBtn.textContent = 'Сохранить промпт', 2000);
    }
});

const saveTemplateBtn = document.getElementById('save-template-btn');
if (saveTemplateBtn) {
    saveTemplateBtn.addEventListener('click', async () => {
        const system_template = document.getElementById('system-template-textarea').value;
        const tool_rules = document.getElementById('tool-rules-textarea').value;
        saveTemplateBtn.textContent = 'Сохранение...';
        try {
            await fetch('/api/memory/prompts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ system_template, tool_rules })
            });
            
            if (currentPromptsData) {
                currentPromptsData.system_template = system_template;
                currentPromptsData.tool_rules = tool_rules;
            }
            
            saveTemplateBtn.textContent = 'Сохранено ✓';
            setTimeout(() => saveTemplateBtn.textContent = 'Сохранить структуру', 2000);
        } catch (e) {
            console.error("Save template error:", e);
            saveTemplateBtn.textContent = 'Ошибка';
            setTimeout(() => saveTemplateBtn.textContent = 'Сохранить структуру', 2000);
        }
    });
}

function applyTheme(theme) {
    if (theme === 'light') {
        document.body.classList.add('theme-light');
    } else if (theme === 'system') {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
            document.body.classList.add('theme-light');
        } else {
            document.body.classList.remove('theme-light');
        }
    } else {
        document.body.classList.remove('theme-light');
    }
}

// Check initial theme on load
fetch('/api/settings').then(r => r.json()).then(s => {
    if (s && s.theme) applyTheme(s.theme);
}).catch(e => {});
