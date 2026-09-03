/**
 * VEYRiX Chat Logic
 * Plain JavaScript implementation for chat behavior and voice features.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('menuToggle');
    const mobileCloseBtn = document.getElementById('mobileCloseBtn');
    const newChatBtn = document.getElementById('newChatBtn');
    const clearChatBtn = document.getElementById('clearChatBtn');
    const chatHistory = document.getElementById('chatHistory');
    const chatContainer = document.getElementById('chatContainer');
    const welcomeScreen = document.getElementById('welcomeScreen');
    const messageList = document.getElementById('messageList');
    const typingIndicator = document.getElementById('typingIndicator');
    const messageInput = document.getElementById('messageInput');
    const micBtn = document.getElementById('micBtn');
    const sendBtn = document.getElementById('sendBtn');

    // State
    let currentChatId = null;
    let isRecording = false;
    let recognition = null;
    let synth = window.speechSynthesis;
    let currentUtterance = null;

    // --- Initialization ---

    async function init() {
        setupEventListeners();
        setupSpeechRecognition();
        await loadChatHistory();
    }

    // --- Event Listeners ---

    function setupEventListeners() {
        // Sidebar Toggles
        menuToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
        mobileCloseBtn.addEventListener('click', () => sidebar.classList.remove('open'));

        // Chat Management
        newChatBtn.addEventListener('click', startNewChat);
        clearChatBtn.addEventListener('click', handleClearChat);

        // Input Handling
        messageInput.addEventListener('input', handleInputResize);
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });

        sendBtn.addEventListener('click', handleSendMessage);
        micBtn.addEventListener('click', toggleSpeechRecognition);
    }

    // --- Chat Logic ---

    async function loadChatHistory() {
        const chats = await VEYRIX_API.getChats();
        renderChatHistory(chats);
    }

    function renderChatHistory(chats) {
        // Remove existing items except label
        const items = chatHistory.querySelectorAll('.chat-item');
        items.forEach(item => item.remove());

        chats.forEach(chat => {
            const btn = document.createElement('button');
            btn.className = `chat-item ${chat.id === currentChatId ? 'active' : ''}`;
            btn.innerHTML = `
                <i data-lucide="message-square"></i>
                <span>${chat.name || 'Untitled Chat'}</span>
                <div class="delete-chat" data-id="${chat.id}">
                    <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                </div>
            `;
            
            btn.onclick = (e) => {
                if (e.target.closest('.delete-chat')) {
                    handleDeleteChat(chat.id);
                } else {
                    selectChat(chat.id);
                }
            };
            
            chatHistory.appendChild(btn);
        });
        lucide.createIcons();
    }

    async function startNewChat() {
        const newChat = await VEYRIX_API.createChat();
        currentChatId = newChat.id;
        messageList.innerHTML = '';
        welcomeScreen.style.display = 'flex';
        await loadChatHistory();
        if (window.innerWidth <= 768) sidebar.classList.remove('open');
    }

    async function selectChat(chatId) {
        currentChatId = chatId;
        welcomeScreen.style.display = 'none';
        messageList.innerHTML = '';
        
        const messages = await VEYRIX_API.getChatMessages(chatId);
        messages.forEach(msg => addMessageToUI(msg.role, msg.content));
        
        await loadChatHistory();
        scrollToBottom();
        if (window.innerWidth <= 768) sidebar.classList.remove('open');
    }

    async function handleDeleteChat(chatId) {
        if (confirm('Delete this chat?')) {
            await VEYRIX_API.deleteChat(chatId);
            if (currentChatId === chatId) {
                currentChatId = null;
                messageList.innerHTML = '';
                welcomeScreen.style.display = 'flex';
            }
            await loadChatHistory();
        }
    }

    async function handleClearChat() {
        if (!currentChatId) return;
        if (confirm('Clear all messages in this chat?')) {
            await VEYRIX_API.clearChat(currentChatId);
            messageList.innerHTML = '';
            welcomeScreen.style.display = 'flex';
        }
    }

    // --- Message Handling ---

    function handleInputResize() {
        messageInput.style.height = 'auto';
        messageInput.style.height = `${messageInput.scrollHeight}px`;
        sendBtn.disabled = !messageInput.value.trim();
    }

    async function handleSendMessage() {
        const text = messageInput.value.trim();
        if (!text) return;

        // Create chat if none exists
        if (!currentChatId) {
            const newChat = await VEYRIX_API.createChat();
            currentChatId = newChat.id;
        }

        welcomeScreen.style.display = 'none';
        addMessageToUI('user', text);
        messageInput.value = '';
        handleInputResize();
        scrollToBottom();

        // Show thinking indicator
        typingIndicator.style.display = 'flex';
        scrollToBottom();

        try {
            const data = await VEYRIX_API.sendMessage(currentChatId, text);
            typingIndicator.style.display = 'none';
            addMessageToUI('assistant', data.response);
            scrollToBottom();
        } catch (error) {
            typingIndicator.style.display = 'none';
            addMessageToUI('assistant', "Sorry, I encountered an error connecting to the server.");
        }
    }

    function addMessageToUI(role, content) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        
        const avatar = role === 'assistant'
        ? '<div class="ai-avatar"><img src="assets/veyrix-logo.png" alt="VEYRiX"></div>'
        : '<div class="user-avatar">S</div>';

        msgDiv.innerHTML = `
            <div class="avatar-container">${avatar}</div>
            <div class="message-content">
                <div class="message-header">
                    <span>${role === 'assistant' ? 'VEYRiX' : 'You'}</span>
                </div>
                <div class="message-body">${content}</div>
                ${role === 'assistant' ? `
                <div class="message-actions">
                    <button class="msg-action-btn tts-btn" title="Read Aloud">
                        <i data-lucide="volume-2"></i>
                    </button>
                    <button class="msg-action-btn" title="Copy to clipboard">
                        <i data-lucide="copy"></i>
                    </button>
                </div>` : ''}
            </div>
        `;

        messageList.appendChild(msgDiv);
        lucide.createIcons();

        // Attach TTS listener
        if (role === 'assistant') {
            const ttsBtn = msgDiv.querySelector('.tts-btn');
            ttsBtn.onclick = () => toggleTTS(content, ttsBtn);
        }
    }

    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // --- Voice Features (Speech to Text) ---

    function setupSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            micBtn.style.display = 'none';
            console.warn('Speech Recognition not supported in this browser.');
            return;
        }

        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add('recording');
            micBtn.querySelector('i').setAttribute('data-lucide', 'square');
            lucide.createIcons();
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            messageInput.value += (messageInput.value ? ' ' : '') + transcript;
            handleInputResize();
        };

        recognition.onerror = (event) => {
            console.error('Speech Recognition Error:', event.error);
            stopRecording();
        };

        recognition.onend = () => {
            stopRecording();
        };
    }

    function toggleSpeechRecognition() {
        if (!recognition) return;
        
        if (isRecording) {
            recognition.stop();
        } else {
            try {
                recognition.start();
            } catch (e) {
                console.error('Start error:', e);
            }
        }
    }

    function stopRecording() {
        isRecording = false;
        micBtn.classList.remove('recording');
        micBtn.querySelector('i').setAttribute('data-lucide', 'mic');
        lucide.createIcons();
    }

    // --- Voice Features (Text to Speech) ---

    function toggleTTS(text, btn) {
        if (synth.speaking && currentUtterance) {
            synth.cancel();
            if (btn.classList.contains('speaking')) {
                stopTTSUI(btn);
                return;
            }
        }

        // Remove speaking class from all other buttons
        document.querySelectorAll('.tts-btn').forEach(b => stopTTSUI(b));

        currentUtterance = new SpeechSynthesisUtterance(text);
        
        currentUtterance.onstart = () => {
            btn.classList.add('speaking');
            btn.querySelector('i').setAttribute('data-lucide', 'volume-x');
            lucide.createIcons();
        };

        currentUtterance.onend = () => {
            stopTTSUI(btn);
        };

        currentUtterance.onerror = () => {
            stopTTSUI(btn);
        };

        synth.speak(currentUtterance);
    }

    function stopTTSUI(btn) {
        btn.classList.remove('speaking');
        btn.querySelector('i').setAttribute('data-lucide', 'volume-2');
        lucide.createIcons();
    }

    // Launch!
    init();
});
