/* ============================================================
   AISP2 BASEBALL
   FILE: static/js/chat.js
   PURPOSE: live homepage chat intelligence controller
   ============================================================ */

const AISP2_CHAT_STATE = {
    initialized: false,
    isSending: false,
    messages: [],
    maxMessages: 40,
    endpoint: "/api/chat",
    teams: [],
    players: [],
    lastSummary: null
};

document.addEventListener("DOMContentLoaded", initializeAISP2Chat);

function initializeAISP2Chat() {
    if (AISP2_CHAT_STATE.initialized) return;

    bindChatEvents();
    upgradeChatHeader();
    renderLiveModeNotice();
    focusChatInput();

    AISP2_CHAT_STATE.initialized = true;
}

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

function bindChatEvents() {
    const form = getChatForm();

    if (form) {
        form.addEventListener("submit", handleChatSubmit);
    }

    getSuggestionButtons().forEach(function(button) {
        button.addEventListener("click", function() {
            const prompt = button.dataset.prompt || button.innerText;
            sendChatMessage(prompt);
        });
    });
}

function upgradeChatHeader() {
    const subtitle = document.querySelector(".chat-title span");
    const pill = document.querySelector(".mode-pill");

    if (subtitle) {
        subtitle.innerText = "Baseball intelligence engine · live API mode";
    }

    if (pill) {
        pill.innerText = "LIVE";
    }
}

function renderLiveModeNotice() {
    addBotMessage(
        "AISP2 Live Mode is active. Ask: show all MLB teams, search Corbin Carroll, is the database connected, or how many players are loaded."
    );
}

function handleChatSubmit(event) {
    event.preventDefault();

    const input = getChatInput();
    if (!input) return;

    sendChatMessage(input.value);
}

async function sendChatMessage(rawMessage) {
    if (AISP2_CHAT_STATE.isSending) return;

    const message = cleanMessage(rawMessage);
    if (!message) return;

    addUserMessage(message);
    clearChatInput();
    setChatLoading(true);

    const loadingMessage = addBotMessage("Checking AISP2 live data...");

    try {
        const reply = await routeLiveChatMessage(message);

        updateMessageText(loadingMessage, reply);
        addConversationEntry("assistant", reply);
    } catch (error) {
        console.error("AISP2 live chat error:", error);

        updateMessageText(
            loadingMessage,
            "AISP2 could not complete the live request. The page is running, but the backend endpoint may be missing or temporarily unavailable."
        );
    } finally {
        setChatLoading(false);
        focusChatInput();
    }
}

async function routeLiveChatMessage(message) {
    const text = message.toLowerCase();

    if (
        text.includes("health") ||
        text.includes("api online") ||
        text.includes("api healthy")
    ) {
        return await handleHealthQuestion();
    }

    if (
        text.includes("database") ||
        text.includes("db connected") ||
        text.includes("how many") ||
        text.includes("loaded") ||
        text.includes("synced")
    ) {
        return await handleDatabaseQuestion();
    }

    if (
        text.includes("all teams") ||
        text.includes("show teams") ||
        text.includes("list teams") ||
        text === "teams"
    ) {
        return await handleTeamsQuestion();
    }

    if (
        text.includes("search") ||
        text.includes("find") ||
        text.includes("show me") ||
        text.includes("corbin") ||
        text.includes("judge") ||
        text.includes("ohtani") ||
        text.includes("soto")
    ) {
        return await handlePlayerSearchQuestion(message);
    }

    if (
        text.includes("predict") ||
        text.includes("home run") ||
        text.includes("homer") ||
        text.includes("hit") ||
        text.includes("single") ||
        text.includes("double") ||
        text.includes("triple")
    ) {
        return handlePredictionSetupQuestion(message);
    }

    return await sendMessageToBackendFallback(message);
}

async function handleHealthQuestion() {
    const health = await fetchJSON("/health");

    return [
        "AISP2 Health Check",
        "",
        "API Status: " + (health.status || "unknown"),
        "Service: " + (health.service || "aisp2-baseball"),
        "Phase: " + (health.phase || "unknown"),
        "",
        "The homepage chat is now calling live backend routes instead of only using demo text."
    ].join("\n");
}

async function handleDatabaseQuestion() {
    let summary = null;

    try {
        summary = await fetchJSON("/admin/database/summary");
    } catch (error) {
        summary = await fetchJSON("/health");
    }

    AISP2_CHAT_STATE.lastSummary = summary;

    return [
        "AISP2 Database / Warehouse Status",
        "",
        "Teams: " + formatNumber(summary.teams || 0),
        "Players: " + formatNumber(summary.players || 0),
        "Games: " + formatNumber(summary.games || 0),
        "Game Predictions: " + formatNumber(summary.game_predictions || 0),
        "Player Predictions: " + formatNumber(summary.player_predictions || 0),
        "Statcast Events: " + formatNumber(summary.statcast_events || 0),
        "",
        "If these numbers are zero, the UI is working but the warehouse still needs live data sync."
    ].join("\n");
}

async function handleTeamsQuestion() {
    let teams = [];

    try {
        teams = await fetchJSON("/teams");
    } catch (error) {
        const fallback = await fetchJSON("/api/mlb/teams");
        teams = fallback.teams || [];
    }

    AISP2_CHAT_STATE.teams = Array.isArray(teams) ? teams : [];

    if (AISP2_CHAT_STATE.teams.length === 0) {
        return "No teams were returned. The chat is live, but the teams endpoint is empty or unavailable.";
    }

    const lines = AISP2_CHAT_STATE.teams.map(function(team, index) {
        return (
            (index + 1) +
            ". " +
            (team.name || team.team_name || "Unknown Team") +
            " — " +
            (team.abbreviation || team.abbrev || "N/A")
        );
    });

    return [
        "MLB Teams Loaded: " + AISP2_CHAT_STATE.teams.length,
        "",
        lines.join("\n"),
        "",
        "Next: ask me to search for a player, like Corbin Carroll."
    ].join("\n");
}

async function handlePlayerSearchQuestion(message) {
    const query = extractPlayerQuery(message);

    if (!query) {
        return "Tell me which player to search. Example: search Corbin Carroll.";
    }

    const players = await fetchJSON(
        "/players/search?q=" + encodeURIComponent(query)
    );

    AISP2_CHAT_STATE.players = Array.isArray(players) ? players : [];

    if (AISP2_CHAT_STATE.players.length === 0) {
        return "No players found for: " + query + ". If this should work, run roster sync first.";
    }

    const lines = AISP2_CHAT_STATE.players.slice(0, 10).map(function(player, index) {
        return [
            (index + 1) + ". " + (player.name || "Unknown Player"),
            "   Team: " + (player.team || "Unknown Team"),
            "   Position: " + (player.position || "Unknown"),
            "   Bats/Throws: " + (player.bats || "N/A") + "/" + (player.throws || "N/A")
        ].join("\n");
    });

    return [
        "Player Search Results: " + query,
        "",
        lines.join("\n\n"),
        "",
        "Next: ask for an outcome, like predict Corbin Carroll home run."
    ].join("\n");
}

function handlePredictionSetupQuestion(message) {
    const outcome = extractOutcome(message);
    const playerName = extractPlayerQuery(message) || "Selected Player";

    return [
        "Prediction Setup Ready",
        "",
        "Player: " + playerName,
        "Outcome: " + outcome,
        "",
        "Current Status:",
        "The homepage can now understand prediction requests.",
        "",
        "Next Backend Endpoint Needed:",
        "POST /predict/player",
        "",
        "Once that endpoint exists, this chat can display probability, confidence, model name, and plain-English reasoning."
    ].join("\n");
}

async function sendMessageToBackendFallback(message) {
    try {
        const payload = await sendMessageToBackend(message);
        return payload.reply || getFallbackReply();
    } catch (error) {
        return [
            "I understand the message, but I need a more specific baseball command.",
            "",
            "Try:",
            "show all MLB teams",
            "search Corbin Carroll",
            "is the database connected",
            "predict Aaron Judge home run"
        ].join("\n");
    }
}

async function sendMessageToBackend(message) {
    const response = await fetch(
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

    const payload = await response.json();

    if (!response.ok) {
        throw new Error(
            payload.detail ||
            payload.error ||
            "AISP2 chat request failed."
        );
    }

    return payload;
}

async function fetchJSON(url) {
    const response = await fetch(url);

    const payload = await response.json();

    if (!response.ok) {
        throw new Error(
            payload.detail ||
            payload.error ||
            "AISP2 request failed: " + url
        );
    }

    return payload;
}

function addUserMessage(message) {
    addConversationEntry("user", message);
    return addMessage(message, "user");
}

function addBotMessage(message) {
    return addMessage(message, "bot");
}

function addMessage(message, type) {
    const messages = getChatMessages();

    if (!messages) return null;

    const messageElement = document.createElement("div");

    messageElement.classList.add("message", type);
    messageElement.innerText = message;

    messages.appendChild(messageElement);

    scrollMessagesToBottom();

    return messageElement;
}

function updateMessageText(messageElement, text) {
    if (!messageElement) return;

    messageElement.innerText = text;
    scrollMessagesToBottom();
}

function addConversationEntry(role, content) {
    AISP2_CHAT_STATE.messages.push({
        role: role,
        content: content,
        timestamp: new Date().toISOString()
    });

    if (AISP2_CHAT_STATE.messages.length > AISP2_CHAT_STATE.maxMessages) {
        AISP2_CHAT_STATE.messages =
            AISP2_CHAT_STATE.messages.slice(-AISP2_CHAT_STATE.maxMessages);
    }
}

function setChatLoading(isLoading) {
    AISP2_CHAT_STATE.isSending = isLoading;

    const input = getChatInput();
    const button = document.querySelector(".send-button");

    if (input) {
        input.disabled = isLoading;
    }

    if (button) {
        button.disabled = isLoading;
        button.innerText = isLoading ? "..." : "Ask";
    }
}

function cleanMessage(message) {
    if (!message) return "";
    return String(message).trim();
}

function clearChatInput() {
    const input = getChatInput();
    if (input) input.value = "";
}

function focusChatInput() {
    const input = getChatInput();

    if (!input) return;

    setTimeout(function() {
        input.focus();
    }, 150);
}

function scrollMessagesToBottom() {
    const messages = getChatMessages();

    if (!messages) return;

    messages.scrollTop = messages.scrollHeight;
}

function extractPlayerQuery(message) {
    let text = cleanMessage(message);

    text = text
        .replace(/search for/i, "")
        .replace(/search/i, "")
        .replace(/find player/i, "")
        .replace(/find/i, "")
        .replace(/show me/i, "")
        .replace(/predict/i, "")
        .replace(/home run/i, "")
        .replace(/homer/i, "")
        .replace(/single/i, "")
        .replace(/double/i, "")
        .replace(/triple/i, "")
        .replace(/hit/i, "")
        .trim();

    return text;
}

function extractOutcome(message) {
    const text = message.toLowerCase();

    if (text.includes("home run") || text.includes("homer")) return "Home Run";
    if (text.includes("single")) return "Single";
    if (text.includes("double")) return "Double";
    if (text.includes("triple")) return "Triple";
    if (text.includes("rbi")) return "RBI";
    if (text.includes("walk")) return "Walk";
    if (text.includes("strikeout")) return "Strikeout";
    if (text.includes("hit")) return "Hit";

    return "Selected Outcome";
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString("en-US");
}

function getFallbackReply() {
    return (
        "I am ready for your next baseball question. " +
        "Ask about teams, players, database status, or prediction setup."
    );
}