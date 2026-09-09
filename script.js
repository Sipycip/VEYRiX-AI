// ============================================================
// VEYRiX FRONTEND
// ============================================================

let currentChatId = null;

let isSending = false;
let isRecording = false;

let voiceMessage = false;

let recognition = null;
let voices = [];

let initialized = false;


// ============================================================
// DOM ELEMENTS
// ============================================================

let chatList;
let newChatButton;

let messageContainer;
let messageInput;

let sendButton;
let micButton;

let clearChatButton;

let menuToggle;
let mobileCloseButton;

let sidebar;
let topHeader;

let chatContainer;
let welcomeScreen;

let typingIndicator;


// ============================================================
// CACHE DOM
// ============================================================

function cacheDOMElements() {

    chatList =
        document.getElementById(
            "chatHistory"
        );

    newChatButton =
        document.getElementById(
            "newChatBtn"
        );

    messageContainer =
        document.getElementById(
            "messageList"
        );

    messageInput =
        document.getElementById(
            "messageInput"
        );

    sendButton =
        document.getElementById(
            "sendBtn"
        );

    micButton =
        document.getElementById(
            "micBtn"
        );

    clearChatButton =
        document.getElementById(
            "clearChatBtn"
        );

    menuToggle =
        document.getElementById(
            "menuToggle"
        );

    mobileCloseButton =
        document.getElementById(
            "mobileCloseBtn"
        );

    sidebar =
        document.getElementById(
            "sidebar"
        );

    topHeader =
        document.querySelector(
            ".top-header"
        );

    chatContainer =
        document.getElementById(
            "chatContainer"
        );

    welcomeScreen =
        document.getElementById(
            "welcomeScreen"
        );

    typingIndicator =
        document.getElementById(
            "typingIndicator"
        );
}


// ============================================================
// EVENTS
// ============================================================

function setupEventListeners() {

    if (newChatButton) {

        newChatButton.addEventListener(
            "click",
            createNewChat
        );
    }


    if (sendButton) {

        sendButton.addEventListener(
            "click",
            handleSendMessage
        );
    }


    if (messageInput) {

        messageInput.addEventListener(
            "input",
            () => {

                autoResizeInput();

                updateSendButton();
            }
        );


        messageInput.addEventListener(
            "keydown",
            event => {

                if (
                    event.key === "Enter"
                    &&
                    !event.shiftKey
                ) {

                    event.preventDefault();

                    handleSendMessage();
                }
            }
        );
    }


    if (micButton) {

        micButton.addEventListener(
            "click",
            toggleVoiceInput
        );
    }


    if (clearChatButton) {

        clearChatButton.addEventListener(
            "click",
            clearCurrentChat
        );
    }


    /*
       Sidebar toggle.

       Desktop:
       collapse / expand

       Mobile:
       slide in / out
    */

    if (
        menuToggle
        &&
        sidebar
    ) {

        menuToggle.addEventListener(
            "click",
            toggleSidebar
        );
    }


    if (
        mobileCloseButton
        &&
        sidebar
    ) {

        mobileCloseButton.addEventListener(
            "click",
            closeSidebar
        );
    }


    /*
       Close mobile sidebar when
       viewport becomes desktop.
    */

    window.addEventListener(
        "resize",
        handleWindowResize
    );
}


// ============================================================
// SIDEBAR
// ============================================================

function toggleSidebar() {

    if (!sidebar) {
        return;
    }


    if (
        window.innerWidth <= 768
    ) {

        sidebar.classList.toggle(
            "open"
        );

        return;
    }


    sidebar.classList.toggle(
        "collapsed"
    );
}


function closeSidebar() {

    if (!sidebar) {
        return;
    }

    sidebar.classList.remove(
        "open"
    );
}


function handleWindowResize() {

    if (!sidebar) {
        return;
    }


    if (
        window.innerWidth > 768
    ) {

        sidebar.classList.remove(
            "open"
        );
    }
}


// ============================================================
// HEADER VISIBILITY
// ============================================================

function hideTopHeader() {

    if (!topHeader) {
        return;
    }

    topHeader.classList.add(
        "hidden"
    );
}


function showTopHeader() {

    if (!topHeader) {
        return;
    }

    topHeader.classList.remove(
        "hidden"
    );
}


/*
   Header should be visible only
   when current chat has no messages.
*/

function updateHeaderVisibility() {

    if (!messageContainer) {
        return;
    }

    const hasMessages =
        messageContainer.children.length > 0;


    if (hasMessages) {

        hideTopHeader();

    } else {

        showTopHeader();
    }
}


// ============================================================
// LOAD CHATS
// ============================================================

async function loadChats() {

    try {

        const chats =
            await window.VEYRIX_API
                .getChats();


        renderChatList(
            chats
        );


        if (
            chats.length > 0
        ) {

            await openChat(
                chats[0].id
            );

        } else {

            await createNewChat();
        }

    } catch (error) {

        console.error(
            "Failed to load chats:",
            error
        );
    }
}


// ============================================================
// CHAT LIST
// ============================================================

function renderChatList(chats) {

    if (!chatList) {
        return;
    }


    chatList.innerHTML = `
        <div class="history-label">
            Recent Chats
        </div>
    `;


    chats.forEach(
        chat => {

            const chatItem =
                document.createElement(
                    "div"
                );


            chatItem.className =
                "chat-history-item";


            if (
                chat.id
                ===
                currentChatId
            ) {

                chatItem.classList.add(
                    "active"
                );
            }


            // -----------------------------------------------
            // Title
            // -----------------------------------------------

            const title =
                document.createElement(
                    "span"
                );


            title.className =
                "chat-history-title";


            title.textContent =
                chat.title
                ||
                chat.name
                ||
                "New Chat";


            // -----------------------------------------------
            // Delete
            // -----------------------------------------------

            const deleteButton =
                document.createElement(
                    "button"
                );


            deleteButton.className =
                "chat-delete-btn";


            deleteButton.type =
                "button";


            deleteButton.title =
                "Delete chat";


            deleteButton.innerHTML =
                "×";


            deleteButton.addEventListener(
                "click",
                async event => {

                    event.stopPropagation();

                    await deleteChat(
                        chat.id
                    );
                }
            );


            chatItem.appendChild(
                title
            );


            chatItem.appendChild(
                deleteButton
            );


            chatItem.addEventListener(
                "click",
                async () => {

                    await openChat(
                        chat.id
                    );

                    /*
                       On phones, close sidebar
                       after selecting chat.
                    */

                    if (
                        window.innerWidth <= 768
                    ) {

                        closeSidebar();
                    }
                }
            );


            chatList.appendChild(
                chatItem
            );
        }
    );
}


// ============================================================
// NEW CHAT
// ============================================================

async function createNewChat() {

    try {

        const chat =
            await window.VEYRIX_API
                .createChat();


        currentChatId =
            chat.id;


        clearMessagesFromUI();


        updateWelcomeScreen();

        updateHeaderVisibility();


        await refreshChatList();


        if (messageInput) {

            messageInput.value = "";

            autoResizeInput();

            updateSendButton();

            messageInput.focus();
        }


        /*
           A new empty chat should
           show the top VEYRiX header.
        */

        showTopHeader();


        /*
           Close mobile sidebar
           after creating chat.
        */

        if (
            window.innerWidth <= 768
        ) {

            closeSidebar();
        }

    } catch (error) {

        console.error(
            "Failed to create chat:",
            error
        );
    }
}


// ============================================================
// OPEN CHAT
// ============================================================

async function openChat(chatId) {

    try {

        const data =
            await window.VEYRIX_API
                .getChatMessages(
                    chatId
                );


        currentChatId =
            chatId;


        clearMessagesFromUI();


        const messages =
            data.messages
            ||
            data
            ||
            [];


        messages.forEach(
            message => {

                addMessageToUI(
                    message.role,
                    message.content,
                    false
                );
            }
        );


        updateWelcomeScreen();

        updateHeaderVisibility();


        await refreshChatList();


        scrollToBottom();

    } catch (error) {

        console.error(
            "Failed to open chat:",
            error
        );
    }
}


// ============================================================
// REFRESH CHAT LIST
// ============================================================

async function refreshChatList() {

    try {

        const chats =
            await window.VEYRIX_API
                .getChats();


        renderChatList(
            chats
        );

    } catch (error) {

        console.error(
            "Failed to refresh chats:",
            error
        );
    }
}


// ============================================================
// DELETE CHAT
// ============================================================

async function deleteChat(chatId) {

    const confirmed =
        confirm(
            "Delete this chat?\n\n"
            +
            "This cannot be undone."
        );


    if (!confirmed) {
        return;
    }


    try {

        await window.VEYRIX_API
            .deleteChat(
                chatId
            );


        if (
            chatId
            ===
            currentChatId
        ) {

            currentChatId =
                null;


            clearMessagesFromUI();


            const chats =
                await window.VEYRIX_API
                    .getChats();


            if (
                chats.length > 0
            ) {

                await openChat(
                    chats[0].id
                );

            } else {

                await createNewChat();
            }

        } else {

            await refreshChatList();
        }

    } catch (error) {

        console.error(
            "Failed to delete chat:",
            error
        );


        alert(
            "Failed to delete chat."
        );
    }
}


// ============================================================
// SEND MESSAGE
// ============================================================

async function handleSendMessage() {

    if (isSending) {
        return;
    }


    if (!messageInput) {
        return;
    }


    if (!currentChatId) {

        await createNewChat();
    }


    const message =
        messageInput
            .value
            .trim();


    if (!message) {
        return;
    }


    isSending = true;


    updateSendButton();


    /*
       Immediately hide header when
       first message begins.
    */

    hideTopHeader();


    addMessageToUI(
        "user",
        message
    );


    messageInput.value =
        "";


    autoResizeInput();

    updateSendButton();

    updateWelcomeScreen();


    showTypingIndicator();


    try {

        const response =
            await window.VEYRIX_API
                .sendMessage(
                    currentChatId,
                    message
                );


        hideTypingIndicator();


        const answer =
            response.response
            ||
            response.message
            ||
            response.content
            ||
            "";


        if (answer) {

            addMessageToUI(
                "assistant",
                answer
            );


            if (voiceMessage) {

                speakText(
                    answer
                );
            }
        }


        voiceMessage =
            false;


        await refreshChatList();

    } catch (error) {

        hideTypingIndicator();


        console.error(
            "Failed to send message:",
            error
        );


        addMessageToUI(
            "assistant",
            "Sorry, I couldn't process that request."
        );


        voiceMessage =
            false;

    } finally {

        isSending =
            false;


        updateSendButton();


        if (messageInput) {

            messageInput.focus();
        }
    }
}


// ============================================================
// MARKDOWN
// ============================================================

function renderMarkdown(markdown) {

    let text =
        String(
            markdown
        );


    // -----------------------------------------------
    // Escape HTML
    // -----------------------------------------------

    text =
        text
            .replace(
                /&/g,
                "&amp;"
            )
            .replace(
                /</g,
                "&lt;"
            )
            .replace(
                />/g,
                "&gt;"
            );


    // -----------------------------------------------
    // Code blocks
    // -----------------------------------------------

    text = text.replace(
        /```(?:[a-zA-Z0-9_+-]+)?\n?([\s\S]*?)```/g,

        "<pre><code>$1</code></pre>"
    );


    // -----------------------------------------------
    // Inline code
    // -----------------------------------------------

    const codeBlocks = [];


    text = text.replace(
        /`([^`]+)`/g,

        (
            match,
            code
        ) => {

            const index =
                codeBlocks.length;


            codeBlocks.push(
                `<code>${code}</code>`
            );


            return (
                `@@CODE${index}@@`
            );
        }
    );


    // -----------------------------------------------
    // Bold
    // -----------------------------------------------

    text = text.replace(
        /\*\*(.+?)\*\*/g,
        "<strong>$1</strong>"
    );


    text = text.replace(
        /__(.+?)__/g,
        "<strong>$1</strong>"
    );


    // -----------------------------------------------
    // Italic
    // -----------------------------------------------

    text = text.replace(
        /(?<!\*)\*([^*\n]+)\*(?!\*)/g,

        "<em>$1</em>"
    );


    text = text.replace(
        /(?<!_)_([^_\n]+)_(?!_)/g,

        "<em>$1</em>"
    );


    // -----------------------------------------------
    // Restore inline code
    // -----------------------------------------------

    text = text.replace(
        /@@CODE(\d+)@@/g,

        (
            match,
            index
        ) => (
            codeBlocks[index]
        )
    );


    // -----------------------------------------------
    // New lines
    // -----------------------------------------------

    text = text.replace(
        /\n/g,
        "<br>"
    );


    return text;
}


// ============================================================
// MESSAGE UI
// ============================================================

function addMessageToUI(
    role,
    content,
    shouldScroll = true
) {

    if (!messageContainer) {
        return;
    }


    const messageWrapper =
        document.createElement(
            "div"
        );


    messageWrapper.className =
        "message";


    if (
        role === "user"
    ) {

        messageWrapper.classList.add(
            "user-message"
        );

    } else {

        messageWrapper.classList.add(
            "assistant-message"
        );
    }


    // -----------------------------------------------
    // Avatar
    // -----------------------------------------------

    const avatar =
        document.createElement(
            "div"
        );


    avatar.className =
        "message-avatar";


    if (
        role === "assistant"
    ) {

        avatar.innerHTML = `
            <img
                src="assets/veyrix-logo.png"
                alt="VEYRiX"
            >
        `;

    } else {

        avatar.textContent =
            "S";
    }


    // -----------------------------------------------
    // Text
    // -----------------------------------------------

    const text =
        document.createElement(
            "div"
        );


    text.className =
        "message-text";


    if (
        role === "assistant"
    ) {

        text.innerHTML =
            renderMarkdown(
                content
            );

    } else {

        text.textContent =
            content;
    }


    messageWrapper.appendChild(
        avatar
    );


    messageWrapper.appendChild(
        text
    );


    messageContainer.appendChild(
        messageWrapper
    );


    updateHeaderVisibility();


    if (shouldScroll) {

        scrollToBottom();
    }
}


// ============================================================
// CLEAR MESSAGES
// ============================================================

function clearMessagesFromUI() {

    if (!messageContainer) {
        return;
    }


    messageContainer.innerHTML =
        "";


    updateHeaderVisibility();
}


// ============================================================
// CLEAR CHAT
// ============================================================

async function clearCurrentChat() {

    if (!currentChatId) {
        return;
    }


    const confirmed =
        confirm(
            "Clear all messages from this chat?"
        );


    if (!confirmed) {
        return;
    }


    try {

        await window.VEYRIX_API
            .clearChat(
                currentChatId
            );


        clearMessagesFromUI();


        updateWelcomeScreen();

        showTopHeader();


        await refreshChatList();

    } catch (error) {

        console.error(
            "Failed to clear chat:",
            error
        );
    }
}


// ============================================================
// WELCOME SCREEN
// ============================================================

function updateWelcomeScreen() {

    if (!welcomeScreen) {
        return;
    }


    const hasMessages =
        messageContainer
        &&
        messageContainer
            .children
            .length
        > 0;


    welcomeScreen.style.display =
        hasMessages
            ? "none"
            : "flex";


    updateHeaderVisibility();
}


// ============================================================
// TYPING INDICATOR
// ============================================================

function showTypingIndicator() {

    if (typingIndicator) {

        typingIndicator.style.display =
            "flex";
    }


    scrollToBottom();
}


function hideTypingIndicator() {

    if (typingIndicator) {

        typingIndicator.style.display =
            "none";
    }
}


// ============================================================
// SEND BUTTON
// ============================================================

function updateSendButton() {

    if (
        !sendButton
        ||
        !messageInput
    ) {

        return;
    }


    const hasText =
        messageInput
            .value
            .trim()
            .length
        > 0;


    if (
        hasText
        &&
        !isSending
    ) {

        sendButton.disabled =
            false;


        sendButton.classList.add(
            "active"
        );

    } else {

        sendButton.disabled =
            true;


        sendButton.classList.remove(
            "active"
        );
    }
}


// ============================================================
// AUTO RESIZE
// ============================================================

function autoResizeInput() {

    if (!messageInput) {
        return;
    }


    messageInput.style.height =
        "auto";


    const maxHeight =
        180;


    messageInput.style.height =
        Math.min(
            messageInput.scrollHeight,
            maxHeight
        )
        +
        "px";
}


// ============================================================
// SCROLL
// ============================================================

function scrollToBottom() {

    if (!chatContainer) {
        return;
    }


    requestAnimationFrame(
        () => {

            chatContainer.scrollTop =
                chatContainer.scrollHeight;
        }
    );
}


// ============================================================
// SPEECH RECOGNITION
// ============================================================

function setupSpeechRecognition() {

    const SpeechRecognition =
        window.SpeechRecognition
        ||
        window.webkitSpeechRecognition;


    if (!SpeechRecognition) {

        console.warn(
            "Speech recognition is not supported in this browser."
        );


        if (micButton) {

            micButton.disabled =
                true;
        }


        return;
    }


    recognition =
        new SpeechRecognition();


    recognition.continuous =
        true;


    recognition.interimResults =
        false;


    recognition.lang =
        "en-US";


    recognition.maxAlternatives =
        1;


    recognition.onstart =
        () => {

            isRecording =
                true;


            updateMicButton();
        };


    recognition.onresult =
        event => {

            let transcript =
                "";


            for (
                let i =
                    event.resultIndex;

                i
                <
                event.results.length;

                i++
            ) {

                if (
                    event.results[i]
                        .isFinal
                ) {

                    transcript +=
                        event
                            .results[i][0]
                            .transcript;
                }
            }


            transcript =
                transcript.trim();


            if (!transcript) {
                return;
            }


            if (messageInput) {

                messageInput.value =
                    transcript;
            }


            autoResizeInput();

            updateSendButton();


            voiceMessage =
                true;


            handleSendMessage();
        };


    recognition.onerror =
        event => {

            console.error(
                "Speech recognition error:",
                event.error
            );


            if (
                event.error
                ===
                "not-allowed"

                ||

                event.error
                ===
                "service-not-allowed"
            ) {

                isRecording =
                    false;


                updateMicButton();


                return;
            }


            if (isRecording) {

                try {

                    recognition.stop();

                } catch (error) {

                    console.error(
                        error
                    );
                }
            }
        };


    recognition.onend =
        () => {

            if (
                isRecording
                &&
                !isSending
            ) {

                try {

                    recognition.start();

                    return;

                } catch (error) {

                    console.error(
                        error
                    );
                }
            }


            isRecording =
                false;


            updateMicButton();
        };
}


// ============================================================
// TOGGLE MICROPHONE
// ============================================================

function toggleVoiceInput() {

    if (!recognition) {
        return;
    }


    if (isRecording) {

        isRecording =
            false;


        try {

            recognition.stop();

        } catch (error) {

            console.error(
                error
            );
        }


        updateMicButton();

    } else {

        try {

            recognition.start();

        } catch (error) {

            console.error(
                "Could not start speech recognition:",
                error
            );
        }
    }
}


// ============================================================
// MIC UI
// ============================================================

function updateMicButton() {

    if (!micButton) {
        return;
    }


    if (isRecording) {

        micButton.classList.add(
            "active"
        );


        micButton.classList.add(
            "recording"
        );

    } else {

        micButton.classList.remove(
            "active"
        );


        micButton.classList.remove(
            "recording"
        );
    }
}


// ============================================================
// TEXT TO SPEECH
// ============================================================

function loadVoices() {

    if (
        !(
            "speechSynthesis"
            in
            window
        )
    ) {

        return;
    }


    voices =
        speechSynthesis
            .getVoices();
}


if (
    "speechSynthesis"
    in
    window
) {

    speechSynthesis
        .onvoiceschanged =
        loadVoices;
}


function speakText(text) {

    if (
        !(
            "speechSynthesis"
            in
            window
        )
    ) {

        return;
    }


    speechSynthesis.cancel();


    const utterance =
        new SpeechSynthesisUtterance(
            text
        );


    const preferredVoice =
        voices.find(
            voice => {

                const name =
                    voice.name
                        .toLowerCase();


                const language =
                    voice.lang
                        .toLowerCase();


                return (
                    language
                        .startsWith(
                            "en"
                        )

                    &&

                    (
                        name.includes(
                            "male"
                        )

                        ||

                        name.includes(
                            "david"
                        )

                        ||

                        name.includes(
                            "mark"
                        )

                        ||

                        name.includes(
                            "daniel"
                        )
                    )
                );
            }
        );


    if (preferredVoice) {

        utterance.voice =
            preferredVoice;
    }


    utterance.lang =
        "en-US";


    utterance.rate =
        1;


    utterance.pitch =
        1;


    utterance.onend =
        () => {

            if (
                isRecording
                &&
                recognition
            ) {

                try {

                    recognition.start();

                } catch (error) {

                    console.error(
                        error
                    );
                }
            }
        };


    speechSynthesis.speak(
        utterance
    );
}


// ============================================================
// START APP
// ============================================================

function startApplication() {

    if (initialized) {
        return;
    }


    initialized =
        true;


    cacheDOMElements();


    setupEventListeners();


    setupSpeechRecognition();


    loadVoices();


    loadChats().catch(
        error => {

            console.error(
                "Failed to load chats:",
                error
            );
        }
    );


    updateSendButton();


    updateMicButton();


    updateHeaderVisibility();
}


// ============================================================
// START
// ============================================================

if (
    document.readyState
    ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        startApplication
    );

} else {

    startApplication();
}
