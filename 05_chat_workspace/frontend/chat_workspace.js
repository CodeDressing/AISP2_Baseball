/* ============================================================
AISP2 BASEBALL
PHASE 6.00
FILE: 05_chat_workspace/frontend/chat_workspace.js
PURPOSE: Enterprise frontend orchestration layer for the
floating AISP2 baseball intelligence workspace.

This file connects:
- chat_shell.html
- chat_workspace.css
- backend API routes
- real team data
- real player search
- conversation state
- localStorage persistence
- drag behavior
- resize behavior
- fullscreen/minimize/collapse behavior
- future prediction workflow

Existing shell and styling are already present in:
- chat_shell.html
- chat_workspace.css
============================================================ */


/* ============================================================
SECTION 01 - STRICT MODE AND GLOBAL SAFETY WRAPPER
============================================================ */

"use strict";


/* ============================================================
SECTION 02 - AISP2 WORKSPACE CONSTANTS
============================================================ */

const AISP2_WORKSPACE_VERSION = "phase_6_00";

const AISP2_DEFAULT_API_BASE_URL = "https://aisp-baseball-api.onrender.com";

const AISP2_STORAGE_KEYS = Object.freeze({
    workspaceState: "aisp2_chat_workspace_state",
    conversationState: "aisp2_conversation_state",
    uiState: "aisp2_chat_ui_state",
    activeTab: "aisp2_chat_active_tab",
    dragState: "aisp2_chat_drag_state",
    resizeState: "aisp2_chat_resize_state",
    selectedTeam: "aisp2_selected_team",
    selectedPlayer: "aisp2_selected_player",
    selectedPrediction: "aisp2_selected_prediction",
    apiBaseUrl: "aisp2_api_base_url",
});

const AISP2_UI_STATES = Object.freeze({
    open: "open",
    collapsed: "collapsed",
    minimized: "minimized",
    fullscreen: "fullscreen",
    hidden: "hidden",
});

const AISP2_TABS = Object.freeze({
    chat: "chat",
    teams: "teams",
    players: "players",
    predictions: "predictions",
    system: "system",
});

const AISP2_MESSAGE_ROLES = Object.freeze({
    user: "user",
    assistant: "assistant",
    system: "system",
    error: "error",
});

const AISP2_INTENTS = Object.freeze({
    health: "health",
    database: "database",
    teams: "teams",
    teamSearch: "team_search",
    playerSearch: "player_search",
    playerProfile: "player_profile",
    predictionSetup: "prediction_setup",
    warehouse: "warehouse",
    help: "help",
    unknown: "unknown",
});

const AISP2_OUTCOME_MARKETS = Object.freeze([
    {
        id: "hit_1_plus",
        label: "Gets at least 1 hit",
        category: "batting",
    },
    {
        id: "single",
        label: "Hits a single",
        category: "batting",
    },
    {
        id: "double",
        label: "Hits a double",
        category: "batting",
    },
    {
        id: "triple",
        label: "Hits a triple",
        category: "batting",
    },
    {
        id: "home_run",
        label: "Hits a home run",
        category: "batting",
    },
    {
        id: "rbi",
        label: "Records an RBI",
        category: "batting",
    },
    {
        id: "run",
        label: "Scores a run",
        category: "batting",
    },
    {
        id: "walk",
        label: "Draws a walk",
        category: "batting",
    },
    {
        id: "strikeout",
        label: "Strikes out",
        category: "batting",
    },
    {
        id: "stolen_base",
        label: "Steals a base",
        category: "baserunning",
    },
    {
        id: "total_bases_0_5",
        label: "Over 0.5 total bases",
        category: "batting",
    },
    {
        id: "total_bases_1_5",
        label: "Over 1.5 total bases",
        category: "batting",
    },
    {
        id: "total_bases_2_5",
        label: "Over 2.5 total bases",
        category: "batting",
    },
]);

const AISP2_SELECTORS = Object.freeze({
    root: "[data-aisp2-floating-panel]",
    window: "[data-aisp2-chat-window]",
    header: "[data-aisp2-chat-drag-handle]",
    messages: "[data-aisp2-chat-messages]",
    form: "[data-aisp2-chat-form]",
    input: "[data-aisp2-chat-input]",
    send: "[data-aisp2-chat-send]",
    collapse: "[data-aisp2-chat-collapse]",
    fullscreen: "[data-aisp2-chat-fullscreen]",
    close: "[data-aisp2-chat-close]",
    launcher: "[data-aisp2-chat-launcher]",
    resizeHandle: "[data-aisp2-chat-resize-handle]",
});


/* ============================================================
SECTION 03 - DEFAULT WORKSPACE STATE
============================================================ */

function buildDefaultAisp2WorkspaceState() {
    return {
        version: AISP2_WORKSPACE_VERSION,
        apiBaseUrl: AISP2_DEFAULT_API_BASE_URL,

        ui: {
            state: AISP2_UI_STATES.open,
            activeTab: AISP2_TABS.chat,
            isBootstrapped: false,
            lastError: null,
        },

        drag: {
            x: null,
            y: null,
            isDragging: false,
        },

        resize: {
            width: 560,
            height: 680,
            isResizing: false,
        },

        data: {
            health: null,
            database: null,
            warehouse: null,
            teams: [],
            players: [],
            selectedTeam: null,
            selectedPlayer: null,
            selectedOutcome: AISP2_OUTCOME_MARKETS[0],
            lastPredictionSetup: null,
        },

        conversation: {
            id: "default",
            title: "AISP2 Baseball Assistant",
            messages: [
                {
                    role: AISP2_MESSAGE_ROLES.assistant,
                    content:
                        "Welcome to AISP2. I can now connect to real baseball API routes for teams, players, health checks, warehouse status, and prediction setup.",
                    createdAt: new Date().toISOString(),
                    metadata: {
                        source: "workspace_bootstrap",
                    },
                },
            ],
        },
    };
}


/* ============================================================
SECTION 04 - SAFE LOCAL STORAGE HELPERS
============================================================ */

function aisp2ReadStorage(key, fallbackValue = null) {
    try {
        const rawValue = window.localStorage.getItem(key);

        if (!rawValue) {
            return fallbackValue;
        }

        return JSON.parse(rawValue);
    } catch (error) {
        console.warn("AISP2 storage read failed:", key, error);
        return fallbackValue;
    }
}


function aisp2WriteStorage(key, value) {
    try {
        window.localStorage.setItem(
            key,
            JSON.stringify(value),
        );

        return true;
    } catch (error) {
        console.warn("AISP2 storage write failed:", key, error);
        return false;
    }
}


function aisp2RemoveStorage(key) {
    try {
        window.localStorage.removeItem(key);
        return true;
    } catch (error) {
        console.warn("AISP2 storage remove failed:", key, error);
        return false;
    }
}


/* ============================================================
SECTION 05 - SMALL UTILITY HELPERS
============================================================ */

function aisp2NowIso() {
    return new Date().toISOString();
}


function aisp2Clamp(value, minimum, maximum) {
    return Math.max(
        minimum,
        Math.min(
            value,
            maximum,
        ),
    );
}


function aisp2EscapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function aisp2NormalizeText(value) {
    if (!value) {
        return "";
    }

    return String(value)
        .trim()
        .replace(/\s+/g, " ");
}


function aisp2TitleCase(value) {
    const text = aisp2NormalizeText(value);

    if (!text) {
        return "";
    }

    return text
        .split(" ")
        .map((part) => {
            if (!part) {
                return "";
            }

            return (
                part.charAt(0).toUpperCase()
                + part.slice(1).toLowerCase()
            );
        })
        .join(" ");
}


function aisp2FormatCount(value) {
    const numericValue = Number(value || 0);

    return numericValue.toLocaleString("en-US");
}


function aisp2Sleep(milliseconds) {
    return new Promise((resolve) => {
        window.setTimeout(resolve, milliseconds);
    });
}


/* ============================================================
SECTION 06 - API CLIENT
============================================================ */

class Aisp2ApiClient {
    constructor(baseUrl) {
        this.baseUrl = (
            baseUrl
            || aisp2ReadStorage(
                AISP2_STORAGE_KEYS.apiBaseUrl,
                window.location.origin
            )
            || window.location.origin
        ).replace(/\/+$/, "");
    }

    setBaseUrl(baseUrl) {
        const cleanedBaseUrl = String(baseUrl || "").trim();

        if (!cleanedBaseUrl) {
            return;
        }

        this.baseUrl = cleanedBaseUrl.replace(/\/+$/, "");

        aisp2WriteStorage(
            AISP2_STORAGE_KEYS.apiBaseUrl,
            this.baseUrl
        );
    }

    buildUrl(path, params = null) {
        const safePath = String(path || "").startsWith("/")
            ? path
            : `/${path}`;

        const url = new URL(
            `${this.baseUrl}${safePath}`
        );

        if (params && typeof params === "object") {
            Object.entries(params).forEach(([key, value]) => {
                if (value !== null && value !== undefined && value !== "") {
                    url.searchParams.set(key, String(value));
                }
            });
        }

        return url.toString();
    }

    async request(path, options = {}) {
        const {
            method = "GET",
            params = null,
            body = null,
            timeoutMs = 30000,
        } = options;

        const controller = new AbortController();

        const timeoutId = window.setTimeout(() => {
            controller.abort();
        }, timeoutMs);

        try {
            const response = await fetch(
                this.buildUrl(path, params),
                {
                    method,
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    body: body ? JSON.stringify(body) : null,
                    signal: controller.signal,
                }
            );

            const contentType = response.headers.get("content-type") || "";

            const payload = contentType.includes("application/json")
                ? await response.json()
                : await response.text();

            if (!response.ok) {
                const error = new Error(
                    `AISP2 API request failed: ${response.status}`
                );

                error.status = response.status;
                error.payload = payload;

                throw error;
            }

            return payload;
        } finally {
            window.clearTimeout(timeoutId);
        }
    }

    async sendChatMessage(message) {
        return this.request(
            "/api/chat",
            {
                method: "POST",
                body: {
                    message,
                },
                timeoutMs: 45000,
            }
        );
    }

    async getHealth() {
        return this.request("/health");
    }

    async getDatabaseHealth() {
        return this.request("/health");
    }

    async getSystemInfo() {
        return this.request("/system/info");
    }

    async getWarehouseSummary() {
        return this.request("/project/status");
    }

    async getWarehouseAudit() {
        return this.request("/project/data-sources");
    }

    async getTeams() {
        const payload = await this.request("/api/mlb/teams");

        return payload?.teams || [];
    }

    async getTeam(teamId) {
        const teams = await this.getTeams();

        return teams.find((team) => {
            return String(team.id) === String(teamId);
        }) || null;
    }

    async searchPlayers(query) {
        const teams = await this.getTeams();
        const allPlayers = [];

        for (const team of teams) {
            if (!team?.id) {
                continue;
            }

            try {
                const payload = await this.request(
                    `/api/mlb/teams/${team.id}/players`
                );

                const players = payload?.players || [];

                players.forEach((player) => {
                    allPlayers.push({
                        ...player,
                        team: team.name,
                        team_id: team.id,
                        abbreviation: team.abbreviation,
                    });
                });
            } catch (error) {
                console.warn("AISP2 player roster fetch failed:", team.name, error);
            }
        }

        const normalizedQuery = aisp2NormalizeText(query).toLowerCase();

        return allPlayers.filter((player) => {
            return String(player.name || "")
                .toLowerCase()
                .includes(normalizedQuery);
        });
    }

    async getPlayer(playerId) {
        const players = await this.searchPlayers("");

        return players.find((player) => {
            return String(player.id) === String(playerId);
        }) || null;
    }
}

/* ============================================================
SECTION 07 - DOM CACHE
============================================================ */

class Aisp2DomCache {
    constructor() {
        this.root = null;
        this.window = null;
        this.header = null;
        this.messages = null;
        this.form = null;
        this.input = null;
        this.send = null;
        this.collapse = null;
        this.fullscreen = null;
        this.close = null;
        this.launcher = null;
        this.resizeHandle = null;
    }

    query() {
        this.root = document.querySelector(AISP2_SELECTORS.root);
        this.window = document.querySelector(AISP2_SELECTORS.window);
        this.header = document.querySelector(AISP2_SELECTORS.header);
        this.messages = document.querySelector(AISP2_SELECTORS.messages);
        this.form = document.querySelector(AISP2_SELECTORS.form);
        this.input = document.querySelector(AISP2_SELECTORS.input);
        this.send = document.querySelector(AISP2_SELECTORS.send);
        this.collapse = document.querySelector(AISP2_SELECTORS.collapse);
        this.fullscreen = document.querySelector(AISP2_SELECTORS.fullscreen);
        this.close = document.querySelector(AISP2_SELECTORS.close);
        this.launcher = document.querySelector(AISP2_SELECTORS.launcher);
        this.resizeHandle = document.querySelector(AISP2_SELECTORS.resizeHandle);

        return this;
    }

    isReady() {
        return Boolean(
            this.root
            && this.window
            && this.messages
            && this.form
            && this.input
        );
    }
}


/* ============================================================
SECTION 08 - MESSAGE RENDERING
============================================================ */

function aisp2BuildMessageElement(message) {
    const wrapper = document.createElement("div");

    const role = message.role || AISP2_MESSAGE_ROLES.assistant;

    wrapper.classList.add("aisp2-chat-message");

    if (role === AISP2_MESSAGE_ROLES.user) {
        wrapper.classList.add("aisp2-chat-message-user");
    } else if (role === AISP2_MESSAGE_ROLES.error) {
        wrapper.classList.add("aisp2-chat-message-assistant");
        wrapper.classList.add("aisp2-chat-message-error");
    } else {
        wrapper.classList.add("aisp2-chat-message-assistant");
    }

    const paragraph = document.createElement("p");

    paragraph.innerHTML = aisp2RenderMarkdownLite(
        message.content || "",
    );

    wrapper.appendChild(paragraph);

    return wrapper;
}


function aisp2RenderMarkdownLite(value) {
    const escaped = aisp2EscapeHtml(value);

    return escaped
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");
}


function aisp2ScrollMessagesToBottom(messagesElement) {
    if (!messagesElement) {
        return;
    }

    messagesElement.scrollTop = messagesElement.scrollHeight;
}


/* ============================================================
SECTION 09 - INTENT DETECTION
============================================================ */

function aisp2DetectIntent(rawText) {
    const text = aisp2NormalizeText(rawText).toLowerCase();

    if (!text) {
        return {
            intent: AISP2_INTENTS.unknown,
            entities: {},
        };
    }

    if (
        text.includes("health")
        || text.includes("api online")
        || text.includes("api healthy")
        || text.includes("is the api")
    ) {
        return {
            intent: AISP2_INTENTS.health,
            entities: {},
        };
    }

    if (
        text.includes("database")
        || text.includes("db connected")
        || text.includes("is the database")
    ) {
        return {
            intent: AISP2_INTENTS.database,
            entities: {},
        };
    }

    if (
        text.includes("warehouse")
        || text.includes("how many teams")
        || text.includes("how many players")
        || text.includes("loaded")
        || text.includes("synced")
    ) {
        return {
            intent: AISP2_INTENTS.warehouse,
            entities: {},
        };
    }

    if (
        text.includes("all teams")
        || text.includes("show teams")
        || text.includes("list teams")
        || text === "teams"
    ) {
        return {
            intent: AISP2_INTENTS.teams,
            entities: {},
        };
    }

    if (
        text.includes("search for")
        || text.includes("find player")
        || text.includes("show me")
        || text.includes("look up")
    ) {
        const extractedPlayer = aisp2ExtractPlayerName(rawText);

        if (extractedPlayer) {
            return {
                intent: AISP2_INTENTS.playerSearch,
                entities: {
                    playerName: extractedPlayer,
                },
            };
        }
    }

    if (
        text.includes("predict")
        || text.includes("probability")
        || text.includes("home run")
        || text.includes("homer")
        || text.includes("hit a")
    ) {
        return {
            intent: AISP2_INTENTS.predictionSetup,
            entities: {
                playerName: aisp2ExtractPlayerName(rawText),
                outcome: aisp2ExtractOutcome(rawText),
            },
        };
    }

    if (
        text.includes("help")
        || text.includes("what can you do")
    ) {
        return {
            intent: AISP2_INTENTS.help,
            entities: {},
        };
    }

    return {
        intent: AISP2_INTENTS.unknown,
        entities: {},
    };
}


function aisp2ExtractPlayerName(rawText) {
    const text = aisp2NormalizeText(rawText);

    const patterns = [
        /search for (.+)$/i,
        /find player (.+)$/i,
        /show me (.+)$/i,
        /look up (.+)$/i,
        /predict (.+?) (home run|homer|hit|single|double|triple|rbi|walk|strikeout)/i,
    ];

    for (const pattern of patterns) {
        const match = text.match(pattern);

        if (match && match[1]) {
            return aisp2NormalizeText(match[1]);
        }
    }

    return "";
}


function aisp2ExtractOutcome(rawText) {
    const text = aisp2NormalizeText(rawText).toLowerCase();

    if (text.includes("home run") || text.includes("homer")) {
        return AISP2_OUTCOME_MARKETS.find((item) => item.id === "home_run");
    }

    if (text.includes("double")) {
        return AISP2_OUTCOME_MARKETS.find((item) => item.id === "double");
    }

    if (text.includes("triple")) {
        return AISP2_OUTCOME_MARKETS.find((item) => item.id === "triple");
    }

    if (text.includes("single")) {
        return AISP2_OUTCOME_MARKETS.find((item) => item.id === "single");
    }

    if (text.includes("rbi")) {
        return AISP2_OUTCOME_MARKETS.find((item) => item.id === "rbi");
    }

    if (text.includes("walk")) {
        return AISP2_OUTCOME_MARKETS.find((item) => item.id === "walk");
    }

    if (text.includes("strikeout") || text.includes("strikes out")) {
        return AISP2_OUTCOME_MARKETS.find((item) => item.id === "strikeout");
    }

    return AISP2_OUTCOME_MARKETS[0];
}
/* ============================================================
SECTION 10 - RESPONSE FORMATTERS
============================================================ */

function aisp2FormatHealthResponse(healthPayload, databasePayload) {
    const apiStatus = healthPayload?.status || "unknown";
    const serviceName = healthPayload?.service || "aisp-baseball-api";
    const databaseConnected = Boolean(
        databasePayload?.database
        || healthPayload?.database
    );

    return [
        "**AISP2 System Health**",
        "",
        `API Service: **${serviceName}**`,
        `API Status: **${apiStatus}**`,
        `Database Connected: **${databaseConnected ? "Yes" : "No"}**`,
        "",
        databaseConnected
            ? "The backend is reachable and the database connection is active."
            : "The backend responded, but the database connection may need attention.",
    ].join("\n");
}


function aisp2FormatDatabaseResponse(databasePayload, summaryPayload) {
    const databaseConnected = Boolean(databasePayload?.database);

    const teams = summaryPayload?.teams ?? 0;
    const players = summaryPayload?.players ?? 0;
    const games = summaryPayload?.games ?? 0;
    const gamePredictions = summaryPayload?.game_predictions ?? 0;
    const playerPredictions = summaryPayload?.player_predictions ?? 0;
    const statcastEvents = summaryPayload?.statcast_events ?? 0;

    return [
        "**AISP2 Database Status**",
        "",
        `Database Connected: **${databaseConnected ? "Yes" : "No"}**`,
        "",
        "**Current Warehouse Counts**",
        `Teams: **${aisp2FormatCount(teams)}**`,
        `Players: **${aisp2FormatCount(players)}**`,
        `Games: **${aisp2FormatCount(games)}**`,
        `Game Predictions: **${aisp2FormatCount(gamePredictions)}**`,
        `Player Predictions: **${aisp2FormatCount(playerPredictions)}**`,
        `Statcast Events: **${aisp2FormatCount(statcastEvents)}**`,
    ].join("\n");
}


function aisp2FormatWarehouseResponse(summaryPayload, auditPayload) {
    const teams = summaryPayload?.teams ?? auditPayload?.teams ?? 0;
    const players = summaryPayload?.players ?? auditPayload?.players ?? 0;
    const games = summaryPayload?.games ?? 0;
    const rosterEntries = auditPayload?.roster_entries ?? 0;
    const playerStats = auditPayload?.player_stats ?? 0;
    const statcastEvents = (
        summaryPayload?.statcast_events
        ?? auditPayload?.statcast_events
        ?? 0
    );
    const warehouseScore = auditPayload?.warehouse_score ?? 0;
    const status = auditPayload?.status || "unknown";

    return [
        "**AISP2 Warehouse Status**",
        "",
        `Warehouse Score: **${warehouseScore}/100**`,
        `Warehouse Status: **${status}**`,
        "",
        "**Loaded Data**",
        `Teams: **${aisp2FormatCount(teams)}**`,
        `Players: **${aisp2FormatCount(players)}**`,
        `Roster Entries: **${aisp2FormatCount(rosterEntries)}**`,
        `Player Season Stats: **${aisp2FormatCount(playerStats)}**`,
        `Games: **${aisp2FormatCount(games)}**`,
        `Statcast Events: **${aisp2FormatCount(statcastEvents)}**`,
        "",
        teams > 0 && players > 0
            ? "AISP2 has enough team/player data to support real browsing and prediction setup."
            : "AISP2 still needs team and roster sync before the workspace can fully leave demo mode.",
    ].join("\n");
}


function aisp2FormatTeamsResponse(teams) {
    if (!Array.isArray(teams) || teams.length === 0) {
        return [
            "**MLB Teams**",
            "",
            "No teams were returned from the API.",
            "",
            "Next step: run the team sync endpoint from the Warehouse/Admin tools.",
        ].join("\n");
    }

    const lines = teams.map((team, index) => {
        const name = team.name || "Unknown Team";
        const abbreviation = team.abbreviation || "N/A";
        const league = team.league || "Unknown League";
        const division = team.division || "Unknown Division";

        return `${index + 1}. **${name}** (${abbreviation}) — ${league}, ${division}`;
    });

    return [
        `**MLB Teams Loaded: ${teams.length}**`,
        "",
        ...lines,
        "",
        "You can ask: **show me Corbin Carroll**, **find Aaron Judge**, or **predict a home run for Shohei Ohtani**.",
    ].join("\n");
}


function aisp2FormatPlayerSearchResponse(players, query) {
    if (!Array.isArray(players) || players.length === 0) {
        return [
            `**Player Search: ${query}**`,
            "",
            "No players were found.",
            "",
            "If this player should exist, run roster sync first, then search again.",
        ].join("\n");
    }

    const lines = players.map((player, index) => {
        const name = player.name || "Unknown Player";
        const team = player.team || "Unknown Team";
        const position = player.position || "Unknown Position";
        const bats = player.bats || "N/A";
        const throws = player.throws || "N/A";

        return [
            `${index + 1}. **${name}**`,
            `   Team: ${team}`,
            `   Position: ${position}`,
            `   Bats/Throws: ${bats}/${throws}`,
        ].join("\n");
    });

    return [
        `**Player Search Results: ${query}**`,
        "",
        ...lines,
        "",
        "Select one of these players in the workspace, or ask for a prediction outcome like **home run**, **single**, **double**, **triple**, **RBI**, **walk**, or **strikeout**.",
    ].join("\n");
}


function aisp2FormatPredictionSetupResponse(setup) {
    const player = setup.player || {};
    const team = setup.team || {};
    const outcome = setup.outcome || AISP2_OUTCOME_MARKETS[0];

    return [
        "**Prediction Setup Ready**",
        "",
        `Team: **${team.name || player.team || "Not selected"}**`,
        `Player: **${player.name || "Not selected"}**`,
        `Position: **${player.position || "Unknown"}**`,
        `Outcome: **${outcome.label || "Unknown Outcome"}**`,
        "",
        "**Current Status**",
        "The UI can now prepare a real prediction request.",
        "",
        "**Next Backend Target**",
        "`POST /predict/player`",
        "",
        "Once the prediction endpoint is added, this card will show probability, confidence, model name, and reasoning.",
    ].join("\n");
}


function aisp2FormatHelpResponse() {
    return [
        "**AISP2 Baseball Intelligence Commands**",
        "",
        "Try asking:",
        "",
        "1. **Is the API online and healthy?**",
        "2. **Is the database connected?**",
        "3. **How many teams are loaded?**",
        "4. **Show me all MLB teams**",
        "5. **Search for Corbin Carroll**",
        "6. **Find Aaron Judge**",
        "7. **Predict Corbin Carroll home run**",
        "8. **What data is synced?**",
        "",
        "AISP2 will route these questions to real API calls where available.",
    ].join("\n");
}


function aisp2FormatUnknownResponse() {
    return [
        "I can help with AISP2 baseball data, teams, players, health checks, warehouse status, and prediction setup.",
        "",
        "Try asking:",
        "",
        "**Show me all MLB teams**",
        "**Search for Corbin Carroll**",
        "**Is the database connected?**",
        "**How many players are loaded?**",
    ].join("\n");
}


/* ============================================================
SECTION 11 - WORKSPACE CORE CLASS
============================================================ */

class Aisp2ChatWorkspace {
    constructor(options = {}) {
        this.options = options;

        this.state = this.loadInitialState();

        this.dom = new Aisp2DomCache();

        this.api = new Aisp2ApiClient(
            this.state.apiBaseUrl,
        );

        this.isBootstrapped = false;

        this.boundHandleSubmit = this.handleSubmit.bind(this);
        this.boundHandleCollapse = this.handleCollapse.bind(this);
        this.boundHandleFullscreen = this.handleFullscreen.bind(this);
        this.boundHandleClose = this.handleClose.bind(this);
        this.boundHandleLauncher = this.handleLauncher.bind(this);
        this.boundHandleInputKeydown = this.handleInputKeydown.bind(this);

        this.dragSession = null;
        this.resizeSession = null;
    }

    loadInitialState() {
        const defaultState = buildDefaultAisp2WorkspaceState();

        const savedState = aisp2ReadStorage(
            AISP2_STORAGE_KEYS.workspaceState,
            null,
        );

        if (!savedState || typeof savedState !== "object") {
            return defaultState;
        }

        return this.mergeState(
            defaultState,
            savedState,
        );
    }

    mergeState(defaultState, savedState) {
        return {
            ...defaultState,
            ...savedState,

            ui: {
                ...defaultState.ui,
                ...(savedState.ui || {}),
            },

            drag: {
                ...defaultState.drag,
                ...(savedState.drag || {}),
            },

            resize: {
                ...defaultState.resize,
                ...(savedState.resize || {}),
            },

            data: {
                ...defaultState.data,
                ...(savedState.data || {}),
            },

            conversation: {
                ...defaultState.conversation,
                ...(savedState.conversation || {}),
                messages: (
                    savedState.conversation?.messages
                    || defaultState.conversation.messages
                ),
            },
        };
    }

    saveState() {
        aisp2WriteStorage(
            AISP2_STORAGE_KEYS.workspaceState,
            this.state,
        );
    }

    bootstrap() {
        this.dom.query();

        if (!this.dom.isReady()) {
            console.warn(
                "AISP2 chat workspace shell not found. Bootstrap skipped.",
            );

            return false;
        }

        this.applyPersistedLayout();
        this.applyUiState();
        this.renderConversation();
        this.bindEvents();
        this.initializeDrag();
        this.initializeResize();

        this.state.ui.isBootstrapped = true;
        this.isBootstrapped = true;

        this.saveState();

        this.runStartupChecks();

        return true;
    }

    bindEvents() {
        if (this.dom.form) {
            this.dom.form.addEventListener(
                "submit",
                this.boundHandleSubmit,
            );
        }

        if (this.dom.collapse) {
            this.dom.collapse.addEventListener(
                "click",
                this.boundHandleCollapse,
            );
        }

        if (this.dom.fullscreen) {
            this.dom.fullscreen.addEventListener(
                "click",
                this.boundHandleFullscreen,
            );
        }

        if (this.dom.close) {
            this.dom.close.addEventListener(
                "click",
                this.boundHandleClose,
            );
        }

        if (this.dom.launcher) {
            this.dom.launcher.addEventListener(
                "click",
                this.boundHandleLauncher,
            );
        }

        if (this.dom.input) {
            this.dom.input.addEventListener(
                "keydown",
                this.boundHandleInputKeydown,
            );
        }
    }

    destroy() {
        if (this.dom.form) {
            this.dom.form.removeEventListener(
                "submit",
                this.boundHandleSubmit,
            );
        }

        if (this.dom.collapse) {
            this.dom.collapse.removeEventListener(
                "click",
                this.boundHandleCollapse,
            );
        }

        if (this.dom.fullscreen) {
            this.dom.fullscreen.removeEventListener(
                "click",
                this.boundHandleFullscreen,
            );
        }

        if (this.dom.close) {
            this.dom.close.removeEventListener(
                "click",
                this.boundHandleClose,
            );
        }

        if (this.dom.launcher) {
            this.dom.launcher.removeEventListener(
                "click",
                this.boundHandleLauncher,
            );
        }

        if (this.dom.input) {
            this.dom.input.removeEventListener(
                "keydown",
                this.boundHandleInputKeydown,
            );
        }

        this.isBootstrapped = false;
    }
}


/* ============================================================
SECTION 12 - CONVERSATION METHODS
============================================================ */

Aisp2ChatWorkspace.prototype.addMessage = function addMessage(
    role,
    content,
    metadata = {},
) {
    const cleanContent = aisp2NormalizeText(content);

    if (!cleanContent) {
        return null;
    }

    const message = {
        role,
        content: cleanContent,
        createdAt: aisp2NowIso(),
        metadata,
    };

    this.state.conversation.messages.push(message);

    if (this.state.conversation.messages.length > 200) {
        this.state.conversation.messages = (
            this.state.conversation.messages.slice(-200)
        );
    }

    this.saveState();
    this.renderMessage(message);

    return message;
};


Aisp2ChatWorkspace.prototype.addAssistantMessage = function addAssistantMessage(
    content,
    metadata = {},
) {
    return this.addMessage(
        AISP2_MESSAGE_ROLES.assistant,
        content,
        metadata,
    );
};


Aisp2ChatWorkspace.prototype.addUserMessage = function addUserMessage(
    content,
    metadata = {},
) {
    return this.addMessage(
        AISP2_MESSAGE_ROLES.user,
        content,
        metadata,
    );
};


Aisp2ChatWorkspace.prototype.addErrorMessage = function addErrorMessage(
    content,
    metadata = {},
) {
    return this.addMessage(
        AISP2_MESSAGE_ROLES.error,
        content,
        metadata,
    );
};


Aisp2ChatWorkspace.prototype.renderConversation = function renderConversation() {
    if (!this.dom.messages) {
        return;
    }

    this.dom.messages.innerHTML = "";

    this.state.conversation.messages.forEach((message) => {
        this.renderMessage(message);
    });

    aisp2ScrollMessagesToBottom(
        this.dom.messages,
    );
};


Aisp2ChatWorkspace.prototype.renderMessage = function renderMessage(message) {
    if (!this.dom.messages) {
        return;
    }

    const element = aisp2BuildMessageElement(message);

    this.dom.messages.appendChild(element);

    aisp2ScrollMessagesToBottom(
        this.dom.messages,
    );
};


/* ============================================================
SECTION 13 - USER INPUT HANDLERS
============================================================ */

Aisp2ChatWorkspace.prototype.handleSubmit = async function handleSubmit(event) {
    event.preventDefault();

    if (!this.dom.input) {
        return;
    }

    const userText = aisp2NormalizeText(
        this.dom.input.value,
    );

    if (!userText) {
        return;
    }

    this.dom.input.value = "";

    this.addUserMessage(
        userText,
        {
            source: "chat_form",
        },
    );

    await this.processUserMessage(userText);
};


Aisp2ChatWorkspace.prototype.handleInputKeydown = function handleInputKeydown(event) {
    if (
        event.key === "Enter"
        && !event.shiftKey
    ) {
        event.preventDefault();

        if (this.dom.form) {
            this.dom.form.requestSubmit();
        }
    }
};


/* ============================================================
SECTION 14 - INTENT ROUTER
============================================================ */

Aisp2ChatWorkspace.prototype.processUserMessage = async function processUserMessage(
    userText
) {
    const detected = aisp2DetectIntent(userText);

    try {
        if (detected.intent === AISP2_INTENTS.health) {
            await this.handleHealthIntent();
            return;
        }

        if (detected.intent === AISP2_INTENTS.database) {
            await this.handleDatabaseIntent();
            return;
        }

        if (detected.intent === AISP2_INTENTS.warehouse) {
            await this.handleWarehouseIntent();
            return;
        }

        if (detected.intent === AISP2_INTENTS.teams) {
            await this.handleTeamsIntent();
            return;
        }

        if (detected.intent === AISP2_INTENTS.playerSearch) {
            await this.handlePlayerSearchIntent(
                detected.entities.playerName
            );
            return;
        }

        if (detected.intent === AISP2_INTENTS.predictionSetup) {
            await this.handlePredictionSetupIntent(
                detected.entities
            );
            return;
        }

        if (detected.intent === AISP2_INTENTS.help) {
            this.addAssistantMessage(
                aisp2FormatHelpResponse(),
                {
                    intent: detected.intent,
                }
            );
            return;
        }

        const chatPayload = await this.api.sendChatMessage(userText);

        this.addAssistantMessage(
            chatPayload.reply || "AISP2 processed the request, but no reply was returned.",
            {
                intent: chatPayload.intent || detected.intent,
                backend_chat: true,
                context: chatPayload.context || null,
                nlu: chatPayload.nlu || null,
                memory: chatPayload.memory || null,
            }
        );
    } catch (error) {
        this.handleIntentError(
            error,
            detected
        );
    }
};
/* ============================================================
SECTION 15 - HEALTH / DATABASE / WAREHOUSE INTENTS
============================================================ */

Aisp2ChatWorkspace.prototype.handleHealthIntent = async function handleHealthIntent() {
    this.addAssistantMessage(
        "Checking AISP2 API health...",
        {
            intent: AISP2_INTENTS.health,
            transient: true,
        },
    );

    const health = await this.api.getHealth();
    const database = await this.api.getDatabaseHealth();

    this.state.data.health = health;
    this.state.data.database = database;

    this.saveState();

    this.addAssistantMessage(
        aisp2FormatHealthResponse(
            health,
            database,
        ),
        {
            intent: AISP2_INTENTS.health,
            apiPayload: {
                health,
                database,
            },
        },
    );
};


Aisp2ChatWorkspace.prototype.handleDatabaseIntent = async function handleDatabaseIntent() {
    const database = await this.api.getDatabaseHealth();
    const summary = await this.api.getWarehouseSummary();

    this.state.data.database = database;
    this.state.data.warehouse = summary;

    this.saveState();

    this.addAssistantMessage(
        aisp2FormatDatabaseResponse(
            database,
            summary,
        ),
        {
            intent: AISP2_INTENTS.database,
            apiPayload: {
                database,
                summary,
            },
        },
    );
};


Aisp2ChatWorkspace.prototype.handleWarehouseIntent = async function handleWarehouseIntent() {
    const summary = await this.api.getWarehouseSummary();

    let audit = null;

    try {
        audit = await this.api.getWarehouseAudit();
    } catch (error) {
        audit = {
            warehouse_score: 0,
            status: "audit_endpoint_unavailable",
        };
    }

    this.state.data.warehouse = {
        summary,
        audit,
    };

    this.saveState();

    this.addAssistantMessage(
        aisp2FormatWarehouseResponse(
            summary,
            audit,
        ),
        {
            intent: AISP2_INTENTS.warehouse,
            apiPayload: {
                summary,
                audit,
            },
        },
    );
};


/* ============================================================
SECTION 16 - TEAM INTENTS
============================================================ */

Aisp2ChatWorkspace.prototype.handleTeamsIntent = async function handleTeamsIntent() {
    const teams = await this.loadTeams();

    this.addAssistantMessage(
        aisp2FormatTeamsResponse(teams),
        {
            intent: AISP2_INTENTS.teams,
            teamCount: teams.length,
        },
    );
};


Aisp2ChatWorkspace.prototype.loadTeams = async function loadTeams(
    forceRefresh = false,
) {
    if (
        !forceRefresh
        && Array.isArray(this.state.data.teams)
        && this.state.data.teams.length > 0
    ) {
        return this.state.data.teams;
    }

    const teams = await this.api.getTeams();

    const safeTeams = Array.isArray(teams)
        ? teams
        : [];

    this.state.data.teams = safeTeams;

    if (
        !this.state.data.selectedTeam
        && safeTeams.length > 0
    ) {
        this.state.data.selectedTeam = safeTeams[0];
    }

    this.saveState();

    return safeTeams;
};


Aisp2ChatWorkspace.prototype.selectTeamByName = function selectTeamByName(
    teamName,
) {
    const normalizedTarget = aisp2NormalizeText(
        teamName,
    ).toLowerCase();

    const team = this.state.data.teams.find((item) => {
        const name = aisp2NormalizeText(item.name).toLowerCase();
        const abbreviation = aisp2NormalizeText(item.abbreviation).toLowerCase();

        return (
            name === normalizedTarget
            || abbreviation === normalizedTarget
            || name.includes(normalizedTarget)
        );
    });

    if (team) {
        this.state.data.selectedTeam = team;

        aisp2WriteStorage(
            AISP2_STORAGE_KEYS.selectedTeam,
            team,
        );

        this.saveState();
    }

    return team || null;
};


/* ============================================================
SECTION 17 - PLAYER INTENTS
============================================================ */

Aisp2ChatWorkspace.prototype.handlePlayerSearchIntent = async function handlePlayerSearchIntent(
    playerName,
) {
    const cleanPlayerName = aisp2NormalizeText(playerName);

    if (!cleanPlayerName) {
        this.addAssistantMessage(
            "Please give me a player name to search.",
            {
                intent: AISP2_INTENTS.playerSearch,
            },
        );
        return;
    }

    const players = await this.searchPlayers(
        cleanPlayerName,
    );

    this.addAssistantMessage(
        aisp2FormatPlayerSearchResponse(
            players,
            cleanPlayerName,
        ),
        {
            intent: AISP2_INTENTS.playerSearch,
            playerQuery: cleanPlayerName,
            resultCount: players.length,
        },
    );
};


Aisp2ChatWorkspace.prototype.searchPlayers = async function searchPlayers(
    query,
) {
    const players = await this.api.searchPlayers(query);

    const safePlayers = Array.isArray(players)
        ? players
        : [];

    this.state.data.players = safePlayers;

    if (safePlayers.length > 0) {
        this.state.data.selectedPlayer = safePlayers[0];

        aisp2WriteStorage(
            AISP2_STORAGE_KEYS.selectedPlayer,
            safePlayers[0],
        );
    }

    this.saveState();

    return safePlayers;
};


Aisp2ChatWorkspace.prototype.selectPlayerByName = function selectPlayerByName(
    playerName,
) {
    const normalizedTarget = aisp2NormalizeText(
        playerName,
    ).toLowerCase();

    const player = this.state.data.players.find((item) => {
        const name = aisp2NormalizeText(item.name).toLowerCase();

        return (
            name === normalizedTarget
            || name.includes(normalizedTarget)
        );
    });

    if (player) {
        this.state.data.selectedPlayer = player;

        aisp2WriteStorage(
            AISP2_STORAGE_KEYS.selectedPlayer,
            player,
        );

        this.saveState();
    }

    return player || null;
};

/* ============================================================
SECTION 18 - PREDICTION SETUP INTENTS
============================================================ */

Aisp2ChatWorkspace.prototype.handlePredictionSetupIntent = async function handlePredictionSetupIntent(
    entities = {},
) {
    const requestedPlayerName = aisp2NormalizeText(
        entities.playerName || "",
    );

    const requestedOutcome = (
        entities.outcome
        || this.state.data.selectedOutcome
        || AISP2_OUTCOME_MARKETS[0]
    );

    let selectedPlayer = this.state.data.selectedPlayer;

    if (requestedPlayerName) {
        const players = await this.searchPlayers(
            requestedPlayerName,
        );

        if (players.length > 0) {
            selectedPlayer = players[0];
            this.state.data.selectedPlayer = selectedPlayer;
        }
    }

    if (!selectedPlayer) {
        this.addAssistantMessage(
            [
                "**Prediction Setup Needs A Player**",
                "",
                "I need a real player from the database before I can prepare a probability setup.",
                "",
                "Try:",
                "**Search for Corbin Carroll**",
                "**Search for Aaron Judge**",
                "**Search for Shohei Ohtani**",
            ].join("\n"),
            {
                intent: AISP2_INTENTS.predictionSetup,
                status: "missing_player",
            },
        );

        return;
    }

    let selectedTeam = this.state.data.selectedTeam;

    if (!selectedTeam) {
        const teams = await this.loadTeams();

        selectedTeam = teams.find((team) => {
            return (
                team.name === selectedPlayer.team
                || team.abbreviation === selectedPlayer.team
            );
        }) || teams[0] || null;

        this.state.data.selectedTeam = selectedTeam;
    }

    this.state.data.selectedOutcome = requestedOutcome;

    const predictionSetup = {
        status: "ready_for_backend_prediction_endpoint",
        player: selectedPlayer,
        team: selectedTeam,
        outcome: requestedOutcome,
        requestedAt: aisp2NowIso(),
        backendEndpoint: "/predict/player",
        backendReady: false,
        modelLayer: "pending",
        probability: null,
        confidence: null,
        reasoning: [
            "recent player performance",
            "season stat profile",
            "team context",
            "opponent context",
            "Statcast trends",
            "future model output",
        ],
    };

    this.state.data.lastPredictionSetup = predictionSetup;

    aisp2WriteStorage(
        AISP2_STORAGE_KEYS.selectedPrediction,
        predictionSetup,
    );

    this.saveState();

    this.addAssistantMessage(
        aisp2FormatPredictionSetupResponse(
            predictionSetup,
        ),
        {
            intent: AISP2_INTENTS.predictionSetup,
            predictionSetup,
        },
    );

    this.renderPredictionPanel();
};


/* ============================================================
SECTION 19 - ENHANCED UI CARD RENDERING HELPERS
============================================================ */

function aisp2CreateCardElement(title, bodyHtml, options = {}) {
    const card = document.createElement("div");

    card.classList.add("aisp2-workspace-card");

    if (options.variant) {
        card.classList.add(
            `aisp2-workspace-card-${options.variant}`,
        );
    }

    const heading = document.createElement("div");
    heading.classList.add("aisp2-workspace-card-heading");
    heading.textContent = title;

    const body = document.createElement("div");
    body.classList.add("aisp2-workspace-card-body");
    body.innerHTML = bodyHtml;

    card.appendChild(heading);
    card.appendChild(body);

    return card;
}


function aisp2CreateButtonElement(label, onClick, options = {}) {
    const button = document.createElement("button");

    button.type = "button";
    button.classList.add("aisp2-workspace-button");

    if (options.variant) {
        button.classList.add(
            `aisp2-workspace-button-${options.variant}`,
        );
    }

    button.textContent = label;

    button.addEventListener(
        "click",
        onClick,
    );

    return button;
}


function aisp2CreateSelectElement(options, selectedValue, onChange) {
    const select = document.createElement("select");

    select.classList.add("aisp2-workspace-select");

    options.forEach((option) => {
        const optionElement = document.createElement("option");

        optionElement.value = option.value;
        optionElement.textContent = option.label;

        if (option.value === selectedValue) {
            optionElement.selected = true;
        }

        select.appendChild(optionElement);
    });

    select.addEventListener(
        "change",
        (event) => {
            onChange(event.target.value);
        },
    );

    return select;
}


function aisp2CreateTextInputElement(value, placeholder, onInput) {
    const input = document.createElement("input");

    input.type = "text";
    input.classList.add("aisp2-workspace-text-input");
    input.value = value || "";
    input.placeholder = placeholder || "";

    input.addEventListener(
        "input",
        (event) => {
            onInput(event.target.value);
        },
    );

    return input;
}


/* ============================================================
SECTION 20 - WORKSPACE PANEL INJECTION
============================================================ */

Aisp2ChatWorkspace.prototype.ensureWorkspacePanels = function ensureWorkspacePanels() {
    if (!this.dom.window) {
        return null;
    }

    let panelHost = this.dom.window.querySelector(
        "[data-aisp2-workspace-panels]",
    );

    if (panelHost) {
        return panelHost;
    }

    panelHost = document.createElement("div");
    panelHost.classList.add("aisp2-workspace-panels");
    panelHost.setAttribute(
        "data-aisp2-workspace-panels",
        "true",
    );

    const tabs = document.createElement("div");
    tabs.classList.add("aisp2-workspace-tabs");
    tabs.setAttribute(
        "data-aisp2-workspace-tabs",
        "true",
    );

    const content = document.createElement("div");
    content.classList.add("aisp2-workspace-tab-content");
    content.setAttribute(
        "data-aisp2-workspace-tab-content",
        "true",
    );

    panelHost.appendChild(tabs);
    panelHost.appendChild(content);

    const chatBody = this.dom.window.querySelector(".aisp2-chat-body");

    if (chatBody) {
        chatBody.prepend(panelHost);
    }

    this.renderWorkspaceTabs();

    return panelHost;
};


Aisp2ChatWorkspace.prototype.renderWorkspaceTabs = function renderWorkspaceTabs() {
    const panelHost = this.ensureWorkspacePanels();

    if (!panelHost) {
        return;
    }

    const tabs = panelHost.querySelector(
        "[data-aisp2-workspace-tabs]",
    );

    if (!tabs) {
        return;
    }

    tabs.innerHTML = "";

    const tabDefinitions = [
        {
            id: AISP2_TABS.chat,
            label: "Chat",
        },
        {
            id: AISP2_TABS.teams,
            label: "Teams",
        },
        {
            id: AISP2_TABS.players,
            label: "Players",
        },
        {
            id: AISP2_TABS.predictions,
            label: "Predictions",
        },
        {
            id: AISP2_TABS.system,
            label: "System",
        },
    ];

    tabDefinitions.forEach((tab) => {
        const button = document.createElement("button");

        button.type = "button";
        button.classList.add("aisp2-workspace-tab");
        button.textContent = tab.label;

        if (this.state.ui.activeTab === tab.id) {
            button.classList.add("is-active");
        }

        button.addEventListener(
            "click",
            () => {
                this.setActiveTab(tab.id);
            },
        );

        tabs.appendChild(button);
    });

    this.renderActiveTabContent();
};


Aisp2ChatWorkspace.prototype.setActiveTab = function setActiveTab(tabId) {
    this.state.ui.activeTab = tabId;

    aisp2WriteStorage(
        AISP2_STORAGE_KEYS.activeTab,
        tabId,
    );

    this.saveState();

    this.renderWorkspaceTabs();
};


Aisp2ChatWorkspace.prototype.renderActiveTabContent = function renderActiveTabContent() {
    const panelHost = this.ensureWorkspacePanels();

    if (!panelHost) {
        return;
    }

    const content = panelHost.querySelector(
        "[data-aisp2-workspace-tab-content]",
    );

    if (!content) {
        return;
    }

    content.innerHTML = "";

    if (this.state.ui.activeTab === AISP2_TABS.chat) {
        this.renderChatTab(content);
        return;
    }

    if (this.state.ui.activeTab === AISP2_TABS.teams) {
        this.renderTeamsTab(content);
        return;
    }

    if (this.state.ui.activeTab === AISP2_TABS.players) {
        this.renderPlayersTab(content);
        return;
    }

    if (this.state.ui.activeTab === AISP2_TABS.predictions) {
        this.renderPredictionTab(content);
        return;
    }

    if (this.state.ui.activeTab === AISP2_TABS.system) {
        this.renderSystemTab(content);
        return;
    }
};


/* ============================================================
SECTION 21 - CHAT TAB
============================================================ */

Aisp2ChatWorkspace.prototype.renderChatTab = function renderChatTab(content) {
    const body = [
        "<p><strong>AISP2 Chat Mode</strong></p>",
        "<p>Ask plain-English baseball questions. This workspace can route team, player, warehouse, and health questions to real backend API routes.</p>",
        "<p><strong>Examples:</strong></p>",
        "<ul>",
        "<li>Show me all MLB teams</li>",
        "<li>Search for Corbin Carroll</li>",
        "<li>Predict Corbin Carroll home run</li>",
        "<li>Is the database connected?</li>",
        "</ul>",
    ].join("");

    content.appendChild(
        aisp2CreateCardElement(
            "Chat Commands",
            body,
            {
                variant: "chat",
            },
        ),
    );
};


/* ============================================================
SECTION 22 - TEAMS TAB
============================================================ */

Aisp2ChatWorkspace.prototype.renderTeamsTab = function renderTeamsTab(content) {
    const wrapper = document.createElement("div");
    wrapper.classList.add("aisp2-team-browser");

    const intro = aisp2CreateCardElement(
        "Team Browser",
        [
            "<p>View and select MLB teams from the live AISP2 backend.</p>",
            `<p>Teams Loaded: <strong>${aisp2FormatCount(this.state.data.teams.length)}</strong></p>`,
        ].join(""),
    );

    const loadButton = aisp2CreateButtonElement(
        "Load Teams",
        async () => {
            await this.handleTeamsIntent();
            this.renderActiveTabContent();
        },
        {
            variant: "primary",
        },
    );

    intro.appendChild(loadButton);
    wrapper.appendChild(intro);

    if (Array.isArray(this.state.data.teams) && this.state.data.teams.length > 0) {
        const teamOptions = this.state.data.teams.map((team) => {
            return {
                value: String(team.team_id),
                label: `${team.name || "Unknown Team"} (${team.abbreviation || "N/A"})`,
            };
        });

        const selectedTeamId = String(
            this.state.data.selectedTeam?.team_id
            || this.state.data.teams[0]?.team_id
            || "",
        );

        const select = aisp2CreateSelectElement(
            teamOptions,
            selectedTeamId,
            (value) => {
                const selected = this.state.data.teams.find((team) => {
                    return String(team.team_id) === String(value);
                });

                if (selected) {
                    this.state.data.selectedTeam = selected;

                    aisp2WriteStorage(
                        AISP2_STORAGE_KEYS.selectedTeam,
                        selected,
                    );

                    this.saveState();
                    this.renderActiveTabContent();
                }
            },
        );

        const selectedTeam = this.state.data.selectedTeam || this.state.data.teams[0];

        const details = [
            `<p><strong>Selected Team:</strong> ${aisp2EscapeHtml(selectedTeam?.name || "None")}</p>`,
            `<p><strong>Abbreviation:</strong> ${aisp2EscapeHtml(selectedTeam?.abbreviation || "N/A")}</p>`,
            `<p><strong>League:</strong> ${aisp2EscapeHtml(selectedTeam?.league || "Unknown")}</p>`,
            `<p><strong>Division:</strong> ${aisp2EscapeHtml(selectedTeam?.division || "Unknown")}</p>`,
            `<p><strong>Venue:</strong> ${aisp2EscapeHtml(selectedTeam?.venue || "Unknown")}</p>`,
        ].join("");

        const teamCard = aisp2CreateCardElement(
            "Select A Team",
            details,
            {
                variant: "team",
            },
        );

        teamCard.prepend(select);

        wrapper.appendChild(teamCard);
    }

    content.appendChild(wrapper);
};


/* ============================================================
SECTION 23 - PLAYERS TAB
============================================================ */

Aisp2ChatWorkspace.prototype.renderPlayersTab = function renderPlayersTab(content) {
    const wrapper = document.createElement("div");
    wrapper.classList.add("aisp2-player-browser");

    const currentQuery = this.state.data.lastPlayerQuery || "";

    const searchCard = aisp2CreateCardElement(
        "Player Browser",
        [
            "<p>Search players from the AISP2 player database in regular English.</p>",
            "<p>Examples: Corbin Carroll, Aaron Judge, Shohei Ohtani, Juan Soto.</p>",
        ].join(""),
    );

    const input = aisp2CreateTextInputElement(
        currentQuery,
        "Type a player name...",
        (value) => {
            this.state.data.lastPlayerQuery = value;
            this.saveState();
        },
    );

    const searchButton = aisp2CreateButtonElement(
        "Search Players",
        async () => {
            const query = aisp2NormalizeText(
                this.state.data.lastPlayerQuery,
            );

            if (!query) {
                this.addAssistantMessage(
                    "Please type a player name first.",
                );
                return;
            }

            await this.handlePlayerSearchIntent(query);
            this.renderActiveTabContent();
        },
        {
            variant: "primary",
        },
    );

    searchCard.appendChild(input);
    searchCard.appendChild(searchButton);

    wrapper.appendChild(searchCard);

    if (Array.isArray(this.state.data.players) && this.state.data.players.length > 0) {
        const playerOptions = this.state.data.players.map((player) => {
            return {
                value: String(player.player_id),
                label: `${player.name || "Unknown Player"} — ${player.team || "Unknown Team"} — ${player.position || "N/A"}`,
            };
        });

        const selectedPlayerId = String(
            this.state.data.selectedPlayer?.player_id
            || this.state.data.players[0]?.player_id
            || "",
        );

        const select = aisp2CreateSelectElement(
            playerOptions,
            selectedPlayerId,
            (value) => {
                const selected = this.state.data.players.find((player) => {
                    return String(player.player_id) === String(value);
                });

                if (selected) {
                    this.state.data.selectedPlayer = selected;

                    aisp2WriteStorage(
                        AISP2_STORAGE_KEYS.selectedPlayer,
                        selected,
                    );

                    this.saveState();
                    this.renderActiveTabContent();
                }
            },
        );

        const selectedPlayer = this.state.data.selectedPlayer || this.state.data.players[0];

        const playerDetails = [
            `<p><strong>Selected Player:</strong> ${aisp2EscapeHtml(selectedPlayer?.name || "None")}</p>`,
            `<p><strong>Team:</strong> ${aisp2EscapeHtml(selectedPlayer?.team || "Unknown")}</p>`,
            `<p><strong>Position:</strong> ${aisp2EscapeHtml(selectedPlayer?.position || "Unknown")}</p>`,
            `<p><strong>Bats:</strong> ${aisp2EscapeHtml(selectedPlayer?.bats || "N/A")}</p>`,
            `<p><strong>Throws:</strong> ${aisp2EscapeHtml(selectedPlayer?.throws || "N/A")}</p>`,
            `<p><strong>Height:</strong> ${aisp2EscapeHtml(selectedPlayer?.height || "N/A")}</p>`,
            `<p><strong>Weight:</strong> ${aisp2EscapeHtml(selectedPlayer?.weight || "N/A")}</p>`,
        ].join("");

        const playerCard = aisp2CreateCardElement(
            "Select A Player",
            playerDetails,
            {
                variant: "player",
            },
        );

        playerCard.prepend(select);

        wrapper.appendChild(playerCard);
    }

    content.appendChild(wrapper);
};

/* ============================================================
SECTION 24 - PREDICTION TAB
============================================================ */

Aisp2ChatWorkspace.prototype.renderPredictionTab = function renderPredictionTab(content) {
    const wrapper = document.createElement("div");
    wrapper.classList.add("aisp2-prediction-builder");

    const selectedTeam = this.state.data.selectedTeam;
    const selectedPlayer = this.state.data.selectedPlayer;
    const selectedOutcome = (
        this.state.data.selectedOutcome
        || AISP2_OUTCOME_MARKETS[0]
    );

    const introCard = aisp2CreateCardElement(
        "Probability Viewer",
        [
            "<p>Select a team, player, and outcome in plain English.</p>",
            "<p>This prepares the request that will eventually connect to the real prediction model endpoint.</p>",
        ].join(""),
        {
            variant: "prediction",
        },
    );

    wrapper.appendChild(introCard);

    const teamLabel = selectedTeam
        ? `${selectedTeam.name || "Unknown Team"} (${selectedTeam.abbreviation || "N/A"})`
        : "No team selected";

    const playerLabel = selectedPlayer
        ? `${selectedPlayer.name || "Unknown Player"} — ${selectedPlayer.team || "Unknown Team"} — ${selectedPlayer.position || "N/A"}`
        : "No player selected";

    const summaryBody = [
        `<p><strong>Selected Team:</strong> ${aisp2EscapeHtml(teamLabel)}</p>`,
        `<p><strong>Selected Player:</strong> ${aisp2EscapeHtml(playerLabel)}</p>`,
        `<p><strong>Selected Outcome:</strong> ${aisp2EscapeHtml(selectedOutcome.label)}</p>`,
    ].join("");

    const summaryCard = aisp2CreateCardElement(
        "Current Prediction Setup",
        summaryBody,
        {
            variant: "summary",
        },
    );

    wrapper.appendChild(summaryCard);

    const outcomeOptions = AISP2_OUTCOME_MARKETS.map((outcome) => {
        return {
            value: outcome.id,
            label: outcome.label,
        };
    });

    const outcomeSelect = aisp2CreateSelectElement(
        outcomeOptions,
        selectedOutcome.id,
        (value) => {
            const selected = AISP2_OUTCOME_MARKETS.find((outcome) => {
                return outcome.id === value;
            });

            if (selected) {
                this.state.data.selectedOutcome = selected;

                this.saveState();

                this.renderActiveTabContent();
            }
        },
    );

    const outcomeCard = aisp2CreateCardElement(
        "Choose Outcome To Predict",
        "<p>Examples: home run, single, double, triple, RBI, walk, strikeout, stolen base, total bases.</p>",
        {
            variant: "outcome",
        },
    );

    outcomeCard.appendChild(outcomeSelect);

    wrapper.appendChild(outcomeCard);

    const prepareButton = aisp2CreateButtonElement(
        "Prepare Probability Prediction",
        async () => {
            await this.handlePredictionSetupIntent({
                playerName: selectedPlayer?.name || "",
                outcome: this.state.data.selectedOutcome,
            });

            this.renderActiveTabContent();
        },
        {
            variant: "primary",
        },
    );

    const buttonCard = aisp2CreateCardElement(
        "Generate Setup",
        [
            "<p>This does not pretend to create a fake probability.</p>",
            "<p>It prepares a clean prediction payload and waits for the real backend model endpoint.</p>",
        ].join(""),
        {
            variant: "action",
        },
    );

    buttonCard.appendChild(prepareButton);

    wrapper.appendChild(buttonCard);

    if (this.state.data.lastPredictionSetup) {
        const setup = this.state.data.lastPredictionSetup;

        const probabilityBody = [
            `<p><strong>Status:</strong> ${aisp2EscapeHtml(setup.status || "pending")}</p>`,
            `<p><strong>Backend Endpoint:</strong> ${aisp2EscapeHtml(setup.backendEndpoint || "/predict/player")}</p>`,
            `<p><strong>Backend Ready:</strong> ${setup.backendReady ? "Yes" : "No"}</p>`,
            `<p><strong>Model Layer:</strong> ${aisp2EscapeHtml(setup.modelLayer || "pending")}</p>`,
            "<hr>",
            "<p><strong>Future Output Fields:</strong></p>",
            "<ul>",
            "<li>Probability</li>",
            "<li>Confidence</li>",
            "<li>Model name</li>",
            "<li>Feature contribution</li>",
            "<li>Plain-English reasoning</li>",
            "</ul>",
        ].join("");

        wrapper.appendChild(
            aisp2CreateCardElement(
                "Prepared Probability Card",
                probabilityBody,
                {
                    variant: "probability",
                },
            ),
        );
    }

    content.appendChild(wrapper);
};


Aisp2ChatWorkspace.prototype.renderPredictionPanel = function renderPredictionPanel() {
    if (this.state.ui.activeTab !== AISP2_TABS.predictions) {
        return;
    }

    this.renderActiveTabContent();
};


/* ============================================================
SECTION 25 - SYSTEM TAB
============================================================ */

Aisp2ChatWorkspace.prototype.renderSystemTab = function renderSystemTab(content) {
    const wrapper = document.createElement("div");
    wrapper.classList.add("aisp2-system-panel");

    const health = this.state.data.health;
    const database = this.state.data.database;
    const warehouse = this.state.data.warehouse;

    const healthBody = [
        `<p><strong>API Base URL:</strong> ${aisp2EscapeHtml(this.api.baseUrl)}</p>`,
        `<p><strong>API Status:</strong> ${aisp2EscapeHtml(health?.status || "Not checked")}</p>`,
        `<p><strong>Database:</strong> ${database?.database ? "Connected" : "Not checked"}</p>`,
        `<p><strong>Workspace Version:</strong> ${aisp2EscapeHtml(AISP2_WORKSPACE_VERSION)}</p>`,
    ].join("");

    const healthCard = aisp2CreateCardElement(
        "System Status",
        healthBody,
        {
            variant: "system",
        },
    );

    const checkHealthButton = aisp2CreateButtonElement(
        "Run Health Check",
        async () => {
            await this.handleHealthIntent();
            this.renderActiveTabContent();
        },
        {
            variant: "primary",
        },
    );

    healthCard.appendChild(checkHealthButton);

    wrapper.appendChild(healthCard);

    const warehouseSummary = warehouse?.summary || warehouse || {};

    const warehouseBody = [
        `<p><strong>Teams:</strong> ${aisp2FormatCount(warehouseSummary.teams || 0)}</p>`,
        `<p><strong>Players:</strong> ${aisp2FormatCount(warehouseSummary.players || 0)}</p>`,
        `<p><strong>Games:</strong> ${aisp2FormatCount(warehouseSummary.games || 0)}</p>`,
        `<p><strong>Game Predictions:</strong> ${aisp2FormatCount(warehouseSummary.game_predictions || 0)}</p>`,
        `<p><strong>Player Predictions:</strong> ${aisp2FormatCount(warehouseSummary.player_predictions || 0)}</p>`,
        `<p><strong>Statcast Events:</strong> ${aisp2FormatCount(warehouseSummary.statcast_events || 0)}</p>`,
    ].join("");

    const warehouseCard = aisp2CreateCardElement(
        "Warehouse Snapshot",
        warehouseBody,
        {
            variant: "warehouse",
        },
    );

    const checkWarehouseButton = aisp2CreateButtonElement(
        "Refresh Warehouse",
        async () => {
            await this.handleWarehouseIntent();
            this.renderActiveTabContent();
        },
        {
            variant: "primary",
        },
    );

    warehouseCard.appendChild(checkWarehouseButton);

    wrapper.appendChild(warehouseCard);

    const apiConfigCard = aisp2CreateCardElement(
        "API Configuration",
        "<p>Use this only if you move the backend to a different Render URL.</p>",
        {
            variant: "config",
        },
    );

    const apiInput = aisp2CreateTextInputElement(
        this.api.baseUrl,
        "https://aisp-baseball-api.onrender.com",
        (value) => {
            this.state.apiBaseUrl = value;
        },
    );

    const saveApiButton = aisp2CreateButtonElement(
        "Save API URL",
        () => {
            this.api.setBaseUrl(
                this.state.apiBaseUrl,
            );

            this.state.apiBaseUrl = this.api.baseUrl;

            this.saveState();

            this.addAssistantMessage(
                `API URL saved as **${this.api.baseUrl}**.`,
                {
                    source: "system_config",
                },
            );

            this.renderActiveTabContent();
        },
        {
            variant: "secondary",
        },
    );

    apiConfigCard.appendChild(apiInput);
    apiConfigCard.appendChild(saveApiButton);

    wrapper.appendChild(apiConfigCard);

    content.appendChild(wrapper);
};


/* ============================================================
SECTION 26 - UI STATE CONTROLS
============================================================ */

Aisp2ChatWorkspace.prototype.applyUiState = function applyUiState() {
    if (!this.dom.root) {
        return;
    }

    this.dom.root.classList.remove(
        "is-collapsed",
        "is-minimized",
        "is-hidden",
        "is-fullscreen",
    );

    if (this.state.ui.state === AISP2_UI_STATES.collapsed) {
        this.dom.root.classList.add("is-collapsed");
    }

    if (this.state.ui.state === AISP2_UI_STATES.minimized) {
        this.dom.root.classList.add("is-minimized");
    }

    if (this.state.ui.state === AISP2_UI_STATES.hidden) {
        this.dom.root.classList.add("is-hidden");
    }

    if (this.state.ui.state === AISP2_UI_STATES.fullscreen) {
        this.dom.root.classList.add("is-fullscreen");
    }

    this.saveState();
};


Aisp2ChatWorkspace.prototype.handleCollapse = function handleCollapse() {
    if (this.state.ui.state === AISP2_UI_STATES.collapsed) {
        this.state.ui.state = AISP2_UI_STATES.open;
    } else {
        this.state.ui.state = AISP2_UI_STATES.collapsed;
    }

    this.applyUiState();
};


Aisp2ChatWorkspace.prototype.handleFullscreen = function handleFullscreen() {
    if (this.state.ui.state === AISP2_UI_STATES.fullscreen) {
        this.state.ui.state = AISP2_UI_STATES.open;
    } else {
        this.state.ui.state = AISP2_UI_STATES.fullscreen;
    }

    this.applyUiState();
};


Aisp2ChatWorkspace.prototype.handleClose = function handleClose() {
    this.state.ui.state = AISP2_UI_STATES.minimized;

    this.applyUiState();
};


Aisp2ChatWorkspace.prototype.handleLauncher = function handleLauncher() {
    this.state.ui.state = AISP2_UI_STATES.open;

    this.applyUiState();
};


/* ============================================================
SECTION 27 - LAYOUT PERSISTENCE
============================================================ */

Aisp2ChatWorkspace.prototype.applyPersistedLayout = function applyPersistedLayout() {
    if (!this.dom.root || !this.dom.window) {
        return;
    }

    const width = this.state.resize.width || 560;
    const height = this.state.resize.height || 680;

    this.dom.window.style.width = `${width}px`;
    this.dom.window.style.height = `${height}px`;

    if (
        typeof this.state.drag.x === "number"
        && typeof this.state.drag.y === "number"
    ) {
        this.dom.root.style.left = `${this.state.drag.x}px`;
        this.dom.root.style.top = `${this.state.drag.y}px`;
        this.dom.root.style.right = "auto";
        this.dom.root.style.bottom = "auto";
    }
};


/* ============================================================
SECTION 28 - STARTUP CHECKS
============================================================ */

Aisp2ChatWorkspace.prototype.runStartupChecks = async function runStartupChecks() {
    try {
        const health = await this.api.getHealth();

        this.state.data.health = health;

        this.saveState();

        if (health?.status && health.status !== "healthy") {
            this.addAssistantMessage(
                [
                    "**Startup Notice**",
                    "",
                    `API responded with status: **${health.status}**`,
                    "",
                    "Some data tools may be limited until the backend is fully healthy.",
                ].join("\n"),
                {
                    source: "startup_check",
                },
            );
        }
    } catch (error) {
        this.state.ui.lastError = {
            message: error.message,
            source: "startup_check",
            createdAt: aisp2NowIso(),
        };

        this.saveState();

        this.addErrorMessage(
            [
                "**Startup API Check Failed**",
                "",
                "The workspace loaded, but the backend API did not respond yet.",
                "",
                "This can happen if Render is waking up. Try again in a moment.",
            ].join("\n"),
            {
                source: "startup_check",
            },
        );
    }
};


/* ============================================================
SECTION 29 - INLINE WORKSPACE CSS EXTENSIONS
============================================================ */

function aisp2InjectWorkspaceStyles() {
    if (document.getElementById("aisp2-chat-workspace-js-styles")) {
        return;
    }

    const style = document.createElement("style");

    style.id = "aisp2-chat-workspace-js-styles";

    style.textContent = `
        .aisp2-workspace-panels {
            margin-bottom: 12px;
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            overflow: hidden;
            background: rgba(2, 6, 23, 0.42);
        }

        .aisp2-workspace-tabs {
            display: flex;
            gap: 4px;
            padding: 8px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
            overflow-x: auto;
        }

        .aisp2-workspace-tab {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 999px;
            padding: 7px 11px;
            background: rgba(15, 23, 42, 0.72);
            color: #cbd5e1;
            cursor: pointer;
            font-size: 0.74rem;
            white-space: nowrap;
        }

        .aisp2-workspace-tab.is-active {
            background: linear-gradient(135deg, #2563eb, #06b6d4);
            color: #ffffff;
            border-color: transparent;
        }

        .aisp2-workspace-tab-content {
            max-height: 260px;
            overflow-y: auto;
            padding: 10px;
        }

        .aisp2-workspace-card {
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 15px;
            background: rgba(15, 23, 42, 0.74);
            padding: 12px;
            margin-bottom: 10px;
            color: #dbeafe;
        }

        .aisp2-workspace-card-heading {
            font-weight: 800;
            font-size: 0.82rem;
            margin-bottom: 8px;
            color: #ffffff;
        }

        .aisp2-workspace-card-body {
            font-size: 0.78rem;
            line-height: 1.45;
            color: #cbd5e1;
        }

        .aisp2-workspace-card-body p {
            margin: 0 0 7px;
        }

        .aisp2-workspace-card-body ul {
            margin: 6px 0 0 18px;
            padding: 0;
        }

        .aisp2-workspace-button {
            margin-top: 8px;
            margin-right: 8px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 11px;
            padding: 8px 12px;
            background: rgba(30, 41, 59, 0.92);
            color: #e2e8f0;
            cursor: pointer;
            font-size: 0.76rem;
            font-weight: 700;
        }

        .aisp2-workspace-button-primary {
            background: linear-gradient(135deg, #2563eb, #06b6d4);
            color: #ffffff;
            border-color: transparent;
        }

        .aisp2-workspace-button-secondary {
            background: rgba(15, 23, 42, 0.94);
        }

        .aisp2-workspace-select,
        .aisp2-workspace-text-input {
            width: 100%;
            margin: 8px 0;
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 12px;
            background: rgba(2, 6, 23, 0.82);
            color: #e5edf8;
            padding: 9px 10px;
            font: inherit;
            font-size: 0.78rem;
            outline: none;
        }

        .aisp2-workspace-select:focus,
        .aisp2-workspace-text-input:focus {
            border-color: rgba(56, 189, 248, 0.7);
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.12);
        }

        .aisp2-chat-message-error {
            border-color: rgba(248, 113, 113, 0.35);
            background: rgba(127, 29, 29, 0.42);
        }

        .aisp2-workspace-card hr {
            border: 0;
            border-top: 1px solid rgba(148, 163, 184, 0.15);
            margin: 10px 0;
        }
    `;

    document.head.appendChild(style);
}

/* ============================================================
SECTION 30 - DRAG BEHAVIOR
============================================================ */

Aisp2ChatWorkspace.prototype.initializeDrag = function initializeDrag() {
    if (!this.dom.root || !this.dom.header) {
        return;
    }

    this.dom.header.addEventListener(
        "pointerdown",
        (event) => {
            this.startDrag(event);
        },
    );
};


Aisp2ChatWorkspace.prototype.startDrag = function startDrag(event) {
    if (
        this.state.ui.state === AISP2_UI_STATES.fullscreen
        || !this.dom.root
    ) {
        return;
    }

    event.preventDefault();

    const rootRect = this.dom.root.getBoundingClientRect();

    this.dragSession = {
        startPointerX: event.clientX,
        startPointerY: event.clientY,
        startLeft: rootRect.left,
        startTop: rootRect.top,
    };

    this.state.drag.isDragging = true;

    document.addEventListener(
        "pointermove",
        this.boundDragMove = this.handleDragMove.bind(this),
    );

    document.addEventListener(
        "pointerup",
        this.boundDragEnd = this.endDrag.bind(this),
        {
            once: true,
        },
    );
};


Aisp2ChatWorkspace.prototype.handleDragMove = function handleDragMove(event) {
    if (!this.dragSession || !this.dom.root) {
        return;
    }

    const deltaX = event.clientX - this.dragSession.startPointerX;
    const deltaY = event.clientY - this.dragSession.startPointerY;

    const nextLeft = this.dragSession.startLeft + deltaX;
    const nextTop = this.dragSession.startTop + deltaY;

    const rootRect = this.dom.root.getBoundingClientRect();

    const maxLeft = window.innerWidth - rootRect.width - 8;
    const maxTop = window.innerHeight - rootRect.height - 8;

    const clampedLeft = aisp2Clamp(
        nextLeft,
        8,
        Math.max(8, maxLeft),
    );

    const clampedTop = aisp2Clamp(
        nextTop,
        8,
        Math.max(8, maxTop),
    );

    this.dom.root.style.left = `${clampedLeft}px`;
    this.dom.root.style.top = `${clampedTop}px`;
    this.dom.root.style.right = "auto";
    this.dom.root.style.bottom = "auto";

    this.state.drag.x = clampedLeft;
    this.state.drag.y = clampedTop;
};


Aisp2ChatWorkspace.prototype.endDrag = function endDrag() {
    this.state.drag.isDragging = false;

    this.dragSession = null;

    document.removeEventListener(
        "pointermove",
        this.boundDragMove,
    );

    this.saveState();
};


/* ============================================================
SECTION 31 - RESIZE BEHAVIOR
============================================================ */

Aisp2ChatWorkspace.prototype.initializeResize = function initializeResize() {
    if (!this.dom.window || !this.dom.resizeHandle) {
        return;
    }

    this.dom.resizeHandle.addEventListener(
        "pointerdown",
        (event) => {
            this.startResize(event);
        }
    );
};


Aisp2ChatWorkspace.prototype.startResize = function startResize(event) {
    if (
        this.state.ui.state === AISP2_UI_STATES.fullscreen
        || !this.dom.window
    ) {
        return;
    }

    event.preventDefault();
    event.stopPropagation();

    const rect = this.dom.window.getBoundingClientRect();

    this.resizeSession = {
        startPointerX: event.clientX,
        startPointerY: event.clientY,
        startWidth: rect.width,
        startHeight: rect.height,
    };

    this.state.resize.isResizing = true;

    document.body.classList.add("aisp2-is-resizing-chat");

    this.boundResizeMove = this.handleResizeMove.bind(this);
    this.boundResizeEnd = this.endResize.bind(this);

    document.addEventListener("pointermove", this.boundResizeMove);
    document.addEventListener("pointerup", this.boundResizeEnd, { once: true });
};


Aisp2ChatWorkspace.prototype.handleResizeMove = function handleResizeMove(event) {
    if (!this.resizeSession || !this.dom.window) {
        return;
    }

    const deltaX = event.clientX - this.resizeSession.startPointerX;
    const deltaY = event.clientY - this.resizeSession.startPointerY;

    const viewportMaxWidth = Math.max(380, window.innerWidth - 24);
    const viewportMaxHeight = Math.max(460, window.innerHeight - 24);

    const nextWidth = this.resizeSession.startWidth + deltaX;
    const nextHeight = this.resizeSession.startHeight + deltaY;

    const clampedWidth = aisp2Clamp(
        nextWidth,
        380,
        Math.min(980, viewportMaxWidth)
    );

    const clampedHeight = aisp2Clamp(
        nextHeight,
        460,
        Math.min(920, viewportMaxHeight)
    );

    this.dom.window.style.width = `${Math.round(clampedWidth)}px`;
    this.dom.window.style.height = `${Math.round(clampedHeight)}px`;

    this.state.resize.width = Math.round(clampedWidth);
    this.state.resize.height = Math.round(clampedHeight);

    this.keepPanelInsideViewport();
};


Aisp2ChatWorkspace.prototype.endResize = function endResize() {
    this.state.resize.isResizing = false;

    this.resizeSession = null;

    document.body.classList.remove("aisp2-is-resizing-chat");

    document.removeEventListener(
        "pointermove",
        this.boundResizeMove
    );

    this.keepPanelInsideViewport();
    this.saveState();
};
/* ============================================================
SECTION 32 - WINDOW AND VIEWPORT SAFETY
============================================================ */

Aisp2ChatWorkspace.prototype.keepPanelInsideViewport = function keepPanelInsideViewport() {
    if (!this.dom.root) {
        return;
    }

    const rect = this.dom.root.getBoundingClientRect();

    if (!rect.width || !rect.height) {
        return;
    }

    const nextLeft = aisp2Clamp(
        rect.left,
        8,
        Math.max(8, window.innerWidth - rect.width - 8),
    );

    const nextTop = aisp2Clamp(
        rect.top,
        8,
        Math.max(8, window.innerHeight - rect.height - 8),
    );

    this.dom.root.style.left = `${nextLeft}px`;
    this.dom.root.style.top = `${nextTop}px`;
    this.dom.root.style.right = "auto";
    this.dom.root.style.bottom = "auto";

    this.state.drag.x = nextLeft;
    this.state.drag.y = nextTop;

    this.saveState();
};


Aisp2ChatWorkspace.prototype.bindViewportSafety = function bindViewportSafety() {
    window.addEventListener(
        "resize",
        () => {
            if (this.state.ui.state !== AISP2_UI_STATES.fullscreen) {
                this.keepPanelInsideViewport();
            }
        },
    );
};


/* ============================================================
SECTION 33 - RESET AND RECOVERY TOOLS
============================================================ */

Aisp2ChatWorkspace.prototype.resetLayout = function resetLayout() {
    this.state.drag.x = null;
    this.state.drag.y = null;

    this.state.resize.width = 560;
    this.state.resize.height = 680;

    this.state.ui.state = AISP2_UI_STATES.open;

    if (this.dom.root) {
        this.dom.root.style.left = "";
        this.dom.root.style.top = "";
        this.dom.root.style.right = "28px";
        this.dom.root.style.bottom = "28px";
    }

    if (this.dom.window) {
        this.dom.window.style.width = "560px";
        this.dom.window.style.height = "680px";
    }

    this.applyUiState();
    this.saveState();
};


Aisp2ChatWorkspace.prototype.clearConversation = function clearConversation() {
    this.state.conversation.messages = [
        {
            role: AISP2_MESSAGE_ROLES.assistant,
            content:
                "Conversation cleared. Ask me about MLB teams, players, health checks, warehouse status, or prediction setup.",
            createdAt: aisp2NowIso(),
            metadata: {
                source: "clear_conversation",
            },
        },
    ];

    this.saveState();
    this.renderConversation();
};


Aisp2ChatWorkspace.prototype.clearCachedBaseballData = function clearCachedBaseballData() {
    this.state.data.teams = [];
    this.state.data.players = [];
    this.state.data.selectedTeam = null;
    this.state.data.selectedPlayer = null;
    this.state.data.lastPredictionSetup = null;

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.selectedTeam,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.selectedPlayer,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.selectedPrediction,
    );

    this.saveState();
    this.renderActiveTabContent();

    this.addAssistantMessage(
        "Cached team/player/prediction data cleared. Load teams or search players again to refresh from the backend.",
        {
            source: "cache_clear",
        },
    );
};


/* ============================================================
SECTION 34 - SYSTEM TAB RECOVERY BUTTONS
============================================================ */

Aisp2ChatWorkspace.prototype.renderRecoveryControls = function renderRecoveryControls() {
    const panelHost = this.ensureWorkspacePanels();

    if (!panelHost) {
        return;
    }

    const content = panelHost.querySelector(
        "[data-aisp2-workspace-tab-content]",
    );

    if (!content) {
        return;
    }

    const recoveryCard = aisp2CreateCardElement(
        "Recovery Tools",
        [
            "<p>Use these if the floating workspace gets stuck, too small, off-screen, or filled with stale cached data.</p>",
        ].join(""),
        {
            variant: "recovery",
        },
    );

    const resetButton = aisp2CreateButtonElement(
        "Reset Layout",
        () => {
            this.resetLayout();
        },
        {
            variant: "secondary",
        },
    );

    const clearConversationButton = aisp2CreateButtonElement(
        "Clear Conversation",
        () => {
            this.clearConversation();
        },
        {
            variant: "secondary",
        },
    );

    const clearDataButton = aisp2CreateButtonElement(
        "Clear Cached Data",
        () => {
            this.clearCachedBaseballData();
        },
        {
            variant: "secondary",
        },
    );

    recoveryCard.appendChild(resetButton);
    recoveryCard.appendChild(clearConversationButton);
    recoveryCard.appendChild(clearDataButton);

    content.appendChild(recoveryCard);
};


/* ============================================================
SECTION 35 - PATCH SYSTEM TAB WITH RECOVERY CONTROLS
============================================================ */

const aisp2OriginalRenderSystemTab = (
    Aisp2ChatWorkspace.prototype.renderSystemTab
);

Aisp2ChatWorkspace.prototype.renderSystemTab = function renderSystemTabWithRecovery(
    content,
) {
    aisp2OriginalRenderSystemTab.call(
        this,
        content,
    );

    this.renderRecoveryControls();
};


/* ============================================================
SECTION 36 - KEYBOARD SHORTCUTS
============================================================ */

Aisp2ChatWorkspace.prototype.bindKeyboardShortcuts = function bindKeyboardShortcuts() {
    document.addEventListener(
        "keydown",
        (event) => {
            const isMac = navigator.platform.toLowerCase().includes("mac");

            const modifierPressed = isMac
                ? event.metaKey
                : event.ctrlKey;

            if (!modifierPressed || !event.shiftKey) {
                return;
            }

            const key = event.key.toLowerCase();

            if (key === "a") {
                event.preventDefault();

                if (this.state.ui.state === AISP2_UI_STATES.minimized) {
                    this.state.ui.state = AISP2_UI_STATES.open;
                } else {
                    this.state.ui.state = AISP2_UI_STATES.minimized;
                }

                this.applyUiState();
            }

            if (key === "f") {
                event.preventDefault();
                this.handleFullscreen();
            }

            if (key === "r") {
                event.preventDefault();
                this.resetLayout();
            }
        },
    );
};


/* ============================================================
SECTION 37 - QUICK ACTION COMMANDS
============================================================ */

Aisp2ChatWorkspace.prototype.runQuickAction = async function runQuickAction(actionId) {
    if (actionId === "health") {
        await this.handleHealthIntent();
        return;
    }

    if (actionId === "warehouse") {
        await this.handleWarehouseIntent();
        return;
    }

    if (actionId === "teams") {
        await this.handleTeamsIntent();
        return;
    }

    if (actionId === "help") {
        this.addAssistantMessage(
            aisp2FormatHelpResponse(),
            {
                source: "quick_action",
            },
        );
        return;
    }
};


Aisp2ChatWorkspace.prototype.renderQuickActions = function renderQuickActions(content) {
    const quickCard = aisp2CreateCardElement(
        "Quick Actions",
        "<p>Run common AISP2 checks without typing a full question.</p>",
        {
            variant: "quick-actions",
        },
    );

    const actions = [
        {
            id: "health",
            label: "Health",
        },
        {
            id: "warehouse",
            label: "Warehouse",
        },
        {
            id: "teams",
            label: "Teams",
        },
        {
            id: "help",
            label: "Help",
        },
    ];

    actions.forEach((action) => {
        quickCard.appendChild(
            aisp2CreateButtonElement(
                action.label,
                async () => {
                    await this.runQuickAction(action.id);
                },
                {
                    variant: "secondary",
                },
            ),
        );
    });

    content.appendChild(quickCard);
};


/* ============================================================
SECTION 38 - PATCH CHAT TAB WITH QUICK ACTIONS
============================================================ */

const aisp2OriginalRenderChatTab = (
    Aisp2ChatWorkspace.prototype.renderChatTab
);

Aisp2ChatWorkspace.prototype.renderChatTab = function renderChatTabWithQuickActions(
    content,
) {
    aisp2OriginalRenderChatTab.call(
        this,
        content,
    );

    this.renderQuickActions(content);
};

/* ============================================================
SECTION 39 - BOOTSTRAP HELPERS
============================================================ */

function aisp2WaitForWorkspaceShell(maxAttempts = 40, intervalMs = 125) {
    return new Promise((resolve) => {
        let attempts = 0;

        const check = () => {
            attempts += 1;

            const root = document.querySelector(AISP2_SELECTORS.root);
            const chatWindow = document.querySelector(AISP2_SELECTORS.window);
            const messages = document.querySelector(AISP2_SELECTORS.messages);
            const form = document.querySelector(AISP2_SELECTORS.form);
            const input = document.querySelector(AISP2_SELECTORS.input);

            if (
                root
                && chatWindow
                && messages
                && form
                && input
            ) {
                resolve(true);
                return;
            }

            if (attempts >= maxAttempts) {
                resolve(false);
                return;
            }

            window.setTimeout(
                check,
                intervalMs,
            );
        };

        check();
    });
}


function aisp2BuildWorkspaceDiagnostics(workspace) {
    return {
        loaded: Boolean(workspace),
        version: AISP2_WORKSPACE_VERSION,
        apiBaseUrl: workspace?.api?.baseUrl || AISP2_DEFAULT_API_BASE_URL,
        uiState: workspace?.state?.ui?.state || null,
        activeTab: workspace?.state?.ui?.activeTab || null,
        messageCount: workspace?.state?.conversation?.messages?.length || 0,
        teamsLoaded: workspace?.state?.data?.teams?.length || 0,
        playersLoaded: workspace?.state?.data?.players?.length || 0,
        selectedTeam: workspace?.state?.data?.selectedTeam || null,
        selectedPlayer: workspace?.state?.data?.selectedPlayer || null,
        lastPredictionSetup: workspace?.state?.data?.lastPredictionSetup || null,
    };
}


/* ============================================================
SECTION 40 - FINAL BOOTSTRAP METHOD PATCH
============================================================ */

const aisp2OriginalBootstrap = (
    Aisp2ChatWorkspace.prototype.bootstrap
);

Aisp2ChatWorkspace.prototype.bootstrap = function bootstrapWithFinalSystems() {
    const result = aisp2OriginalBootstrap.call(this);

    if (!result) {
        return false;
    }

    aisp2InjectWorkspaceStyles();

    this.bindViewportSafety();
    this.bindKeyboardShortcuts();

    this.ensureWorkspacePanels();
    this.renderWorkspaceTabs();

    const hasFinalBootstrapMessage = this.state.conversation.messages.some((message) => {
        return message?.metadata?.source === "final_bootstrap";
    });

    if (!hasFinalBootstrapMessage) {
        this.addAssistantMessage(
            [
                "**AISP2 Workspace Online**",
                "",
                "The floating AI workspace is active across the application.",
                "",
                "You can ask:",
                "",
                "**Show me all MLB teams**",
                "**Search for Corbin Carroll**",
                "**Is the database connected?**",
                "**Who has the highest home run probability right now?**",
            ].join("\n"),
            {
                source: "final_bootstrap",
                version: AISP2_WORKSPACE_VERSION,
            }
        );
    }

    this.saveState();

    return true;
};
/* ============================================================
SECTION 41 - PUBLIC API FOR DEBUGGING AND FUTURE INTEGRATION
============================================================ */

function aisp2CreatePublicWorkspaceApi(workspace) {
    return {
        version: AISP2_WORKSPACE_VERSION,

        getState() {
            return workspace.state;
        },

        getDiagnostics() {
            return aisp2BuildWorkspaceDiagnostics(workspace);
        },

        async health() {
            await workspace.handleHealthIntent();
            return workspace.state.data.health;
        },

        async database() {
            await workspace.handleDatabaseIntent();
            return workspace.state.data.database;
        },

        async warehouse() {
            await workspace.handleWarehouseIntent();
            return workspace.state.data.warehouse;
        },

        async teams(forceRefresh = false) {
            return workspace.loadTeams(forceRefresh);
        },

        async searchPlayers(query) {
            return workspace.searchPlayers(query);
        },

        setApiBaseUrl(baseUrl) {
            workspace.api.setBaseUrl(baseUrl);
            workspace.state.apiBaseUrl = workspace.api.baseUrl;
            workspace.saveState();
            return workspace.api.baseUrl;
        },

        resetLayout() {
            workspace.resetLayout();
            return true;
        },

        clearConversation() {
            workspace.clearConversation();
            return true;
        },

        clearCachedData() {
            workspace.clearCachedBaseballData();
            return true;
        },

        open() {
            workspace.state.ui.state = AISP2_UI_STATES.open;
            workspace.applyUiState();
            return true;
        },

        minimize() {
            workspace.state.ui.state = AISP2_UI_STATES.minimized;
            workspace.applyUiState();
            return true;
        },

        fullscreen() {
            workspace.state.ui.state = AISP2_UI_STATES.fullscreen;
            workspace.applyUiState();
            return true;
        },

        switchTab(tabId) {
            workspace.setActiveTab(tabId);
            return workspace.state.ui.activeTab;
        },
    };
}


/* ============================================================
SECTION 42 - GLOBAL BOOTSTRAP
============================================================ */

async function bootstrapAisp2ChatWorkspace() {
    if (window.AISP2_CHAT_WORKSPACE_INSTANCE) {
        return window.AISP2_CHAT_WORKSPACE_INSTANCE;
    }

    const shellReady = await aisp2WaitForWorkspaceShell();

    if (!shellReady) {
        console.warn(
            "AISP2 chat workspace shell was not found. Confirm chat_shell.html is included before chat_workspace.js.",
        );

        return null;
    }

    const workspace = new Aisp2ChatWorkspace();

    const bootstrapped = workspace.bootstrap();

    if (!bootstrapped) {
        console.warn(
            "AISP2 chat workspace failed to bootstrap.",
        );

        return null;
    }

    window.AISP2_CHAT_WORKSPACE_INSTANCE = workspace;
    window.AISP2_CHAT_WORKSPACE = aisp2CreatePublicWorkspaceApi(
        workspace,
    );

    console.info(
        "AISP2 Chat Workspace bootstrapped.",
        window.AISP2_CHAT_WORKSPACE.getDiagnostics(),
    );

    return workspace;
}


/* ============================================================
SECTION 43 - DOM READY ENTRYPOINT
============================================================ */

if (document.readyState === "loading") {
    document.addEventListener(
        "DOMContentLoaded",
        () => {
            bootstrapAisp2ChatWorkspace();
        },
    );
} else {
    bootstrapAisp2ChatWorkspace();
}


/* ============================================================
SECTION 44 - OPTIONAL MANUAL REBOOT HOOK
============================================================ */

window.bootstrapAisp2ChatWorkspace = bootstrapAisp2ChatWorkspace;

window.resetAisp2ChatWorkspace = function resetAisp2ChatWorkspace() {
    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.workspaceState,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.conversationState,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.uiState,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.activeTab,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.dragState,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.resizeState,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.selectedTeam,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.selectedPlayer,
    );

    aisp2RemoveStorage(
        AISP2_STORAGE_KEYS.selectedPrediction,
    );

    if (window.AISP2_CHAT_WORKSPACE_INSTANCE) {
        window.AISP2_CHAT_WORKSPACE_INSTANCE.destroy();
    }

    window.AISP2_CHAT_WORKSPACE_INSTANCE = null;
    window.AISP2_CHAT_WORKSPACE = null;

    return bootstrapAisp2ChatWorkspace();
};


/* ============================================================
SECTION 45 - FINAL ROADMAP LEDGER
============================================================ */

/*
Phase 6.00 completed:
- Real frontend workspace orchestrator created.
- Existing chat_shell.html selectors wired.
- Existing chat_workspace.css shell supported.
- Floating panel initialized.
- Chat conversation state persisted.
- Health/database/warehouse routes integrated.
- Teams route integrated.
- Player search route integrated.
- Prediction setup workflow created.
- Teams tab added.
- Players tab added.
- Predictions tab added.
- System tab added.
- Recovery controls added.
- Dragging added.
- Resizing added.
- Fullscreen/minimize/collapse behavior added.
- Public debugging API exposed at window.AISP2_CHAT_WORKSPACE.

Next backend milestones:
1. Add POST /predict/player.
2. Add POST /predict/game.
3. Add player stat lookup endpoint.
4. Add team roster endpoint.
5. Add feature_engineering_service.py.
6. Add baseline probability model.
7. Add Monte Carlo engine.
8. Add real probability cards into this workspace.

Useful console commands:
- window.AISP2_CHAT_WORKSPACE.getDiagnostics()
- window.AISP2_CHAT_WORKSPACE.health()
- window.AISP2_CHAT_WORKSPACE.database()
- window.AISP2_CHAT_WORKSPACE.warehouse()
- window.AISP2_CHAT_WORKSPACE.teams(true)
- window.AISP2_CHAT_WORKSPACE.searchPlayers("Corbin Carroll")
- window.resetAisp2ChatWorkspace()
*/