// frontend/script.js

const API_BASE = 'http://localhost:8000';
let sessionId = null;
let messageCount = 0;
let currentLanguage = 'en';
let conversationHistory = [];

// Load conversation history from localStorage
function loadConversationHistory() {
    const stored = localStorage.getItem('jain_conversations');
    if (stored) {
        conversationHistory = JSON.parse(stored);
        updateHistoryUI();
        document.getElementById('sessionCount').textContent = conversationHistory.length;
    }
}

// Save conversation to history
function saveConversation(title, messages) {
    const conversation = {
        id: sessionId,
        title: title,
        timestamp: new Date().toISOString(),
        messages: messages
    };

    // Keep only last 3 conversations
    conversationHistory.unshift(conversation);
    if (conversationHistory.length > 3) {
        conversationHistory = conversationHistory.slice(0, 3);
    }

    localStorage.setItem('jain_conversations', JSON.stringify(conversationHistory));
    updateHistoryUI();
    document.getElementById('sessionCount').textContent = conversationHistory.length;
}

// Update history UI
function updateHistoryUI() {
    const historyList = document.getElementById('historyList');
    historyList.innerHTML = '';

    conversationHistory.forEach((conv, index) => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.onclick = () => loadConversation(index);
        
        const time = new Date(conv.timestamp);
        const timeStr = time.toLocaleDateString() + ' ' + time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        item.innerHTML = `
            <div class="history-item-title">${conv.title}</div>
            <div class="history-item-time">${timeStr}</div>
        `;
        historyList.appendChild(item);
    });
}

// Load a past conversation
function loadConversation(index) {
    const conv = conversationHistory[index];
    sessionId = conv.id;
    
    // Clear chat
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.innerHTML = '';
    
    // Hide welcome screen
    messageCount = conv.messages.length;
    
    // Reload messages
    conv.messages.forEach(msg => {
        if (msg.role === 'user') {
            addMessage(msg.content, 'user');
        } else {
            addMessage(msg.content, 'assistant', msg.sources || [], msg.suggestions || []);
        }
    });
}

// Start new chat
function startNewChat() {
    sessionId = null;
    messageCount = 0;
    currentMessages = [];
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.innerHTML = `
        <div class="welcome-screen">
            <div class="welcome-icon">🕉️</div>
            <h1 class="welcome-title">Welcome to Your Learning Journey</h1>
            <p class="welcome-subtitle">
                I'm here to guide you through the beautiful philosophy and practices of Jainism.
                Whether you're just beginning or deepening your understanding, I'm here to help.
            </p>
            <div class="quick-actions">
                <div class="quick-action-card" onclick="sendQuickMessage('What is Jainism?')">
                    <div class="quick-action-icon">📖</div>
                    <div class="quick-action-title">Introduction to Jainism</div>
                </div>
                <div class="quick-action-card" onclick="sendQuickMessage('Tell me about Ahimsa')">
                    <div class="quick-action-icon">🕊️</div>
                    <div class="quick-action-title">Ahimsa - Non-Violence</div>
                </div>
                <div class="quick-action-card" onclick="sendQuickMessage('Who was Mahavira?')">
                    <div class="quick-action-icon">👤</div>
                    <div class="quick-action-title">Life of Mahavira</div>
                </div>
                <div class="quick-action-card" onclick="sendQuickMessage('How can I practice Jainism daily?')">
                    <div class="quick-action-icon">🧘</div>
                    <div class="quick-action-title">Daily Practices</div>
                </div>
            </div>
        </div>
    `;
}

// Load stats on startup
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();
        document.getElementById('docCount').textContent = data.vector_db.total_documents;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function setLanguage(lang) {
    currentLanguage = lang;
    
    // Update button states
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`lang-${lang}`).classList.add('active');
    
    console.log(`Language set to: ${lang}`);
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function sendQuickMessage(message) {
    document.getElementById('messageInput').value = message;
    sendMessage();
}

let currentMessages = [];

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;

    // Clear input
    input.value = '';
    
    // Hide welcome screen on first message
    if (messageCount === 0) {
        const welcomeScreen = document.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.style.display = 'none';
        }
    }
    messageCount++;

    // Store message
    currentMessages.push({role: 'user', content: message});

    // Add user message
    addMessage(message, 'user');

    // Show loading
    const loadingId = addLoading();

    // Disable input
    const sendBtn = document.getElementById('sendBtn');
    input.disabled = true;
    sendBtn.disabled = true;

    try {
        // Check if audio is enabled
        const includeAudio = document.getElementById('audioToggle').checked;
        
        // Send to API with language parameter
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                user_id: 'web_user',
                session_id: sessionId,
                include_audio: includeAudio,
                language: currentLanguage
            })
        });

        const data = await response.json();
        
        // Store session ID
        if (data.session_id) {
            sessionId = data.session_id;
        }

        // Remove loading
        removeLoading(loadingId);

        // Store assistant message
        currentMessages.push({
            role: 'assistant', 
            content: data.message,
            sources: data.sources,
            suggestions: data.suggestions
        });

        // Add assistant response
        addMessage(data.message, 'assistant', data.sources, data.suggestions, data.audio_url);

        // Save conversation
        if (messageCount === 2) {
            const title = currentMessages[0].content.substring(0, 50) + (currentMessages[0].content.length > 50 ? '...' : '');
            saveConversation(title, currentMessages);
        } else if (messageCount > 2) {
            const title = currentMessages[0].content.substring(0, 50) + (currentMessages[0].content.length > 50 ? '...' : '');
            saveConversation(title, currentMessages);
        }

    } catch (error) {
        console.error('Error:', error);
        removeLoading(loadingId);
        addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
    } finally {
        // Re-enable input
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

function addMessage(text, role, sources = [], suggestions = [], audioUrl = null) {
    const chatContainer = document.getElementById('chatContainer');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🕉️';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Format text with line breaks
    const formattedText = text.replace(/\n/g, '<br>');
    contentDiv.innerHTML = formattedText;
    
    // Add audio player if available
    if (audioUrl) {
        const audioPlayer = document.createElement('audio');
        audioPlayer.controls = true;
        audioPlayer.src = audioUrl;
        contentDiv.appendChild(audioPlayer);
        
        // Auto-play if enabled
        if (document.getElementById('audioToggle').checked) {
            audioPlayer.play().catch(e => console.log('Auto-play blocked:', e));
        }
    }
    
    // Add sources if available
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources';
        sourcesDiv.innerHTML = '<div class="sources-title">📚 Sources:</div>';
        sources.forEach(source => {
            const tag = document.createElement('span');
            tag.className = 'source-tag';
            tag.textContent = `${source.title} (${source.relevance.toFixed(2)})`;
            sourcesDiv.appendChild(tag);
        });
        contentDiv.appendChild(sourcesDiv);
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    
    // Add suggestions if available
    if (suggestions && suggestions.length > 0) {
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.className = 'suggestions';
        suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-btn';
            btn.textContent = suggestion;
            btn.onclick = () => {
                document.getElementById('messageInput').value = suggestion;
                sendMessage();
            };
            suggestionsDiv.appendChild(btn);
        });
        chatContainer.appendChild(suggestionsDiv);
    }
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function addLoading() {
    const chatContainer = document.getElementById('chatContainer');
    const loadingDiv = document.createElement('div');
    const id = 'loading-' + Date.now();
    loadingDiv.id = id;
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = `
        <div class="message-avatar">🕉️</div>
        <div class="message-content">
            <div class="loading">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
        </div>
    `;
    chatContainer.appendChild(loadingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return id;
}

function removeLoading(id) {
    const loadingDiv = document.getElementById(id);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// Initialize
loadStats();
loadConversationHistory();
document.getElementById('messageInput').focus();