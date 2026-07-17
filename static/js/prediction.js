# ============================================================
# PHASE 12 PART 5.5B - WRITE PREDICTION.JS DIRECTLY
# FILE: static/js/prediction.js
# PURPOSE:
# Avoid failed ChatGPT download link and write the upgraded
# Prediction Workbench JavaScript directly into the project.
# ============================================================

@'
/* ============================================================
   AISP2 BASEBALL INTELLIGENCE PLATFORM
   FILE: static/js/prediction.js
   PHASE: PHASE 12 PART 5.5B
   PURPOSE:
   Stable Prediction Workbench JavaScript runtime.

   FIXES:
   - Blank player dropdowns.
   - Duplicate selector initialization.
   - Old demo-only rendering.
   - One-element-only text updates.
   - /api/player-explorer/bootstrap and /api/v2/player-explorer/bootstrap shape mismatch.
   - AI Prediction Intelligence panel staying Pending.
   ============================================================ */

const AISP2_PREDICTION_STATE = {
    initialized: false,
    selectorLoaded: false,
    selectorLoading: false,
    predictionRunning: false,
    endpoints: {
        bootstrapPrimary: "/api/player-explorer/bootstrap",
        bootstrapV2: "/api/v2/player-explorer/bootstrap",
        teamPlayersV2: "/api/v2/player-explorer/teams/{team_identifier}/players",
        prediction: "/predict/player"
    },
    teams: [],
    playersByTeam: {},
    teamIndex: {},
    selectedTeam: null,
    selectedPlayers: [],
    selectorSource: "Pending",
    selectorWarnings: [],
    selectorDiagnostics: {},
    fallbackChain: [],
    lastPrediction: null,
    lastError: null
};

document.addEventListener("DOMContentLoaded", function () {
    initializeAISP2PredictionWorkbench();
});

async function initializeAISP2PredictionWorkbench() {
    if (AISP2_PREDICTION_STATE.initialized) {
        return;
    }

    AISP2_PREDICTION_STATE.initialized = true;

    hydrateEndpointsFromTemplate();
    bindPredictionWorkbenchEvents();
    resetPredictionWorkbenchDisplay();

    await loadPredictionSelectors({ force: true });
}

function hydrateEndpointsFromTemplate() {
    const shell =
        document.querySelector("[data-page='prediction-workbench']") ||
        document.querySelector(".app-shell");

    if (!shell || !shell.dataset) {
        return;
    }

    if (shell.dataset.bootstrapEndpoint) {
        AISP2_PREDICTION_STATE.endpoints.bootstrapPrimary = shell.dataset.bootstrapEndpoint;
    }

    if (shell.dataset.v2BootstrapEndpoint) {
        AISP2_PREDICTION_STATE.endpoints.bootstrapV2 = shell.dataset.v2BootstrapEndpoint;
    }

    if (shell.dataset.predictionEndpoint) {
        AISP2_PREDICTION_STATE.endpoints.prediction = shell.dataset.predictionEndpoint;
    }
}

function qs(selector) {
    return document.querySelector(selector);
}

function qsa(selector) {
    return Array.from(document.querySelectorAll(selector));
}

function getTeamSelector() {
    return qs("[data-prediction-team]");
}

function getPlayerSelector() {
    return qs("[data-prediction-player]");
}

function getOutcomeSelector() {
    return qs("[data-prediction-outcome]");
}

function getPredictionButton() {
    return qs("[data-prediction-submit]");
}

function getResetButton() {
    return qs("[data-prediction-reset]");
}

function getSelectorRefreshButton() {
    return qs("[data-selector-refresh]");
}

function selectedOption(selectElement) {
    if (!selectElement || !selectElement.selectedOptions || !selectElement.selectedOptions.length) {
        return null;
    }

    return selectElement.selectedOptions[0];
}

function setTextIfExists(selector, value) {
    const elements = qsa(selector);

    if (!elements.length) {
        return;
    }

    const text =
        value === null ||
        value === undefined ||
        value === ""
            ? "Pending"
            : String(value);

    elements.forEach(function (element) {
        element.textContent = text;
    });
}

function setListIfExists(selector, values) {
    const elements = qsa(selector);

    if (!elements.length) {
        return;
    }

    const items =
        Array.isArray(values) && values.length
            ? values
            : ["No items reported."];

    elements.forEach(function (element) {
        element.innerHTML = "";

        items.forEach(function (item) {
            const li = document.createElement("li");

            if (typeof item === "string") {
                li.textContent = item;
            } else if (item && typeof item === "object") {
                li.textContent =
                    item.message ||
                    item.detail ||
                    item.error ||
                    JSON.stringify(item);
            } else {
                li.textContent = String(item);
            }

            element.appendChild(li);
        });
    });
}

function clearSelect(selectElement, message) {
    if (!selectElement) {
        return;
    }

    selectElement.innerHTML = "";

    const option = document.createElement("option");
    option.value = "";
    option.textContent = message || "Pending";
    selectElement.appendChild(option);
}

function addSelectOption(selectElement, value, label, dataset) {
    if (!selectElement || value === null || value === undefined || !label) {
        return;
    }

    const option = document.createElement("option");
    option.value = String(value);
    option.textContent = String(label);

    if (dataset && typeof dataset === "object") {
        Object.keys(dataset).forEach(function (key) {
            if (dataset[key] !== null && dataset[key] !== undefined) {
                option.dataset[key] = String(dataset[key]);
            }
        });
    }

    selectElement.appendChild(option);
}

function normalizeText(value) {
    return String(value || "")
        .toLowerCase()
        .trim()
        .replace(/\./g, " ")
        .replace(/,/g, " ")
        .replace(/'/g, "")
        .replace(/’/g, "")
        .replace(/-/g, " ")
        .replace(/_/g, " ")
        .replace(/\s+/g, " ");
}

function compactText(value) {
    return normalizeText(value).replace(/\s+/g, "");
}

function titleCase(value) {
    return String(value || "")
        .replace(/_/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .replace(/\w\S*/g, function (word) {
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        });
}

function safeNumber(value) {
    if (value === null || value === undefined || value === "") {
        return null;
    }

    const number = Number(value);

    if (Number.isNaN(number) || !Number.isFinite(number)) {
        return null;
    }

    return number;
}

function formatPercent(value, fallback) {
    const number = safeNumber(value);

    if (number === null) {
        return fallback || "Pending";
    }

    return String(number) + "%";
}

function formatCount(value, fallback) {
    const number = safeNumber(value);

    if (number === null) {
        return fallback || "Pending";
    }

    return String(Math.round(number));
}

function formatSource(value) {
    return titleCase(
        String(value || "Pending")
            .replace(/api/g, "API")
            .replace(/mlb/g, "MLB")
    );
}

function isInvalidPlayerValue(value) {
    const text = normalizeText(value);

    return (
        !text ||
        text === "select player" ||
        text === "selected player" ||
        text === "select a team first" ||
        text === "loading players" ||
        text === "player list unavailable" ||
        text.includes("no players loaded") ||
        text.includes("unavailable")
    );
}

function bindPredictionWorkbenchEvents() {
    const form = qs("[data-prediction-form]");

    if (form && !form.dataset.aisp2Bound) {
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            runPrediction();
        });

        form.dataset.aisp2Bound = "true";
    }

    const runButton = getPredictionButton();

    if (runButton && !runButton.dataset.aisp2Bound) {
        runButton.addEventListener("click", function (event) {
            event.preventDefault();
            runPrediction();
        });

        runButton.dataset.aisp2Bound = "true";
    }

    const resetButton = getResetButton();

    if (resetButton && !resetButton.dataset.aisp2Bound) {
        resetButton.addEventListener("click", function (event) {
            event.preventDefault();
            resetPredictionWorkbenchDisplay();
        });

        resetButton.dataset.aisp2Bound = "true";
    }

    const refreshButton = getSelectorRefreshButton();

    if (refreshButton && !refreshButton.dataset.aisp2Bound) {
        refreshButton.addEventListener("click", async function (event) {
            event.preventDefault();
            await loadPredictionSelectors({ force: true });
        });

        refreshButton.dataset.aisp2Bound = "true";
    }

    const teamSelector = getTeamSelector();

    if (teamSelector && !teamSelector.dataset.aisp2TeamBound) {
        teamSelector.addEventListener("change", async function () {
            await handleTeamChange();
        });

        teamSelector.dataset.aisp2TeamBound = "true";
    }

    const playerSelector = getPlayerSelector();

    if (playerSelector && !playerSelector.dataset.aisp2PlayerBound) {
        playerSelector.addEventListener("change", function () {
            updateSelectedContextPreview();
        });

        playerSelector.dataset.aisp2PlayerBound = "true";
    }

    const outcomeSelector = getOutcomeSelector();

    if (outcomeSelector && !outcomeSelector.dataset.aisp2OutcomeBound) {
        outcomeSelector.addEventListener("change", function () {
            updateSelectedContextPreview();
        });

        outcomeSelector.dataset.aisp2OutcomeBound = "true";
    }
}

async function handleTeamChange() {
    const teamSelector = getTeamSelector();
    const team = resolveTeam(teamSelector ? teamSelector.value : "");

    await renderPlayersForTeam(team);

    clearPredictionNotice();
    updateSelectedContextPreview();
}

async function fetchJSON(endpoint) {
    const response = await fetch(
        endpoint,
        {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        }
    );

    let payload = null;

    try {
        payload = await response.json();
    } catch (error) {
        throw new Error(endpoint + " returned invalid JSON.");
    }

    if (!response.ok) {
        throw new Error(
            payload.message ||
            payload.error ||
            payload.detail ||
            endpoint + " returned HTTP " + response.status
        );
    }

    return payload;
}

async function fetchBootstrapPayload() {
    const primaryEndpoint = AISP2_PREDICTION_STATE.endpoints.bootstrapPrimary;
    const v2Endpoint = AISP2_PREDICTION_STATE.endpoints.bootstrapV2;

    try {
        const primaryPayload = await fetchJSON(primaryEndpoint);
        const normalizedPrimary = normalizeBootstrapPayload(primaryPayload);

        if (normalizedPrimary.teams.length > 0) {
            primaryPayload.__endpoint = primaryEndpoint;
            return primaryPayload;
        }

        throw new Error("Primary bootstrap returned zero teams.");
    } catch (primaryError) {
        try {
            const v2Payload = await fetchJSON(v2Endpoint);
            v2Payload.__endpoint = v2Endpoint;
            v2Payload.__primary_error = primaryError.message;
            return v2Payload;
        } catch (v2Error) {
            return buildEmergencyBootstrapPayload(primaryError, v2Error);
        }
    }
}

function buildEmergencyBootstrapPayload(primaryError, v2Error) {
    return {
        status: "partial",
        bootstrap_source: "emergency_static_fallback",
        selector_status: "emergency_static_fallback",
        team_count: 3,
        player_count: 3,
        teams: [
            {
                id: "147",
                mlb_team_id: "147",
                name: "New York Yankees",
                abbreviation: "NYY",
                source: "emergency_static_fallback"
            },
            {
                id: "119",
                mlb_team_id: "119",
                name: "Los Angeles Dodgers",
                abbreviation: "LAD",
                source: "emergency_static_fallback"
            },
            {
                id: "111",
                mlb_team_id: "111",
                name: "Boston Red Sox",
                abbreviation: "BOS",
                source: "emergency_static_fallback"
            }
        ],
        players_by_team: {
            "147": [
                {
                    id: "592450",
                    mlb_player_id: "592450",
                    full_name: "Aaron Judge",
                    name: "Aaron Judge",
                    source: "emergency_static_fallback"
                }
            ],
            "119": [
                {
                    id: "660271",
                    mlb_player_id: "660271",
                    full_name: "Shohei Ohtani",
                    name: "Shohei Ohtani",
                    source: "emergency_static_fallback"
                }
            ],
            "111": [
                {
                    id: "646240",
                    mlb_player_id: "646240",
                    full_name: "Rafael Devers",
                    name: "Rafael Devers",
                    source: "emergency_static_fallback"
                }
            ]
        },
        default_team: {
            id: "147",
            mlb_team_id: "147",
            name: "New York Yankees",
            abbreviation: "NYY"
        },
        fallback_chain: [
            "primary_bootstrap_failed",
            "v2_bootstrap_failed",
            "emergency_static_fallback"
        ],
        warnings: [
            "Primary bootstrap failed: " + primaryError.message,
            "V2 bootstrap failed: " + v2Error.message,
            "Emergency selector fallback is active."
        ],
        __endpoint: "emergency_static_fallback"
    };
}

function normalizeBootstrapPayload(payload) {
    const rawTeams = Array.isArray(payload.teams) ? payload.teams : [];

    const teams = rawTeams
        .map(normalizeTeam)
        .filter(Boolean)
        .sort(function (a, b) {
            return a.name.localeCompare(b.name);
        });

    const rawPlayersByTeam =
        payload.players_by_team ||
        payload.playersByTeam ||
        {};

    const playersByTeam = normalizePlayersByTeam(rawPlayersByTeam);

    const source =
        payload.bootstrap_source ||
        payload.selector_source ||
        payload.source ||
        payload.__endpoint ||
        "database_or_api";

    const warnings =
        Array.isArray(payload.warnings)
            ? payload.warnings
            : [];

    const fallbackChain =
        Array.isArray(payload.fallback_chain)
            ? payload.fallback_chain
            : buildFallbackChain(payload);

    return {
        raw: payload,
        teams: teams,
        playersByTeam: playersByTeam,
        source: source,
        warnings: warnings,
        fallbackChain: fallbackChain,
        defaultTeam: normalizeTeam(payload.default_team) || teams[0] || null,
        diagnostics: {
            status: payload.status || payload.selector_status || "unknown",
            team_count: payload.team_count || teams.length,
            player_count: payload.player_count || countUniquePlayers(playersByTeam),
            database_team_count: payload.database_team_count,
            database_player_count: payload.database_player_count,
            players_by_team_key_count:
                payload.players_by_team_key_count ||
                Object.keys(playersByTeam).length,
            fallback_reason: payload.fallback_reason || "",
            endpoint: payload.__endpoint || ""
        }
    };
}

function normalizeTeam(team) {
    if (!team || typeof team !== "object") {
        return null;
    }

    const name =
        team.name ||
        team.team_name ||
        team.full_name ||
        team.club_name ||
        team.abbreviation;

    if (!name) {
        return null;
    }

    const id =
        team.id ||
        team.database_id ||
        team.team_id ||
        team.mlb_team_id ||
        name;

    const mlbTeamId =
        team.mlb_team_id ||
        team.mlbTeamId ||
        team.team_id ||
        team.id ||
        "";

    return {
        id: String(id),
        mlb_team_id: mlbTeamId !== null && mlbTeamId !== undefined ? String(mlbTeamId) : "",
        name: String(name),
        team_name: String(name),
        abbreviation: team.abbreviation || "",
        club_name: team.club_name || team.clubName || "",
        short_name: team.short_name || team.shortName || "",
        location_name: team.location_name || team.locationName || "",
        source: team.source || "bootstrap"
    };
}

function normalizePlayersByTeam(rawPlayersByTeam) {
    const output = {};

    if (!rawPlayersByTeam || typeof rawPlayersByTeam !== "object") {
        return output;
    }

    Object.keys(rawPlayersByTeam).forEach(function (teamKey) {
        output[String(teamKey)] = normalizePlayersArray(rawPlayersByTeam[teamKey]);
    });

    return output;
}

function normalizePlayersArray(players) {
    if (!Array.isArray(players)) {
        return [];
    }

    const seen = new Set();

    return players
        .map(function (player) {
            if (!player || typeof player !== "object") {
                return null;
            }

            const playerName =
                player.full_name ||
                player.name ||
                player.player_name ||
                player.fullName;

            if (!playerName) {
                return null;
            }

            const mlbPlayerId =
                player.mlb_player_id ||
                player.mlbPlayerId ||
                player.player_id ||
                player.id ||
                "";

            const id =
                player.id ||
                player.database_id ||
                player.player_id ||
                mlbPlayerId ||
                playerName;

            const dedupeKey = compactText(playerName) + "|" + String(mlbPlayerId || id);

            if (seen.has(dedupeKey)) {
                return null;
            }

            seen.add(dedupeKey);

            return {
                id: String(id),
                mlb_player_id: mlbPlayerId !== null && mlbPlayerId !== undefined ? String(mlbPlayerId) : "",
                full_name: String(playerName),
                name: String(playerName),
                position: player.position || player.position_name || "",
                position_code: player.position_code || player.positionCode || "",
                team_id: player.team_id || player.current_team_id || "",
                source: player.source || "bootstrap"
            };
        })
        .filter(Boolean)
        .sort(function (a, b) {
            return a.full_name.localeCompare(b.full_name);
        });
}

function buildFallbackChain(payload) {
    const chain = [];

    if (payload.database_team_count === 0 || payload.database_player_count === 0) {
        chain.push("database_empty");
    }

    if (payload.bootstrap_source) {
        chain.push(payload.bootstrap_source);
    }

    if (!chain.length) {
        chain.push("not_reported");
    }

    return chain;
}

function countUniquePlayers(playersByTeam) {
    const seen = new Set();

    Object.keys(playersByTeam || {}).forEach(function (teamKey) {
        const players = playersByTeam[teamKey];

        if (!Array.isArray(players)) {
            return;
        }

        players.forEach(function (player) {
            seen.add(
                String(
                    player.mlb_player_id ||
                    player.id ||
                    player.full_name ||
                    player.name
                )
            );
        });
    });

    return seen.size;
}

function buildTeamIndex(teams) {
    AISP2_PREDICTION_STATE.teamIndex = {};

    teams.forEach(function (team) {
        const keys = [
            team.id,
            team.mlb_team_id,
            team.name,
            team.team_name,
            team.abbreviation,
            team.club_name,
            team.short_name,
            team.location_name,
            normalizeText(team.name),
            compactText(team.name),
            normalizeText(team.abbreviation),
            compactText(team.abbreviation)
        ];

        keys.forEach(function (key) {
            if (key !== null && key !== undefined && key !== "") {
                AISP2_PREDICTION_STATE.teamIndex[String(key)] = team;
            }
        });
    });
}

function resolveTeam(value) {
    const teamSelector = getTeamSelector();
    const option = selectedOption(teamSelector);

    const keys = [];

    if (option) {
        keys.push(
            option.dataset.teamId,
            option.dataset.mlbTeamId,
            option.value,
            option.textContent
        );
    }

    keys.push(value, normalizeText(value), compactText(value));

    for (let index = 0; index < keys.length; index += 1) {
        const key = keys[index];

        if (
            key !== null &&
            key !== undefined &&
            key !== "" &&
            AISP2_PREDICTION_STATE.teamIndex[String(key)]
        ) {
            return AISP2_PREDICTION_STATE.teamIndex[String(key)];
        }
    }

    return null;
}

function getPlayersForTeam(team) {
    if (!team) {
        return [];
    }

    const playersByTeam = AISP2_PREDICTION_STATE.playersByTeam || {};

    const keys = [
        team.id,
        team.mlb_team_id,
        team.name,
        team.team_name,
        team.abbreviation,
        team.club_name,
        team.short_name,
        normalizeText(team.name),
        compactText(team.name),
        normalizeText(team.abbreviation),
        compactText(team.abbreviation)
    ];

    for (let index = 0; index < keys.length; index += 1) {
        const key = keys[index];

        if (key === null || key === undefined || key === "") {
            continue;
        }

        const players = playersByTeam[String(key)];

        if (Array.isArray(players) && players.length > 0) {
            return players;
        }
    }

    return [];
}

async function fetchPlayersForTeamFromV2(team) {
    if (!team) {
        return [];
    }

    const identifier = team.id || team.mlb_team_id || team.name;

    if (!identifier) {
        return [];
    }

    const endpoint =
        AISP2_PREDICTION_STATE.endpoints.teamPlayersV2.replace(
            "{team_identifier}",
            encodeURIComponent(String(identifier))
        );

    try {
        const payload = await fetchJSON(endpoint);

        const players = normalizePlayersArray(payload.players || payload.data || []);

        if (players.length > 0) {
            storePlayersForTeam(team, players);
        }

        return players;
    } catch (error) {
        AISP2_PREDICTION_STATE.selectorWarnings.push(
            "Team player fallback failed for " + team.name + ": " + error.message
        );

        return [];
    }
}

function storePlayersForTeam(team, players) {
    const keys = [
        team.id,
        team.mlb_team_id,
        team.name,
        team.team_name,
        team.abbreviation,
        team.club_name,
        team.short_name
    ];

    keys.forEach(function (key) {
        if (key !== null && key !== undefined && key !== "") {
            AISP2_PREDICTION_STATE.playersByTeam[String(key)] = players;
        }
    });
}

function renderTeamSelector() {
    const teamSelector = getTeamSelector();

    if (!teamSelector) {
        setSelectorFailure("Team selector was not found in the page.");
        return;
    }

    teamSelector.innerHTML = "";

    if (!AISP2_PREDICTION_STATE.teams.length) {
        clearSelect(teamSelector, "No teams loaded");
        return;
    }

    AISP2_PREDICTION_STATE.teams.forEach(function (team) {
        addSelectOption(
            teamSelector,
            team.name,
            team.name,
            {
                teamId: team.id,
                mlbTeamId: team.mlb_team_id,
                abbreviation: team.abbreviation,
                source: team.source
            }
        );
    });

    const defaultTeam =
        AISP2_PREDICTION_STATE.selectedTeam ||
        AISP2_PREDICTION_STATE.teams[0];

    if (defaultTeam && defaultTeam.name) {
        teamSelector.value = defaultTeam.name;
    }
}

async function renderPlayersForTeam(team) {
    const playerSelector = getPlayerSelector();

    if (!playerSelector) {
        setSelectorFailure("Player selector was not found in the page.");
        return;
    }

    playerSelector.innerHTML = "";

    if (!team) {
        clearSelect(playerSelector, "Select a team first");
        setTextIfExists("[data-player-selector-note]", "Select a team first.");
        return;
    }

    let players = getPlayersForTeam(team);

    if (!players.length) {
        clearSelect(playerSelector, "Loading roster...");
        players = await fetchPlayersForTeamFromV2(team);
    }

    if (!players.length) {
        clearSelect(playerSelector, "No players loaded for this team");
        setTextIfExists("[data-player-selector-note]", "No players returned for " + team.name + ".");
        updateSelectorDiagnostics();
        return;
    }

    players.forEach(function (player) {
        addSelectOption(
            playerSelector,
            player.full_name || player.name,
            player.full_name || player.name,
            {
                playerId: player.id,
                mlbPlayerId: player.mlb_player_id,
                position: player.position,
                positionCode: player.position_code,
                source: player.source
            }
        );
    });

    playerSelector.selectedIndex = 0;

    AISP2_PREDICTION_STATE.selectedTeam = team;
    AISP2_PREDICTION_STATE.selectedPlayers = players;

    setTextIfExists("[data-player-selector-note]", String(players.length) + " players loaded for " + team.name + ".");

    updateSelectorDiagnostics();
    updateSelectedContextPreview();
}

async function loadPredictionSelectors(options) {
    const force = options && options.force;

    if (
        AISP2_PREDICTION_STATE.selectorLoading ||
        (AISP2_PREDICTION_STATE.selectorLoaded && !force)
    ) {
        return;
    }

    AISP2_PREDICTION_STATE.selectorLoading = true;

    setTextIfExists("[data-selector-health]", "Loading");
    setTextIfExists("[data-selector-state]", "Loading");
    setTextIfExists("[data-team-selector-note]", "Loading teams...");
    setTextIfExists("[data-player-selector-note]", "Loading players...");
    clearSelect(getPlayerSelector(), "Loading players...");

    try {
        const rawPayload = await fetchBootstrapPayload();
        const normalized = normalizeBootstrapPayload(rawPayload);

        AISP2_PREDICTION_STATE.selectorLoaded = true;
        AISP2_PREDICTION_STATE.selectorLoading = false;
        AISP2_PREDICTION_STATE.teams = normalized.teams;
        AISP2_PREDICTION_STATE.playersByTeam = normalized.playersByTeam;
        AISP2_PREDICTION_STATE.selectorSource = normalized.source;
        AISP2_PREDICTION_STATE.selectorWarnings = normalized.warnings;
        AISP2_PREDICTION_STATE.selectorDiagnostics = normalized.diagnostics;
        AISP2_PREDICTION_STATE.fallbackChain = normalized.fallbackChain;
        AISP2_PREDICTION_STATE.selectedTeam = normalized.defaultTeam || normalized.teams[0] || null;

        buildTeamIndex(normalized.teams);
        renderTeamSelector();

        const teamSelector = getTeamSelector();
        const selectedTeam =
            resolveTeam(teamSelector ? teamSelector.value : "") ||
            AISP2_PREDICTION_STATE.selectedTeam;

        await renderPlayersForTeam(selectedTeam);

        setTextIfExists("[data-selector-health]", "Ready");
        setTextIfExists("[data-selector-state]", "Ready");
        setTextIfExists("[data-team-selector-note]", String(normalized.teams.length) + " teams loaded.");

        updateSelectorDiagnostics();
    } catch (error) {
        AISP2_PREDICTION_STATE.selectorLoading = false;
        AISP2_PREDICTION_STATE.selectorLoaded = false;
        setSelectorFailure(error.message || "Selector loading failed.");
    }
}

function setSelectorFailure(message) {
    setTextIfExists("[data-selector-health]", "Failed");
    setTextIfExists("[data-selector-state]", "Failed");
    setTextIfExists("[data-selector-warning]", message);
    setTextIfExists("[data-player-selector-note]", message);
    clearSelect(getPlayerSelector(), "Player list unavailable");

    AISP2_PREDICTION_STATE.selectorWarnings.push(message);
}

function updateSelectorDiagnostics() {
    const teamCount = AISP2_PREDICTION_STATE.teams.length;
    const playerCount = countUniquePlayers(AISP2_PREDICTION_STATE.playersByTeam);
    const source = formatSource(AISP2_PREDICTION_STATE.selectorSource);

    const fallbackChain =
        Array.isArray(AISP2_PREDICTION_STATE.fallbackChain)
            ? AISP2_PREDICTION_STATE.fallbackChain.join(" -> ")
            : "Not Reported";

    setTextIfExists("[data-teams-loaded]", teamCount);
    setTextIfExists("[data-players-loaded]", playerCount);
    setTextIfExists("[data-bootstrap-source]", source);
    setTextIfExists("[data-selector-source]", source);
    setTextIfExists("[data-fallback-chain]", fallbackChain);

    if (teamCount > 0 && playerCount > 0) {
        setTextIfExists("[data-selector-warning]", "Selectors are populated. Source: " + source + ".");
    } else {
        setTextIfExists("[data-selector-warning]", "Selectors are not fully populated. Check bootstrap JSON.");
    }

    const diagnostics = AISP2_PREDICTION_STATE.selectorDiagnostics || {};

    if (
        diagnostics.database_team_count === 0 &&
        diagnostics.database_player_count === 0
    ) {
        setTextIfExists("[data-warehouse-status]", "Render DB Empty");
    } else {
        setTextIfExists("[data-warehouse-status]", "Selector Ready");
    }
}

function collectPredictionPayload() {
    const teamSelector = getTeamSelector();
    const playerSelector = getPlayerSelector();
    const outcomeSelector = getOutcomeSelector();

    const teamOption = selectedOption(teamSelector);
    const playerOption = selectedOption(playerSelector);

    return {
        team: teamSelector ? teamSelector.value : "",
        team_id: teamOption ? teamOption.dataset.teamId || "" : "",
        mlb_team_id: teamOption ? teamOption.dataset.mlbTeamId || "" : "",
        player: playerSelector ? playerSelector.value : "",
        player_id: playerOption ? playerOption.dataset.playerId || "" : "",
        mlb_player_id: playerOption ? playerOption.dataset.mlbPlayerId || "" : "",
        outcome: outcomeSelector ? outcomeSelector.value : "home_run"
    };
}

function validatePredictionPayload(payload) {
    const errors = [];

    if (!payload.team) {
        errors.push("Select a team before running a prediction.");
    }

    if (!payload.player || isInvalidPlayerValue(payload.player)) {
        errors.push("Select a valid player before running a prediction.");
    }

    if (!payload.outcome) {
        errors.push("Select an outcome before running a prediction.");
    }

    return {
        valid: errors.length === 0,
        errors: errors
    };
}

function updateSelectedContextPreview() {
    const payload = collectPredictionPayload();

    if (payload.player && !isInvalidPlayerValue(payload.player)) {
        setTextIfExists("[data-result-player]", payload.player);
        setTextIfExists("[data-intelligence-summary]", "Ready to generate prediction intelligence for " + payload.player + ".");
    } else {
        setTextIfExists("[data-result-player]", "Select Player");
        setTextIfExists("[data-intelligence-summary]", "Select a team, player, and outcome to generate AISP2 prediction intelligence.");
    }

    setTextIfExists("[data-result-outcome]", titleCase(payload.outcome || "Outcome") + " Probability");
}

async function runPrediction() {
    if (AISP2_PREDICTION_STATE.predictionRunning) {
        return;
    }

    const payload = collectPredictionPayload();
    const validation = validatePredictionPayload(payload);

    if (!validation.valid) {
        renderPredictionError(validation.errors.join(" "));
        return;
    }

    setPredictionLoading(true);
    clearPredictionNotice();

    try {
        const result = await fetchPredictionResult(payload);
        AISP2_PREDICTION_STATE.lastPrediction = result;
        AISP2_PREDICTION_STATE.lastError = null;
        renderPredictionResult(result);
        renderOutcomeLibrary(result);
    } catch (error) {
        AISP2_PREDICTION_STATE.lastError = error;
        console.error("AISP2 prediction error:", error);
        renderPredictionError(error.message || "Prediction failed.");
    } finally {
        setPredictionLoading(false);
    }
}

async function fetchPredictionResult(payload) {
    const response = await fetch(
        AISP2_PREDICTION_STATE.endpoints.prediction,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                team: payload.team || "",
                player: payload.player || "",
                outcome: payload.outcome || "home_run"
            })
        }
    );

    let data = {};

    try {
        data = await response.json();
    } catch (error) {
        throw new Error("Prediction endpoint returned invalid JSON.");
    }

    if (!response.ok) {
        throw new Error(
            data.detail ||
            data.error ||
            data.message ||
            "Prediction request failed."
        );
    }

    return data;
}

function renderPredictionResult(result) {
    const prediction = result.prediction || {};
    const outcome = result.outcome || {};
    const team =
        result.team && typeof result.team === "object"
            ? result.team
            : { name: result.team };
    const supporting = result.supporting_context || {};
    const intelligence = result.intelligence || {};
    const dataStatus = result.data_status || {};

    const probability =
        prediction.estimated_probability ??
        prediction.probability ??
        result.probability;

    const confidence =
        prediction.confidence ??
        result.confidence;

    const tier =
        prediction.tier ||
        intelligence.tier ||
        "Pending";

    const risk =
        prediction.risk_profile ||
        intelligence.risk_profile ||
        "Pending";

    const outcomeProfile =
        intelligence.outcome_profile ||
        supporting.player_style ||
        "Pending";

    const primaryMetric =
        intelligence.primary_metric ||
        supporting.primary_metric ||
        "Pending";

    const model =
        prediction.model ||
        result.model ||
        "AISP2 Prediction Model";

    const dataSource =
        intelligence.data_source ||
        prediction.prediction_source ||
        "Pending";

    const coverage =
        intelligence.data_coverage ??
        prediction.data_coverage ??
        dataStatus.data_coverage;

    const warehouseStatus =
        intelligence.warehouse_status ||
        prediction.warehouse_status ||
        (
            safeNumber(coverage) && safeNumber(coverage) > 0
                ? "Warehouse Partial"
                : "Pending Ingestion"
        );

    const sampleSize =
        intelligence.sample_size ??
        prediction.sample_size ??
        prediction.plate_appearances;

    const explanation =
        intelligence.ai_explanation ||
        supporting.ai_explanation ||
        result.explanation ||
        "AISP2 returned a prediction without a detailed explanation.";

    setTextIfExists("[data-result-player]", result.player || "Unknown Player");
    setTextIfExists("[data-result-team]", team.name || "Unknown Team");
    setTextIfExists("[data-result-outcome]", outcome.label || titleCase(outcome.key || "Prediction"));
    setTextIfExists("[data-result-probability]", formatPercent(probability));
    setTextIfExists("[data-result-confidence]", formatPercent(confidence, "Confidence Pending"));
    setTextIfExists("[data-result-tier]", tier);
    setTextIfExists("[data-result-risk]", risk);
    setTextIfExists("[data-result-profile]", outcomeProfile);
    setTextIfExists("[data-result-supporting-metric]", primaryMetric);
    setTextIfExists("[data-result-model]", model);
    setTextIfExists("[data-result-model-secondary]", model);
    setTextIfExists("[data-result-style]", supporting.player_style || outcomeProfile);
    setTextIfExists("[data-result-form]", supporting.recent_form || "Pending Ingestion");
    setTextIfExists("[data-result-metric]", primaryMetric);
    setTextIfExists("[data-result-source]", formatSource(dataSource));
    setTextIfExists("[data-result-data-coverage]", formatPercent(coverage));
    setTextIfExists("[data-result-sample-size]", formatCount(sampleSize));
    setTextIfExists("[data-result-warehouse-status]", warehouseStatus);
    setTextIfExists("[data-result-ai-explanation]", explanation);

    setTextIfExists("[data-intelligence-summary]", explanation);
    setTextIfExists("[data-intelligence-tier]", tier);
    setTextIfExists("[data-intelligence-risk]", risk);
    setTextIfExists("[data-intelligence-profile]", outcomeProfile);
    setTextIfExists("[data-intelligence-primary-metric]", primaryMetric);
    setTextIfExists("[data-intelligence-data-source]", formatSource(dataSource));
    setTextIfExists("[data-intelligence-coverage]", formatPercent(coverage));
    setTextIfExists("[data-intelligence-warehouse]", warehouseStatus);
    setTextIfExists("[data-intelligence-guidance]", intelligence.model_guidance || "Review warnings and next data needed.");
    setTextIfExists("[data-intelligence-reasoning]", explanation);
    setTextIfExists("[data-warehouse-status]", warehouseStatus);

    setListIfExists(
        "[data-intelligence-warnings]",
        intelligence.warnings ||
        result.warnings ||
        buildWarningsFromDataStatus(dataStatus)
    );

    setListIfExists(
        "[data-intelligence-next-data]",
        intelligence.next_data_needed ||
        result.next_data_needed ||
        buildNextDataFromDataStatus(dataStatus)
    );
}

function buildWarningsFromDataStatus(dataStatus) {
    const warnings = [];

    if (dataStatus && dataStatus.warehouse_data_available === false) {
        warnings.push("Warehouse data is unavailable for this prediction.");
    }

    if (
        dataStatus &&
        dataStatus.database &&
        dataStatus.database.player_count === 0
    ) {
        warnings.push("The deployed database reports zero players.");
    }

    if (!warnings.length) {
        warnings.push("No critical prediction warnings detected.");
    }

    return warnings;
}

function buildNextDataFromDataStatus(dataStatus) {
    if (
        dataStatus &&
        Array.isArray(dataStatus.missing_sources) &&
        dataStatus.missing_sources.length
    ) {
        return dataStatus.missing_sources.map(function (source) {
            return "Load missing source: " + titleCase(source);
        });
    }

    return ["No specific missing source was reported by the prediction endpoint."];
}

function resetOutcomeLibrary() {
    setTextIfExists("[data-prop-home-run]", "Pending");
    setTextIfExists("[data-prop-hit]", "Pending");
    setTextIfExists("[data-prop-rbi]", "Pending");
    setTextIfExists("[data-prop-run-scored]", "Pending");
    setTextIfExists("[data-prop-total-bases]", "Pending");
    setTextIfExists("[data-prop-strikeout]", "Pending");
}

function renderOutcomeLibrary(result) {
    const outcome = result.outcome || {};
    const prediction = result.prediction || {};
    const probability = prediction.estimated_probability;

    if (probability === null || probability === undefined) {
        return;
    }

    const selectorMap = {
        home_run: "[data-prop-home-run]",
        hit: "[data-prop-hit]",
        rbi: "[data-prop-rbi]",
        run: "[data-prop-run-scored]",
        run_scored: "[data-prop-run-scored]",
        total_bases: "[data-prop-total-bases]",
        strikeout: "[data-prop-strikeout]"
    };

    const selector = selectorMap[outcome.key];

    if (selector) {
        setTextIfExists(selector, formatPercent(probability));
    }
}

function renderPredictionError(message) {
    const text = message || "Prediction failed.";

    setTextIfExists("[data-prediction-error]", text);
    setTextIfExists("[data-selector-warning]", text);
    setTextIfExists("[data-intelligence-summary]", text);
    setTextIfExists("[data-intelligence-reasoning]", text);

    setListIfExists("[data-intelligence-warnings]", [text]);

    const errorPanel = qs("[data-prediction-error-panel]");

    if (errorPanel) {
        errorPanel.classList.add("visible");
    }
}

function clearPredictionNotice() {
    const errorPanel = qs("[data-prediction-error-panel]");

    if (errorPanel) {
        errorPanel.classList.remove("visible");
    }
}

function setPredictionLoading(isLoading) {
    AISP2_PREDICTION_STATE.predictionRunning = Boolean(isLoading);

    const button = getPredictionButton();

    if (button) {
        button.disabled = Boolean(isLoading);
        button.textContent = isLoading ? "Running..." : "Run Prediction";
    }

    if (isLoading) {
        setTextIfExists("[data-intelligence-summary]", "Running prediction request...");
        setTextIfExists("[data-intelligence-reasoning]", "AISP2 is requesting Python model output from /predict/player.");
    }
}

function resetPredictionWorkbenchDisplay() {
    AISP2_PREDICTION_STATE.lastPrediction = null;
    AISP2_PREDICTION_STATE.lastError = null;

    setTextIfExists("[data-result-player]", "Select Player");
    setTextIfExists("[data-result-outcome]", "Outcome Pending");
    setTextIfExists("[data-result-probability]", "Pending");
    setTextIfExists("[data-result-confidence]", "Confidence Pending");
    setTextIfExists("[data-result-tier]", "Pending");
    setTextIfExists("[data-result-risk]", "Pending");
    setTextIfExists("[data-result-profile]", "Pending");
    setTextIfExists("[data-result-supporting-metric]", "Pending");
    setTextIfExists("[data-result-model]", "Pending");
    setTextIfExists("[data-result-model-secondary]", "Pending");
    setTextIfExists("[data-result-style]", "Pending");
    setTextIfExists("[data-result-form]", "Pending");
    setTextIfExists("[data-result-metric]", "Pending");
    setTextIfExists("[data-result-source]", "Pending");
    setTextIfExists("[data-result-data-coverage]", "Pending");
    setTextIfExists("[data-result-sample-size]", "Pending");
    setTextIfExists("[data-result-warehouse-status]", "Pending");
    setTextIfExists("[data-result-ai-explanation]", "Select a player and outcome to generate AISP2 baseball intelligence.");

    setTextIfExists("[data-intelligence-summary]", "Select a team, player, and outcome to generate AISP2 prediction intelligence.");
    setTextIfExists("[data-intelligence-tier]", "Pending");
    setTextIfExists("[data-intelligence-risk]", "Pending");
    setTextIfExists("[data-intelligence-profile]", "Pending");
    setTextIfExists("[data-intelligence-primary-metric]", "Pending");
    setTextIfExists("[data-intelligence-data-source]", "Pending");
    setTextIfExists("[data-intelligence-coverage]", "Pending");
    setTextIfExists("[data-intelligence-warehouse]", "Pending");
    setTextIfExists("[data-intelligence-guidance]", "Pending");
    setTextIfExists("[data-intelligence-reasoning]", "Model reasoning will appear after a prediction request completes.");

    setListIfExists("[data-intelligence-warnings]", ["No prediction warnings yet."]);
    setListIfExists("[data-intelligence-next-data]", ["Run a prediction to inspect missing data requirements."]);

    resetOutcomeLibrary();
    clearPredictionNotice();
}

async function initializeLiveMLBSelectors() {
    return loadPredictionSelectors({ force: false });
}

async function loadPlayersForSelectedTeam(teamName) {
    return renderPlayersForTeam(resolveTeam(teamName));
}

async function fetchTeamsForPrediction() {
    if (!AISP2_PREDICTION_STATE.selectorLoaded) {
        await loadPredictionSelectors({ force: false });
    }

    return AISP2_PREDICTION_STATE.teams;
}

async function fetchPlayersForTeam(teamIdentifier) {
    const team = resolveTeam(teamIdentifier);
    let players = getPlayersForTeam(team);

    if (!players.length) {
        players = await fetchPlayersForTeamFromV2(team);
    }

    return players;
}

async function fetchAvailableOutcomes() {
    return [
        "home_run",
        "hit",
        "rbi",
        "run_scored",
        "total_bases",
        "strikeout",
        "walk"
    ];
}

window.AISP2PredictionWorkbench = {
    state: AISP2_PREDICTION_STATE,
    reloadSelectors: function () {
        return loadPredictionSelectors({ force: true });
    },
    runPrediction: runPrediction,
    collectPayload: collectPredictionPayload,
    reset: resetPredictionWorkbenchDisplay,
    renderPlayersForTeam: function (teamValue) {
        return renderPlayersForTeam(resolveTeam(teamValue));
    }
};

window.AISP2PredictionSelectors = {
    state: AISP2_PREDICTION_STATE,
    reload: function () {
        return loadPredictionSelectors({ force: true });
    },
    renderPlayersForTeam: function (teamValue) {
        return renderPlayersForTeam(resolveTeam(teamValue));
    }
};
'@ | Set-Content -Path "static\js\prediction.js" -Encoding UTF8

# Verify file was written
Get-Item "static\js\prediction.js" | Format-List FullName,Length,LastWriteTime

# Commit and push only this file
git status
git add static/js/prediction.js
git commit -m "PHASE 12 PART 5.5B | 2026-07-16 | Replace Prediction Workbench JS with Stable Runtime Selector and Python Payload Renderer"
git push origin main
git status