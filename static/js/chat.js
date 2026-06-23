/* ============================================================
   AISP2 BASEBALL
   FILE: static/js/chat.js
   PURPOSE: chatbot interface logic, message handling,
   suggested prompts, backend requests, loading states,
   error handling, and future AI assistant expansion
   ============================================================ */


/* ============================================================
   SECTION 01 - CHAT STATE
   ============================================================ */

const AISP2_CHAT_STATE = {
    initialized: false,
    isSending: false,
    messages: [],
    maxMessages: 24,
    endpoint: "/api/chat"
};


/* ============================================================
   SECTION 02 - DOM READY INITIALIZATION
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    initializeAISP2Chat
);


function initializeAISP2Chat() {

    if (AISP2_CHAT_STATE.initialized) {
        return;
    }

    bindChatEvents();

    focusChatInput();

    AISP2_CHAT_STATE.initialized = true;
}


/* ============================================================
   SECTION 03 - DOM HELPERS
   ============================================================ */

function getChatForm() {
    return document.getElementById("chat-form");
}


function getChatInput() {
    return document.getElementById("chat-input");
}


function getChatMessages() {
    return document.getElementById("messages");
}


function getSuggestionButtons() {
    return document.querySelectorAll(".suggestion");
}


/* ============================================================
   SECTION 04 - EVENT BINDING
   ============================================================ */

function bindChatEvents() {

    const form = getChatForm();

    if (form) {

        form.addEventListener(
            "submit",
            handleChatSubmit
        );
    }

    const suggestions = getSuggestionButtons();

    suggestions.forEach(
        function(button) {

            button.addEventListener(
                "click",
                function() {

                    const prompt =
                        button.dataset.prompt || button.innerText;

                    sendChatMessage(prompt);
                }
            );
        }
    );
}


/* ============================================================
   SECTION 05 - FORM SUBMISSION
   ============================================================ */

function handleChatSubmit(event) {

    event.preventDefault();

    const input = getChatInput();

    if (!input) {
        return;
    }

    sendChatMessage(
        input.value
    );
}


/* ============================================================
   SECTION 06 - SEND MESSAGE FLOW
   ============================================================ */

async function sendChatMessage(rawMessage) {

    if (AISP2_CHAT_STATE.isSending) {
        return;
    }

    const message =
        cleanMessage(rawMessage);

    if (!message) {
        return;
    }

    addUserMessage(message);

    clearChatInput();

    setChatLoading(true);

    const loadingMessage =
        addBotMessage("Thinking...");

    try {

        const payload =
            await sendMessageToBackend(message);

        updateMessageText(
            loadingMessage,
            payload.reply || getFallbackReply()
        );

        addConversationEntry(
            "assistant",
            payload.reply || getFallbackReply()
        );

    } catch (error) {

        updateMessageText(
            loadingMessage,
            getErrorReply()
        );

        console.error(
            "AISP2 chat error:",
            error
        );

    } finally {

        setChatLoading(false);

        focusChatInput();
    }
}


/* ============================================================
   SECTION 07 - BACKEND REQUEST
   ============================================================ */

async function sendMessageToBackend(message) {

    const response =
        await fetch(
            AISP2_CHAT_STATE.endpoint,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: message
                })
            }
        );

    let payload = {};

    try {

        payload =
            await response.json();

    } catch (error) {

        throw new Error(
            "Invalid JSON response from AISP2 chat backend."
        );
    }

    if (!response.ok) {

        throw new Error(
            payload.detail ||
            payload.error ||
            "AISP2 chat request failed."
        );
    }

    return payload;
}


/* ============================================================
   SECTION 08 - MESSAGE RENDERING
   ============================================================ */

function addUserMessage(message) {

    addConversationEntry(
        "user",
        message
    );

    return addMessage(
        message,
        "user"
    );
}


function addBotMessage(message) {

    return addMessage(
        message,
        "bot"
    );
}


function addMessage(
    message,
    type
) {

    const messages = getChatMessages();

    if (!messages) {
        return null;
    }

    const messageElement =
        document.createElement("div");

    messageElement.classList.add(
        "message",
        type
    );

    messageElement.innerText =
        message;

    messages.appendChild(
        messageElement
    );

    scrollMessagesToBottom();

    return messageElement;
}


function updateMessageText(
    messageElement,
    text
) {

    if (!messageElement) {
        return;
    }

    messageElement.innerText =
        text;

    scrollMessagesToBottom();
}


/* ============================================================
   SECTION 09 - CONVERSATION STATE
   ============================================================ */

function addConversationEntry(
    role,
    content
) {

    AISP2_CHAT_STATE.messages.push({
        role: role,
        content: content,
        timestamp: new Date().toISOString()
    });

    if (
        AISP2_CHAT_STATE.messages.length >
        AISP2_CHAT_STATE.maxMessages
    ) {

        AISP2_CHAT_STATE.messages =
            AISP2_CHAT_STATE.messages.slice(
                -AISP2_CHAT_STATE.maxMessages
            );
    }
}


/* ============================================================
   SECTION 10 - LOADING STATE
   ============================================================ */

function setChatLoading(isLoading) {

    AISP2_CHAT_STATE.isSending =
        isLoading;

    const input = getChatInput();

    const button =
        document.querySelector(
            ".send-button"
        );

    if (input) {
        input.disabled = isLoading;
    }

    if (button) {

        button.disabled = isLoading;

        button.innerText =
            isLoading
                ? "..."
                : "Ask";
    }
}


/* ============================================================
   SECTION 11 - INPUT HELPERS
   ============================================================ */

function cleanMessage(message) {

    if (!message) {
        return "";
    }

    return String(message).trim();
}


function clearChatInput() {

    const input = getChatInput();

    if (!input) {
        return;
    }

    input.value = "";
}


function focusChatInput() {

    const input = getChatInput();

    if (!input) {
        return;
    }

    setTimeout(
        function() {
            input.focus();
        },
        150
    );
}


/* ============================================================
   SECTION 12 - SCROLL HELPERS
   ============================================================ */

function scrollMessagesToBottom() {

    const messages = getChatMessages();

    if (!messages) {
        return;
    }

    messages.scrollTop =
        messages.scrollHeight;
}


/* ============================================================
   SECTION 13 - FALLBACK RESPONSES
   ============================================================ */

function getFallbackReply() {

    return (
        "I am ready for your next baseball question. " +
        "Ask about players, teams, matchups, probabilities, or future predictions."
    );
}


function getErrorReply() {

    return (
        "AISP2 is having trouble responding right now. " +
        "The interface is online, but the assistant backend needs attention."
    );
}


/* ============================================================
   SECTION 14 - FUTURE STREAMING SUPPORT
   ============================================================ */

function prepareStreamingResponse() {

    /*
    Future use:
        - Open streaming connection.
        - Render tokens as they arrive.
        - Show typing animation.
        - Attach citations.
        - Attach probability cards.
    */

    return null;
}


/* ============================================================
   SECTION 15 - FUTURE RESPONSE CARDS
   ============================================================ */

function renderFutureProbabilityCard(payload) {

    /*
    Future use:
        payload.player
        payload.team
        payload.outcome
        payload.probability
        payload.confidence
        payload.explanation
    */

    return null;
}


function renderFuturePlayerCard(payload) {

    /*
    Future use:
        payload.player_name
        payload.position
        payload.team
        payload.recent_stats
        payload.statcast_profile
    */

    return null;
}


function renderFutureTeamCard(payload) {

    /*
    Future use:
        payload.team_name
        payload.record
        payload.division
        payload.recent_form
        payload.key_players
    */

    return null;
}


/* ============================================================
   SECTION 16 - CHAT ROADMAP
   ============================================================ */

/*

16.01 Backend conversation memory

16.02 Streaming responses

16.03 Suggested prompt categories

16.04 Team cards

16.05 Player cards

16.06 Probability cards

16.07 Model explanation cards

16.08 Statcast trend cards

16.09 Source citations

16.10 Voice input

16.11 Multi-agent analyst mode

16.12 Saved conversations

*/