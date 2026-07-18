/* ============================================================
   AISP2 BASEBALL
   FILE: static/js/prediction.js
   PHASE: PHASE 12 PART 5.9
   PURPOSE:
   Clean enterprise Prediction Workbench runtime.

   RESPONSIBILITIES:
   - Load teams and players from Python bootstrap endpoints.
   - Populate Team and Player selectors.
   - Keep selector diagnostics synchronized.
   - Call POST /predict/player.
   - Fill every runtime section with real response values.
   - Label unavailable datasets honestly as Pending Ingestion.
   - Avoid old demo-only prediction logic.
   ============================================================ */


/* ============================================================
   SECTION 01 - GLOBAL STATE
   ============================================================ */

const AISP2_PREDICTION_STATE = {
    initialized: false,
    selectorLoading: false,
    selectorLoaded: false,
    predictionRunning: false,

    endpoints: {
        bootstrapPrimary: "/api/player-explorer/bootstrap",
        bootstrapV2: "/api/v2/player-explorer/bootstrap",
        prediction: "/predict/player"
    },

    teams: [],
    playersByTeam: {},
    teamIndex: {},
    selectedTeam: null,
    selectedPlayers: [],
    selectorSource: "Pending",
    fallbackChain: [],
    warnings: [],
    diagnostics: {},

    lastPrediction: null,
    lastError: null
};


/* ============================================================
   SECTION 02 - BOOT
   ============================================================ */

document.addEventListener("DOMContentLoaded", function() {
    initializeAISP2PredictionWorkbench();
});


async function initializeAISP2PredictionWorkbench() {
    if (AISP2_PREDICTION_STATE.initialized) {
        return;
    }

    AISP2_PREDICTION_STATE.initialized = true;

    hydrateEndpointsFromTemplate();
    bindPredictionEvents();
    resetPredictionDisplay();

    await loadPredictionSelectors({ force: true });
}


/* ============================================================
   SECTION 03 - ENDPOINT HYDRATION
   ============================================================ */

function hydrateEndpointsFromTemplate() {
    const shell =
        document.querySelector("[data-page='prediction-workbench']") ||
        document.querySelector(".app-shell");

    if (!shell || !shell.dataset) {
        return;
    }

    if (shell.dataset.bootstrapEndpoint) {
        AISP2_PREDICTION_STATE.endpoints.bootstrapPrimary =
            shell.dataset.bootstrapEndpoint;
    }

    if (shell.dataset.v2BootstrapEndpoint) {
        AISP2_PREDICTION_STATE.endpoints.bootstrapV2 =
            shell.dataset.v2BootstrapEndpoint;
    }

    if (shell.dataset.predictionEndpoint) {
        AISP2_PREDICTION_STATE.endpoints.prediction =
            shell.dataset.predictionEndpoint;
    }
}


/* ============================================================
   SECTION 04 - DOM HELPERS
   ============================================================ */

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


function getRefreshButton() {
    return qs("[data-selector-refresh]");
}


function selectedOption(selectElement) {
    if (
        !selectElement ||
        !selectElement.selectedOptions ||
        selectElement.selectedOptions.length === 0
    ) {
        return null;
    }

    return selectElement.selectedOptions[0];
}


function setText(selector, value) {
    const text =
        value === null ||
        value === undefined ||
        value === ""
            ? "Pending"
            : String(value);

    qsa(selector).forEach(function(element) {
        element.textContent = text;
    });
}


function setList(selector, values) {
    const items =
        Array.isArray(values) && values.length
            ? values
            : ["No items reported."];

    qsa(selector).forEach(function(element) {
        element.innerHTML = "";

        items.forEach(function(item) {
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


function clearSelect(selectElement, label) {
    if (!selectElement) {
        return;
    }

    selectElement.innerHTML = "";

    const option = document.createElement("option");
    option.value = "";
    option.textContent = label || "Pending";
    selectElement.appendChild(option);
}


function addOption(selectElement, value, label, dataset) {
    if (!selectElement || value === null || value === undefined || !label) {
        return;
    }

    const option = document.createElement("option");
    option.value = String(value);
    option.textContent = String(label);

    if (dataset && typeof dataset === "object") {
        Object.keys(dataset).forEach(function(key) {
            if (dataset[key] !== null && dataset[key] !== undefined) {
                option.dataset[key] = String(dataset[key]);
            }
        });
    }

    selectElement.appendChild(option);
}


/* ============================================================
   SECTION 05 - VALUE HELPERS
   ============================================================ */

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
        .replace(/\w\S*/g, function(word) {
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
        String(value || "Runtime")
            .replace(/api/gi, "API")
            .replace(/mlb/gi, "MLB")
    );
}


function isInvalidSelectorValue(value) {
    const text = normalizeText(value);

    return (
        !text ||
        text.includes("loading") ||
        text.includes("pending") ||
        text.includes("unavailable") ||
        text.includes("select a") ||
        text.includes("no players")
    );
}


/* ============================================================
   SECTION 06 - EVENT BINDING
   ============================================================ */

function bindPredictionEvents() {
    const form = qs("[data-prediction-form]");

    if (form && !form.dataset.aisp2Bound) {
        form.addEventListener("submit", function(event) {
            event.preventDefault();
            runPrediction();
        });

        form.dataset.aisp2Bound = "true";
    }

    const button = getPredictionButton();

    if (button && !button.dataset.aisp2Bound) {
        button.addEventListener("click", function(event) {
            event.preventDefault();
            runPrediction();
        });

        button.dataset.aisp2Bound = "true";
    }

    const resetButton = getResetButton();

    if (resetButton && !resetButton.dataset.aisp2Bound) {
        resetButton.addEventListener("click", function(event) {
            event.preventDefault();
            resetPredictionDisplay();
            updateSelectedContextPreview();
        });

        resetButton.dataset.aisp2Bound = "true";
    }

    const refreshButton = getRefreshButton();

    if (refreshButton && !refreshButton.dataset.aisp2Bound) {
        refreshButton.addEventListener("click", async function(event) {
            event.preventDefault();
            await loadPredictionSelectors({ force: true });
        });

        refreshButton.dataset.aisp2Bound = "true";
    }

    const teamSelector = getTeamSelector();

    if (teamSelector && !teamSelector.dataset.aisp2Bound) {
        teamSelector.addEventListener("change", async function() {
            await handleTeamChange();
        });

        teamSelector.dataset.aisp2Bound = "true";
    }

    const playerSelector = getPlayerSelector();

    if (playerSelector && !playerSelector.dataset.aisp2Bound) {
        playerSelector.addEventListener("change", function() {
            updateSelectedContextPreview();
        });

        playerSelector.dataset.aisp2Bound = "true";
    }

    const outcomeSelector = getOutcomeSelector();

    if (outcomeSelector && !outcomeSelector.dataset.aisp2Bound) {
        outcomeSelector.addEventListener("change", function() {
            updateSelectedContextPreview();
        });

        outcomeSelector.dataset.aisp2Bound = "true";
    }
}


async function handleTeamChange() {
    const teamSelector = getTeamSelector();
    const team = resolveTeam(teamSelector ? teamSelector.value : "");

    await renderPlayersForTeam(team);

    updateSelectedContextPreview();
}


/* ============================================================
   SECTION 07 - FETCH HELPERS
   ============================================================ */

async function fetchJson(endpoint) {
    const response = await fetch(endpoint, {
        method: "GET",
        headers: {
            "Accept": "application/json"
        }
    });

    let payload = null;

    try {
        payload = await response.json();
    } catch (error) {
        throw new Error(endpoint + " returned invalid JSON.");
    }

    if (!response.ok) {
        throw new Error(
            payload.detail ||
            payload.message ||
            payload.error ||
            endpoint + " returned HTTP " + response.status
        );
    }

    return payload;
}


async function fetchBootstrapPayload() {
    const primaryEndpoint = AISP2_PREDICTION_STATE.endpoints.bootstrapPrimary;
    const v2Endpoint = AISP2_PREDICTION_STATE.endpoints.bootstrapV2;

    try {
        const primary = await fetchJson(primaryEndpoint);
        primary.__endpoint = primaryEndpoint;

        const normalized = normalizeBootstrapPayload(primary);

        if (normalized.teams.length > 0) {
            return primary;
        }

        throw new Error("Primary bootstrap returned zero teams.");
    } catch (primaryError) {
        try {
            const v2 = await fetchJson(v2Endpoint);
            v2.__endpoint = v2Endpoint;
            v2.__primary_error = primaryError.message;
            return v2;
        } catch (v2Error) {
            return buildEmergencyBootstrap(primaryError, v2Error);
        }
    }
}


function buildEmergencyBootstrap(primaryError, v2Error) {
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


/* ============================================================
   SECTION 08 - BOOTSTRAP NORMALIZATION
   ============================================================ */

function normalizeBootstrapPayload(payload) {
    const teams = normalizeTeams(payload.teams || []);
    const playersByTeam = normalizePlayersByTeam(
        payload.players_by_team ||
        payload.playersByTeam ||
        {}
    );

    const source =
        payload.bootstrap_source ||
        payload.selector_source ||
        payload.source ||
        payload.__endpoint ||
        "database_or_api";

    const fallbackChain =
        Array.isArray(payload.fallback_chain)
            ? payload.fallback_chain
            : buildFallbackChain(payload);

    const warnings =
        Array.isArray(payload.warnings)
            ? payload.warnings
            : [];

    return {
        raw: payload,
        teams: teams,
        playersByTeam: playersByTeam,
        source: source,
        fallbackChain: fallbackChain,
        warnings: warnings,
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


function normalizeTeams(rawTeams) {
    if (!Array.isArray(rawTeams)) {
        return [];
    }

    return rawTeams
        .map(normalizeTeam)
        .filter(Boolean)
        .sort(function(a, b) {
            return a.name.localeCompare(b.name);
        });
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

    Object.keys(rawPlayersByTeam).forEach(function(teamKey) {
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
        .map(function(player) {
            if (!player || typeof player !== "object") {
                return null;
            }

            const fullName =
                player.full_name ||
                player.name ||
                player.player_name ||
                player.fullName;

            if (!fullName) {
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
                fullName;

            const dedupeKey =
                compactText(fullName) + "|" + String(mlbPlayerId || id);

            if (seen.has(dedupeKey)) {
                return null;
            }

            seen.add(dedupeKey);

            return {
                id: String(id),
                mlb_player_id: mlbPlayerId !== null && mlbPlayerId !== undefined ? String(mlbPlayerId) : "",
                full_name: String(fullName),
                name: String(fullName),
                position: player.position || player.position_name || "",
                position_code: player.position_code || player.positionCode || "",
                team_id: player.team_id || player.current_team_id || "",
                source: player.source || "bootstrap"
            };
        })
        .filter(Boolean)
        .sort(function(a, b) {
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
        chain.push("selector_runtime");
    }

    return chain;
}


function countUniquePlayers(playersByTeam) {
    const seen = new Set();

    Object.keys(playersByTeam || {}).forEach(function(teamKey) {
        const players = playersByTeam[teamKey];

        if (!Array.isArray(players)) {
            return;
        }

        players.forEach(function(player) {
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


/* ============================================================
   SECTION 09 - TEAM INDEXING
   ============================================================ */

function buildTeamIndex(teams) {
    AISP2_PREDICTION_STATE.teamIndex = {};

    teams.forEach(function(team) {
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

        keys.forEach(function(key) {
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

    keys.push(
        value,
        normalizeText(value),
        compactText(value)
    );

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


/* ============================================================
   SECTION 10 - SELECTOR RENDERING
   ============================================================ */

async function loadPredictionSelectors(options) {
    const force = options && options.force;

    if (
        AISP2_PREDICTION_STATE.selectorLoading ||
        (AISP2_PREDICTION_STATE.selectorLoaded && !force)
    ) {
        return;
    }

    AISP2_PREDICTION_STATE.selectorLoading = true;

    setText("[data-selector-health]", "Loading");
    setText("[data-selector-state]", "Loading");
    setText("[data-team-selector-note]", "Loading teams...");
    setText("[data-player-selector-note]", "Loading players...");
    clearSelect(getPlayerSelector(), "Loading players...");

    try {
        const rawPayload = await fetchBootstrapPayload();
        const normalized = normalizeBootstrapPayload(rawPayload);

        AISP2_PREDICTION_STATE.teams = normalized.teams;
        AISP2_PREDICTION_STATE.playersByTeam = normalized.playersByTeam;
        AISP2_PREDICTION_STATE.selectorSource = normalized.source;
        AISP2_PREDICTION_STATE.fallbackChain = normalized.fallbackChain;
        AISP2_PREDICTION_STATE.warnings = normalized.warnings;
        AISP2_PREDICTION_STATE.diagnostics = normalized.diagnostics;
        AISP2_PREDICTION_STATE.selectedTeam =
            normalized.defaultTeam ||
            normalized.teams[0] ||
            null;

        buildTeamIndex(normalized.teams);
        renderTeamSelector();

        const teamSelector = getTeamSelector();
        const selectedTeam =
            resolveTeam(teamSelector ? teamSelector.value : "") ||
            AISP2_PREDICTION_STATE.selectedTeam;

        renderPlayersForTeam(selectedTeam);

        AISP2_PREDICTION_STATE.selectorLoaded = true;
        AISP2_PREDICTION_STATE.selectorLoading = false;

        updateSelectorDiagnostics();
        updateSelectedContextPreview();

    } catch (error) {
        AISP2_PREDICTION_STATE.selectorLoaded = false;
        AISP2_PREDICTION_STATE.selectorLoading = false;
        AISP2_PREDICTION_STATE.lastError = error;

        clearSelect(getPlayerSelector(), "Player list unavailable");
        setText("[data-selector-health]", "Failed");
        setText("[data-selector-state]", "Failed");
        setText("[data-selector-warning]", error.message || "Selector loading failed.");
    }
}


function renderTeamSelector() {
    const teamSelector = getTeamSelector();

    if (!teamSelector) {
        return;
    }

    teamSelector.innerHTML = "";

    if (!AISP2_PREDICTION_STATE.teams.length) {
        clearSelect(teamSelector, "No teams loaded");
        return;
    }

    AISP2_PREDICTION_STATE.teams.forEach(function(team) {
        addOption(
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

    const selectedTeam =
        AISP2_PREDICTION_STATE.selectedTeam ||
        AISP2_PREDICTION_STATE.teams[0];

    if (selectedTeam && selectedTeam.name) {
        teamSelector.value = selectedTeam.name;
    }
}


function renderPlayersForTeam(team) {
    const playerSelector = getPlayerSelector();

    if (!playerSelector) {
        return;
    }

    playerSelector.innerHTML = "";

    if (!team) {
        clearSelect(playerSelector, "Select a team first");
        return;
    }

    const players = getPlayersForTeam(team);

    if (!players.length) {
        clearSelect(playerSelector, "No players loaded for this team");
        setText("[data-player-selector-note]", "No players returned for " + team.name + ".");
        updateSelectorDiagnostics();
        return;
    }

    players.forEach(function(player) {
        addOption(
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

    setText("[data-player-selector-note]", "Selected player: " + playerSelector.value + ".");
    updateSelectorDiagnostics();
}


function updateSelectorDiagnostics() {
    const teamCount = AISP2_PREDICTION_STATE.teams.length;
    const playerCount = countUniquePlayers(AISP2_PREDICTION_STATE.playersByTeam);
    const source = formatSource(AISP2_PREDICTION_STATE.selectorSource);
    const fallbackChain =
        Array.isArray(AISP2_PREDICTION_STATE.fallbackChain)
            ? AISP2_PREDICTION_STATE.fallbackChain.join(" -> ")
            : "selector_runtime";

    setText("[data-selector-health]", "Ready");
    setText("[data-selector-state]", "Ready");
    setText("[data-teams-loaded]", teamCount);
    setText("[data-players-loaded]", playerCount);
    setText("[data-bootstrap-source]", source);
    setText("[data-selector-source]", source);
    setText("[data-fallback-chain]", fallbackChain);
    setText("[data-team-selector-note]", "Selected team: " + (getTeamSelector() ? getTeamSelector().value : "Pending") + ".");
    setText("[data-selector-warning]", "Runtime selectors are populated and ready.");

    const diagnostics = AISP2_PREDICTION_STATE.diagnostics || {};

    if (
        diagnostics.database_team_count === 0 &&
        diagnostics.database_player_count === 0
    ) {
        setText("[data-warehouse-status]", "Render DB Empty");
    } else {
        setText("[data-warehouse-status]", "Selector Ready");
    }
}


/* ============================================================
   SECTION 11 - PAYLOAD
   ============================================================ */

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

    if (!payload.team || isInvalidSelectorValue(payload.team)) {
        errors.push("Select a valid team before running a prediction.");
    }

    if (!payload.player || isInvalidSelectorValue(payload.player)) {
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
    const outcomeSelector = getOutcomeSelector();
    const outcomeOption = selectedOption(outcomeSelector);

    if (payload.player && !isInvalidSelectorValue(payload.player)) {
        setText("[data-result-player]", payload.player);
        setText("[data-intelligence-summary]", "Ready to generate prediction intelligence for " + payload.player + ".");
    } else {
        setText("[data-result-player]", "Choose Player");
        setText("[data-intelligence-summary]", "Select a team, player, and outcome to generate AISP2 prediction intelligence.");
    }

    setText("[data-result-team]", payload.team || "Team Pending");
    setText("[data-result-outcome]", outcomeOption ? outcomeOption.textContent : titleCase(payload.outcome));
}


/* ============================================================
   SECTION 12 - PREDICTION REQUEST
   ============================================================ */

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

    try {
        const response = await fetch(AISP2_PREDICTION_STATE.endpoints.prediction, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                team: payload.team,
                player: payload.player,
                outcome: payload.outcome
            })
        });

        let result = null;

        try {
            result = await response.json();
        } catch (error) {
            throw new Error("Prediction endpoint returned invalid JSON.");
        }

        if (!response.ok) {
            throw new Error(
                result.detail ||
                result.message ||
                result.error ||
                "Prediction request failed."
            );
        }

        AISP2_PREDICTION_STATE.lastPrediction = result;
        AISP2_PREDICTION_STATE.lastError = null;

        renderPredictionResult(result);
    } catch (error) {
        AISP2_PREDICTION_STATE.lastError = error;
        renderPredictionError(error.message || "Prediction failed.");
    } finally {
        setPredictionLoading(false);
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
        setText("[data-intelligence-summary]", "Running prediction request...");
        setText("[data-intelligence-reasoning]", "AISP2 is requesting Python model output from /predict/player.");
    }
}


/* ============================================================
   SECTION 13 - RESULT RENDERING
   ============================================================ */

function renderPredictionResult(result) {
    const prediction = result.prediction || {};
    const intelligence = result.intelligence || {};
    const supporting = result.supporting_context || {};
    const outcome = result.outcome || {};
    const dataStatus = result.data_status || {};
    const team =
        result.team && typeof result.team === "object"
            ? result.team
            : { name: result.team };

    const probability =
        prediction.estimated_probability ??
        prediction.probability ??
        result.probability;

    const confidence =
        prediction.confidence ??
        result.confidence;

    const tier =
        intelligence.tier ||
        prediction.tier ||
        "Identity-Aware Baseline";

    const risk =
        intelligence.risk_profile ||
        prediction.risk_profile ||
        "Warehouse Pending";

    const outcomeProfile =
        intelligence.outcome_profile ||
        supporting.player_style ||
        "Outcome Runtime Profile";

    const primaryMetric =
        intelligence.primary_metric ||
        supporting.primary_metric ||
        "Primary Runtime Feature";

    const model =
        prediction.model ||
        result.model ||
        "AISP2 Identity-Aware Baseline";

    const dataSource =
        intelligence.data_source ||
        prediction.prediction_source ||
        "Prediction Runtime";

    const coverage =
        intelligence.data_coverage ??
        prediction.data_coverage ??
        dataStatus.data_coverage ??
        0;

    const warehouse =
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
        prediction.plate_appearances ??
        "Pending Ingestion";

    const explanation =
        intelligence.ai_explanation ||
        supporting.ai_explanation ||
        result.explanation ||
        (
            "AISP2 generated this runtime prediction using the currently available selector identity, outcome, and backend prediction response. Advanced warehouse, matchup, weather, and Monte Carlo data remain pending until those datasets are connected."
        );

    setText("[data-result-player]", result.player || collectPredictionPayload().player || "Unknown Player");
    setText("[data-result-team]", team.name || collectPredictionPayload().team || "Unknown Team");
    setText("[data-result-outcome]", outcome.label || titleCase(outcome.key || collectPredictionPayload().outcome || "Prediction"));
    setText("[data-result-probability]", formatPercent(probability));
    setText("[data-result-confidence]", formatPercent(confidence, "Confidence Pending"));
    setText("[data-result-tier]", tier);
    setText("[data-result-risk]", risk);
    setText("[data-result-profile]", outcomeProfile);
    setText("[data-result-supporting-metric]", primaryMetric);
    setText("[data-result-model]", model);
    setText("[data-result-model-secondary]", model);
    setText("[data-result-style]", supporting.player_style || outcomeProfile);
    setText("[data-result-form]", supporting.recent_form || "Pending Ingestion");
    setText("[data-result-metric]", primaryMetric);
    setText("[data-result-source]", formatSource(dataSource));
    setText("[data-result-data-coverage]", formatPercent(coverage));
    setText("[data-result-sample-size]", sampleSize);
    setText("[data-result-warehouse-status]", warehouse);
    setText("[data-result-ai-explanation]", explanation);

    setText("[data-intelligence-summary]", explanation);
    setText("[data-intelligence-tier]", tier);
    setText("[data-intelligence-risk]", risk);
    setText("[data-intelligence-profile]", outcomeProfile);
    setText("[data-intelligence-primary-metric]", primaryMetric);
    setText("[data-intelligence-data-source]", formatSource(dataSource));
    setText("[data-intelligence-coverage]", formatPercent(coverage));
    setText("[data-intelligence-warehouse]", warehouse);
    setText(
        "[data-intelligence-guidance]",
        intelligence.model_guidance ||
        "Use this as a transparent model estimate while warehouse and matchup data continue to be connected."
    );
    setText("[data-intelligence-reasoning]", explanation);
    setText("[data-warehouse-status]", warehouse);

    setList(
        "[data-intelligence-warnings]",
        intelligence.warnings ||
        result.warnings ||
        buildWarnings(warehouse, dataStatus)
    );

    setList(
        "[data-intelligence-next-data]",
        intelligence.next_data_needed ||
        result.next_data_needed ||
        buildNextDataNeeded(warehouse, dataStatus)
    );

    renderOutcomeLibrary(result, probability, outcome.key);
    renderTransparentPendingSections(model);
}


function buildWarnings(warehouse, dataStatus) {
    const warnings = [];

    if (warehouse === "Pending Ingestion") {
        warnings.push("Advanced warehouse data is pending ingestion.");
    }

    if (
        dataStatus &&
        dataStatus.database &&
        dataStatus.database.player_count === 0
    ) {
        warnings.push("The deployed database reports zero players.");
    }

    if (!warnings.length) {
        warnings.push("No critical runtime warnings detected.");
    }

    return warnings;
}


function buildNextDataNeeded(warehouse, dataStatus) {
    if (
        dataStatus &&
        Array.isArray(dataStatus.missing_sources) &&
        dataStatus.missing_sources.length
    ) {
        return dataStatus.missing_sources.map(function(source) {
            return "Load missing source: " + titleCase(source);
        });
    }

    const items = [];

    if (warehouse === "Pending Ingestion") {
        items.push("Connect Statcast warehouse tables.");
    }

    items.push("Connect schedule and probable pitcher data.");
    items.push("Connect matchup, ballpark, and weather context.");
    items.push("Connect Monte Carlo simulation engine.");

    return items;
}


function renderOutcomeLibrary(result, probability, outcomeKey) {
    const key = outcomeKey || (result.outcome || {}).key || collectPredictionPayload().outcome;

    const selectorMap = {
        home_run: "[data-prop-home-run]",
        hit: "[data-prop-hit]",
        rbi: "[data-prop-rbi]",
        run: "[data-prop-run-scored]",
        run_scored: "[data-prop-run-scored]",
        total_bases: "[data-prop-total-bases]",
        strikeout: "[data-prop-strikeout]"
    };

    if (selectorMap[key]) {
        setText(selectorMap[key], formatPercent(probability));
    }
}


function renderTransparentPendingSections(model) {
    setText("[data-runtime-mode]", "Transparent Runtime");
    setText("[data-model-state]", model || "Baseline Runtime");
}


/* ============================================================
   SECTION 14 - ERROR AND RESET
   ============================================================ */

function renderPredictionError(message) {
    const text = message || "Prediction failed.";

    setText("[data-prediction-error]", text);
    setText("[data-selector-warning]", text);
    setText("[data-intelligence-summary]", text);
    setText("[data-intelligence-reasoning]", text);
    setList("[data-intelligence-warnings]", [text]);

    const panel = qs("[data-prediction-error-panel]");

    if (panel) {
        panel.classList.remove("is-hidden");
        panel.classList.add("visible");
    }
}


function resetPredictionDisplay() {
    AISP2_PREDICTION_STATE.lastPrediction = null;
    AISP2_PREDICTION_STATE.lastError = null;

    setText("[data-result-player]", "Choose Player");
    setText("[data-result-team]", "Select Team");
    setText("[data-result-outcome]", "Select Outcome");
    setText("[data-result-probability]", "—");
    setText("[data-result-confidence]", "Confidence Pending");
    setText("[data-result-tier]", "Pending");
    setText("[data-result-risk]", "Pending");
    setText("[data-result-profile]", "Pending");
    setText("[data-result-supporting-metric]", "Pending");
    setText("[data-result-model]", "Pending");
    setText("[data-result-model-secondary]", "Pending");
    setText("[data-result-style]", "Pending");
    setText("[data-result-form]", "Pending");
    setText("[data-result-metric]", "Pending");
    setText("[data-result-source]", "Pending");
    setText("[data-result-data-coverage]", "Pending");
    setText("[data-result-sample-size]", "Pending");
    setText("[data-result-warehouse-status]", "Pending");
    setText("[data-result-ai-explanation]", "Select a player and outcome to generate AISP2 baseball intelligence.");

    setText("[data-intelligence-summary]", "Select a team, player, and outcome to generate AISP2 prediction intelligence.");
    setText("[data-intelligence-tier]", "Pending");
    setText("[data-intelligence-risk]", "Pending");
    setText("[data-intelligence-profile]", "Pending");
    setText("[data-intelligence-primary-metric]", "Pending");
    setText("[data-intelligence-data-source]", "Pending");
    setText("[data-intelligence-coverage]", "Pending");
    setText("[data-intelligence-warehouse]", "Pending");
    setText("[data-intelligence-guidance]", "Pending");
    setText("[data-intelligence-reasoning]", "Model reasoning will appear after a prediction request completes.");

    setList("[data-intelligence-warnings]", ["No prediction warnings yet."]);
    setList("[data-intelligence-next-data]", ["Run a prediction to inspect missing data requirements."]);

    setText("[data-prop-home-run]", "Pending");
    setText("[data-prop-hit]", "Pending");
    setText("[data-prop-rbi]", "Pending");
    setText("[data-prop-run-scored]", "Pending");
    setText("[data-prop-total-bases]", "Pending");
    setText("[data-prop-strikeout]", "Pending");

    const panel = qs("[data-prediction-error-panel]");

    if (panel) {
        panel.classList.add("is-hidden");
        panel.classList.remove("visible");
    }
}


/* ============================================================
   SECTION 15 - DEBUG EXPORTS
   ============================================================ */

window.AISP2PredictionWorkbench = {
    state: AISP2_PREDICTION_STATE,
    reloadSelectors: function() {
        return loadPredictionSelectors({ force: true });
    },
    runPrediction: runPrediction,
    collectPayload: collectPredictionPayload,
    reset: resetPredictionDisplay,
    renderPlayersForTeam: function(teamValue) {
        return renderPlayersForTeam(resolveTeam(teamValue));
    }
};

window.AISP2PredictionSelectors = {
    state: AISP2_PREDICTION_STATE,
    reload: function() {
        return loadPredictionSelectors({ force: true });
    },
    renderPlayersForTeam: function(teamValue) {
        return renderPlayersForTeam(resolveTeam(teamValue));
    }
};


/* ============================================================
   AISP2 BASEBALL
   FILE: static/js/prediction.js
   PHASE 14 PART 4.0 - PREDICTION ACCOUNT INTEGRATION

   PURPOSE:
   Connect Prediction Workbench to authenticated account APIs.

   APIs:
   - POST /api/account/searches
   - POST /api/account/follow/player
   - POST /api/account/follow/team
   - GET  /api/auth/me
   - POST /predict/player now persists prediction history when logged in

   SECURITY:
   - Does not read HttpOnly cookies.
   - Uses same-origin credentials.
   - If logged out, backend returns auth error and UI points to login.
   ============================================================ */

(function initializeAISP2PredictionAccountIntegration() {
    "use strict";

    const VERSION = "phase_14_part_4_0_prediction_account_integration";

    const state = {
        account: null,
        authenticated: false,
        lastTeam: null,
        lastPlayer: null,
        lastOutcome: null,
        lastPrediction: null,
        lastSavedSearchKey: null,
        initializedAt: new Date().toISOString()
    };

    function $(selector) {
        return document.querySelector(selector);
    }

    function all(selector) {
        return Array.from(document.querySelectorAll(selector));
    }

    function safeText(value, fallback) {
        const text = String(value ?? "").trim();
        return text || fallback || "";
    }

    function normalize(value) {
        return safeText(value, "").toLowerCase().replace(/\s+/g, " ").trim();
    }

    function setStatus(message, kind) {
        const target = $("[data-prediction-account-status]");
        if (!target) {
            return;
        }

        target.textContent = message;
        target.dataset.status = kind || "info";
    }

    function getSelectedText(select) {
        if (!select) {
            return "";
        }

        const option = select.options && select.selectedIndex >= 0
            ? select.options[select.selectedIndex]
            : null;

        return safeText(
            option ? option.textContent : select.value,
            safeText(select.value, "")
        );
    }

    function findTeamControl() {
        return (
            $("[data-team-select]") ||
            $("#teamSelect") ||
            $("#team-select") ||
            $("select[name='team']") ||
            $("select[data-prediction-team]")
        );
    }

    function findPlayerControl() {
        return (
            $("[data-player-select]") ||
            $("#playerSelect") ||
            $("#player-select") ||
            $("select[name='player']") ||
            $("input[name='player']") ||
            $("select[data-prediction-player]")
        );
    }

    function findOutcomeControl() {
        return (
            $("[data-outcome-select]") ||
            $("#outcomeSelect") ||
            $("#outcome-select") ||
            $("select[name='outcome']") ||
            $("select[data-prediction-outcome]")
        );
    }

    function getCurrentSelection() {
        const teamControl = findTeamControl();
        const playerControl = findPlayerControl();
        const outcomeControl = findOutcomeControl();

        const teamValue = teamControl ? teamControl.value : "";
        const playerValue = playerControl ? playerControl.value : "";
        const outcomeValue = outcomeControl ? outcomeControl.value : "";

        const teamName = getSelectedText(teamControl);
        const playerName = getSelectedText(playerControl);
        const outcomeLabel = getSelectedText(outcomeControl);

        return {
            team_id: /^\d+$/.test(String(teamValue || "")) ? Number(teamValue) : null,
            team_name: safeText(teamName || teamValue, null),
            player_id: /^\d+$/.test(String(playerValue || "")) ? Number(playerValue) : null,
            player_name: safeText(playerName || playerValue, null),
            outcome_key: safeText(outcomeValue, "home_run"),
            outcome_label: safeText(outcomeLabel || outcomeValue, "Home Run")
        };
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, {
            credentials: "same-origin",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                ...(options && options.headers ? options.headers : {})
            },
            ...(options || {})
        });

        let payload = null;

        try {
            payload = await response.json();
        } catch (error) {
            payload = {
                success: false,
                detail: "Non-JSON response received."
            };
        }

        if (!response.ok) {
            const message = payload.detail || payload.error || `Request failed with HTTP ${response.status}`;
            const wrapped = new Error(message);
            wrapped.status = response.status;
            wrapped.payload = payload;
            throw wrapped;
        }

        return payload;
    }

    async function loadAccount() {
        try {
            const payload = await fetchJson("/api/auth/me", { method: "GET" });
            state.account = payload.account || payload.user || payload;
            state.authenticated = Boolean(payload.authenticated || payload.success || state.account);
            setStatus("Account connected. Prediction memory is enabled.", "good");
            return state.account;
        } catch (error) {
            state.account = null;
            state.authenticated = false;
            setStatus("Log in to save searches, follow players, and track prediction history.", "warn");
            return null;
        }
    }

    function loginHint() {
        setStatus("Login required. Use the Login link or ask the chatbot: login", "warn");
    }

    async function saveSearch(reason) {
        const selection = getCurrentSelection();

        if (!selection.player_name && !selection.team_name) {
            return null;
        }

        const key = [
            normalize(selection.team_name),
            normalize(selection.player_name),
            normalize(selection.outcome_key),
            reason || "manual"
        ].join("|");

        if (reason !== "manual" && key === state.lastSavedSearchKey) {
            return null;
        }

        state.lastSavedSearchKey = key;

        try {
            const payload = await fetchJson("/api/account/searches", {
                method: "POST",
                body: JSON.stringify({
                    query: [
                        selection.team_name,
                        selection.player_name,
                        selection.outcome_label
                    ].filter(Boolean).join(" "),
                    search_type: "prediction_workbench",
                    source_page: "prediction_workbench",
                    entity_type: selection.player_name ? "player_prediction" : "team",
                    entity_id: selection.player_id || selection.team_id || null,
                    entity_name: selection.player_name || selection.team_name || null,
                    player_id: selection.player_id,
                    player_name: selection.player_name,
                    team_id: selection.team_id,
                    team_name: selection.team_name,
                    outcome_key: selection.outcome_key,
                    outcome_label: selection.outcome_label,
                    result_count: 1,
                    is_saved: true,
                    metadata: {
                        phase: "Phase 14 Part 4.0",
                        reason: reason || "manual",
                        frontend_version: VERSION
                    }
                })
            });

            setStatus("Search saved to your account memory.", "good");
            return payload;
        } catch (error) {
            if (error.status === 401 || error.status === 403) {
                loginHint();
                return null;
            }

            setStatus(`Save search failed: ${error.message}`, "danger");
            return null;
        }
    }

    async function followPlayer() {
        const selection = getCurrentSelection();

        if (!selection.player_name && !selection.player_id) {
            setStatus("Choose a player before following.", "warn");
            return null;
        }

        try {
            const payload = await fetchJson("/api/account/follow/player", {
                method: "POST",
                body: JSON.stringify({
                    player_id: selection.player_id,
                    player_name: selection.player_name,
                    team_id: selection.team_id,
                    team_name: selection.team_name,
                    source_page: "prediction_workbench",
                    alert_preferences: {
                        stat_changes: true,
                        prediction_updates: true,
                        game_day_context: true
                    },
                    metadata: {
                        phase: "Phase 14 Part 4.0",
                        frontend_version: VERSION
                    }
                })
            });

            setStatus("Player followed. This player is now linked to your account.", "good");
            return payload;
        } catch (error) {
            if (error.status === 401 || error.status === 403) {
                loginHint();
                return null;
            }

            setStatus(`Follow player failed: ${error.message}`, "danger");
            return null;
        }
    }

    async function followTeam() {
        const selection = getCurrentSelection();

        if (!selection.team_name && !selection.team_id) {
            setStatus("Choose a team before following.", "warn");
            return null;
        }

        try {
            const payload = await fetchJson("/api/account/follow/team", {
                method: "POST",
                body: JSON.stringify({
                    team_id: selection.team_id,
                    team_name: selection.team_name,
                    source_page: "prediction_workbench",
                    alert_preferences: {
                        stat_changes: true,
                        prediction_updates: true,
                        game_day_context: true
                    },
                    metadata: {
                        phase: "Phase 14 Part 4.0",
                        frontend_version: VERSION
                    }
                })
            });

            setStatus("Team followed. This team is now linked to your account.", "good");
            return payload;
        } catch (error) {
            if (error.status === 401 || error.status === 403) {
                loginHint();
                return null;
            }

            setStatus(`Follow team failed: ${error.message}`, "danger");
            return null;
        }
    }

    function attachSelectionListeners() {
        const controls = [
            findTeamControl(),
            findPlayerControl(),
            findOutcomeControl()
        ].filter(Boolean);

        controls.forEach((control) => {
            if (control.dataset.accountMemoryListener === "true") {
                return;
            }

            control.dataset.accountMemoryListener = "true";

            control.addEventListener("change", function handleAccountMemorySelectionChange() {
                window.clearTimeout(control.__aisp2AccountMemoryTimer);
                control.__aisp2AccountMemoryTimer = window.setTimeout(function delayedSaveSearch() {
                    saveSearch("selection_change");
                }, 650);
            });
        });
    }

    function attachButtonListeners() {
        all("[data-account-action]").forEach((button) => {
            if (button.dataset.accountActionAttached === "true") {
                return;
            }

            button.dataset.accountActionAttached = "true";

            button.addEventListener("click", async function handlePredictionAccountAction() {
                const action = button.dataset.accountAction;

                if (action === "save-search") {
                    await saveSearch("manual");
                }

                if (action === "follow-player") {
                    await followPlayer();
                }

                if (action === "follow-team") {
                    await followTeam();
                }
            });
        });
    }

    function patchFetchForPredictionHistory() {
        if (window.__AISP2_PREDICTION_ACCOUNT_FETCH_PATCHED__) {
            return;
        }

        if (typeof window.fetch !== "function") {
            return;
        }

        window.__AISP2_PREDICTION_ACCOUNT_FETCH_PATCHED__ = true;

        const originalFetch = window.fetch;

        window.fetch = function patchedPredictionAccountFetch(resource, options) {
            const responsePromise = originalFetch.apply(this, arguments);

            try {
                const url = String(
                    typeof resource === "string"
                        ? resource
                        : resource && resource.url
                            ? resource.url
                            : ""
                );

                if (url.indexOf("/predict/player") >= 0) {
                    responsePromise.then(function inspectPredictionResponse(response) {
                        try {
                            response.clone().json().then(function handlePredictionPayload(payload) {
                                state.lastPrediction = payload;

                                if (payload && payload.account_history && payload.account_history.saved) {
                                    setStatus("Prediction saved to your account ledger.", "good");
                                } else if (payload && payload.account_history && payload.account_history.reason === "not_authenticated") {
                                    setStatus("Prediction ran. Log in to save it to your ledger.", "warn");
                                } else {
                                    setStatus("Prediction completed. Account history status checked.", "info");
                                }
                            }).catch(function noop() {});
                        } catch (error) {
                            return null;
                        }
                        return null;
                    }).catch(function noop() {});
                }
            } catch (error) {
                return responsePromise;
            }

            return responsePromise;
        };
    }

    function injectStyles() {
        if (document.querySelector("[data-aisp2-prediction-account-style]")) {
            return;
        }

        const style = document.createElement("style");
        style.dataset.aisp2PredictionAccountStyle = "true";
        style.textContent = `
            .prediction-account-action-bar {
                margin: 18px 0;
                padding: 18px;
                border-radius: 24px;
                border: 1px solid rgba(77, 216, 255, 0.22);
                background:
                    radial-gradient(circle at 0% 0%, rgba(77, 216, 255, 0.13), transparent 38%),
                    rgba(5, 18, 38, 0.72);
                box-shadow: 0 18px 54px rgba(0, 0, 0, 0.22);
            }
            .prediction-account-action-copy strong {
                display: block;
                color: rgba(244, 251, 255, 0.96);
                font-size: 1.02rem;
            }
            .prediction-account-action-copy p {
                margin: 6px 0 0;
                color: rgba(220, 238, 250, 0.68);
                line-height: 1.45;
            }
            .prediction-account-eyebrow {
                display: inline-flex;
                margin-bottom: 8px;
                color: #73e8ff;
                font-size: 0.72rem;
                font-weight: 950;
                letter-spacing: 0.11em;
                text-transform: uppercase;
            }
            .prediction-account-actions {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 14px;
            }
            .prediction-account-button {
                min-height: 38px;
                border: 1px solid rgba(77, 216, 255, 0.28);
                border-radius: 999px;
                padding: 0 14px;
                background: rgba(255,255,255,0.055);
                color: rgba(244,251,255,0.94);
                font-weight: 900;
                cursor: pointer;
                text-decoration: none;
            }
            .prediction-account-button:hover {
                border-color: rgba(115, 232, 255, 0.54);
                color: #73e8ff;
            }
            .prediction-account-button.secondary {
                color: #8df5bd;
            }
            .prediction-account-status {
                margin-top: 12px;
                color: rgba(220, 238, 250, 0.72);
                font-size: 0.88rem;
                font-weight: 800;
            }
            .prediction-account-status[data-status="good"] { color: #8df5bd; }
            .prediction-account-status[data-status="warn"] { color: #ffe29e; }
            .prediction-account-status[data-status="danger"] { color: #ff9f9f; }
        `;
        document.head.appendChild(style);
    }

    function boot() {
        injectStyles();
        attachButtonListeners();
        attachSelectionListeners();
        patchFetchForPredictionHistory();
        loadAccount();

        window.setInterval(attachSelectionListeners, 1500);
        window.setInterval(attachButtonListeners, 1500);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.AISP2PredictionAccountIntegration = {
        version: VERSION,
        state,
        saveSearch,
        followPlayer,
        followTeam,
        getCurrentSelection,
        reloadAccount: loadAccount
    };

    window.AISP2_PREDICTION_ACCOUNT_INTEGRATION_PHASE_14_PART_4 = true;
}());


/* ============================================================
   PHASE 14 PART 7.2 - PREDICTION PAGE SCROLL RESET
   FILE: static/js/prediction.js
   PURPOSE:
   Prevent /tools/prediction from reopening halfway down the page.
   ============================================================ */

(function initializeAISP2PredictionPageScrollReset() {
    "use strict";

    try {
        if ("scrollRestoration" in window.history) {
            window.history.scrollRestoration = "manual";
        }

        function isPredictionPage() {
            const path = String(window.location.pathname || "").toLowerCase();

            return (
                path.includes("/tools/prediction") ||
                path.includes("prediction")
            );
        }

        function resetScroll() {
            if (!isPredictionPage()) {
                return;
            }

            window.requestAnimationFrame(function frameOne() {
                window.scrollTo(0, 0);

                window.requestAnimationFrame(function frameTwo() {
                    window.scrollTo(0, 0);
                });
            });
        }

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", resetScroll);
        } else {
            resetScroll();
        }

        window.addEventListener("load", resetScroll);
    } catch (error) {
        return null;
    }
}());

window.AISP2_PREDICTION_PAGE_SCROLL_RESET_PHASE_14_PART_7_2 = true;

