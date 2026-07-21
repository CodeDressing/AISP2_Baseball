/* ============================================================
   AISP2 BASEBALL INTELLIGENCE PLATFORM
   FILE: static/js/prediction.js
   PHASE: PHASE 16 PART 3C
   PURPOSE:
   Prediction Workbench frontend runtime.

   CORE FIX:
   - Stop sending incomplete player/team payloads.
   - Stop rendering JavaScript objects as [object Object].
   - Send clean scalar values:
       team_id
       mlb_team_id
       team_name
       player_id
       mlb_player_id
       player_name
       outcome_key
       outcome_label
       season
   - Use /api/prediction/workbench/run as the primary runtime endpoint.
   - Render backend-resolved player, source, sample size, and math proof.

   COMPLETION GATE:
   Browser DevTools Network payload must show clean scalar values.
   No [object Object] should appear anywhere on the Workbench.
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
        prediction: "/api/prediction/workbench/run",
        legacyPrediction: "/predict/player"
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

    lastPayload: null,
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

    /*
       Important:
       Older templates may still declare /predict/player.
       Phase 16 Part 3C intentionally routes the Workbench through
       /api/prediction/workbench/run because that endpoint carries the
       feature-builder debug contract.
    */
    if (
        shell.dataset.predictionEndpoint &&
        shell.dataset.predictionEndpoint.indexOf("/api/prediction/workbench/run") >= 0
    ) {
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


function safeDisplay(value, fallback) {
    if (value === null || value === undefined || value === "") {
        return fallback || "Pending";
    }

    if (typeof value === "object") {
        if (value.name) {
            return String(value.name);
        }

        if (value.label) {
            return String(value.label);
        }

        if (value.full_name) {
            return String(value.full_name);
        }

        if (value.player_name) {
            return String(value.player_name);
        }

        if (value.team_name) {
            return String(value.team_name);
        }

        return fallback || "Pending";
    }

    return String(value);
}


function setText(selector, value, fallback) {
    const text = safeDisplay(value, fallback);

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
            li.textContent = safeDisplay(
                item && typeof item === "object"
                    ? item.message || item.detail || item.error || JSON.stringify(item)
                    : item,
                "Pending"
            );
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

    if (typeof value === "string") {
        value = value.replace("%", "").replace(",", "").trim();
    }

    const number = Number(value);

    if (Number.isNaN(number) || !Number.isFinite(number)) {
        return null;
    }

    return number;
}


function scalarId(value) {
    if (value === null || value === undefined || value === "") {
        return "";
    }

    const text = String(value).trim();

    if (!text || text === "[object Object]") {
        return "";
    }

    return text;
}


function scalarNumberOrText(value) {
    const text = scalarId(value);

    if (!text) {
        return "";
    }

    if (/^\d+$/.test(text)) {
        return Number(text);
    }

    return text;
}


function normalizeOutcomeKey(value) {
    const raw = String(value || "home_run")
        .trim()
        .toLowerCase()
        .replace(/-/g, "_")
        .replace(/\s+/g, "_");

    const aliases = {
        hr: "home_run",
        homer: "home_run",
        home_runs: "home_run",
        hits: "hit",
        singles: "single",
        doubles: "double",
        triples: "triple",
        walks: "walk",
        bb: "walk",
        strikeouts: "strikeout",
        k: "strikeout",
        ks: "strikeout",
        runs: "run_scored",
        run: "run_scored",
        tb: "total_bases"
    };

    return aliases[raw] || raw || "home_run";
}


function formatPercent(value, fallback) {
    const number = safeNumber(value);

    if (number === null) {
        return fallback || "Pending";
    }

    return String(Number(number.toFixed(1))) + "%";
}


function formatCount(value, fallback) {
    const number = safeNumber(value);

    if (number === null) {
        return fallback || "Pending";
    }

    return String(Math.round(number));
}


function formatSource(value) {
    const source = safeDisplay(value, "Runtime");

    return titleCase(
        source
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
        text.includes("no players") ||
        text.includes("object object")
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

    renderPlayersForTeam(team);
    updateSelectedContextPreview();
}


/* ============================================================
   SECTION 07 - FETCH HELPERS
   ============================================================ */

async function fetchJson(endpoint) {
    const response = await fetch(endpoint, {
        method: "GET",
        headers: {
            Accept: "application/json"
        },
        credentials: "same-origin"
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


async function postJson(endpoint, payload) {
    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json"
        },
        credentials: "same-origin",
        body: JSON.stringify(payload)
    });

    let result = null;

    try {
        result = await response.json();
    } catch (error) {
        throw new Error(endpoint + " returned invalid JSON.");
    }

    if (!response.ok) {
        throw new Error(
            result.detail ||
            result.message ||
            result.error ||
            "Prediction request failed."
        );
    }

    return result;
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

    let playersByTeam = normalizePlayersByTeam(
        payload.players_by_team ||
        payload.playersByTeam ||
        {}
    );

    /*
       Some v2 bootstrap payloads provide teams only.
       In that case selectors still load teams, but player lists
       may require a team-specific endpoint later. This file keeps
       the primary /api/player-explorer/bootstrap route preferred
       because it usually includes players_by_team.
    */
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
        id: scalarId(id),
        team_id: scalarId(team.team_id || team.id || id),
        database_id: scalarId(team.database_id || team.id || id),
        mlb_team_id: scalarId(mlbTeamId),
        name: String(name),
        team_name: String(name),
        abbreviation: scalarId(team.abbreviation),
        club_name: scalarId(team.club_name || team.clubName),
        short_name: scalarId(team.short_name || team.shortName),
        location_name: scalarId(team.location_name || team.locationName),
        source: scalarId(team.source || "bootstrap")
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
                id: scalarId(id),
                database_id: scalarId(player.database_id || player.id || id),
                player_id: scalarId(player.player_id || player.id || id),
                mlb_player_id: scalarId(mlbPlayerId),
                full_name: String(fullName),
                name: String(fullName),
                player_name: String(fullName),
                position: scalarId(player.position || player.position_name),
                position_code: scalarId(player.position_code || player.positionCode),
                team_id: scalarId(player.team_id || player.current_team_id),
                source: scalarId(player.source || "bootstrap")
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
                    player.player_id ||
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
            team.team_id,
            team.database_id,
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
            option.dataset.databaseId,
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
        team.team_id,
        team.database_id,
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
        const optionValue = team.id || team.team_id || team.mlb_team_id || team.name;

        addOption(
            teamSelector,
            optionValue,
            team.name,
            {
                teamId: team.id || team.team_id || "",
                databaseId: team.database_id || team.id || "",
                mlbTeamId: team.mlb_team_id || "",
                teamName: team.name || "",
                abbreviation: team.abbreviation || "",
                source: team.source || ""
            }
        );
    });

    const selectedTeam =
        AISP2_PREDICTION_STATE.selectedTeam ||
        AISP2_PREDICTION_STATE.teams[0];

    if (selectedTeam) {
        teamSelector.value =
            selectedTeam.id ||
            selectedTeam.team_id ||
            selectedTeam.mlb_team_id ||
            selectedTeam.name;
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
        const optionValue =
            player.id ||
            player.player_id ||
            player.database_id ||
            player.mlb_player_id ||
            player.full_name;

        addOption(
            playerSelector,
            optionValue,
            player.full_name || player.name,
            {
                playerId: player.id || player.player_id || "",
                databaseId: player.database_id || player.id || "",
                mlbPlayerId: player.mlb_player_id || "",
                playerName: player.full_name || player.name || "",
                position: player.position || "",
                positionCode: player.position_code || "",
                teamId: player.team_id || team.id || "",
                source: player.source || ""
            }
        );
    });

    playerSelector.selectedIndex = 0;

    AISP2_PREDICTION_STATE.selectedTeam = team;
    AISP2_PREDICTION_STATE.selectedPlayers = players;

    const playerPayload = getSelectedPlayerPayload();

    setText("[data-player-selector-note]", "Selected player: " + playerPayload.player_name + ".");
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

    const currentPayload = collectPredictionPayload();

    setText("[data-selector-health]", "Ready");
    setText("[data-selector-state]", "Ready");
    setText("[data-teams-loaded]", teamCount);
    setText("[data-players-loaded]", playerCount);
    setText("[data-bootstrap-source]", source);
    setText("[data-selector-source]", source);
    setText("[data-fallback-chain]", fallbackChain);
    setText("[data-team-selector-note]", "Selected team: " + (currentPayload.team_name || "Pending") + ".");
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
   SECTION 11 - CLEAN PAYLOAD BUILDER
   ============================================================ */

function getSelectedTeamPayload() {
    const teamSelector = getTeamSelector();
    const option = selectedOption(teamSelector);
    const resolvedTeam = resolveTeam(teamSelector ? teamSelector.value : "");

    const teamName =
        (option && option.dataset.teamName) ||
        (resolvedTeam && resolvedTeam.name) ||
        (option && option.textContent) ||
        "";

    return {
        team_id: scalarNumberOrText(
            (option && (option.dataset.teamId || option.dataset.databaseId)) ||
            (resolvedTeam && (resolvedTeam.id || resolvedTeam.team_id || resolvedTeam.database_id))
        ),
        mlb_team_id: scalarNumberOrText(
            (option && option.dataset.mlbTeamId) ||
            (resolvedTeam && resolvedTeam.mlb_team_id)
        ),
        team_name: safeDisplay(teamName, "")
    };
}


function getSelectedPlayerPayload() {
    const playerSelector = getPlayerSelector();
    const option = selectedOption(playerSelector);

    const playerName =
        (option && option.dataset.playerName) ||
        (option && option.textContent) ||
        "";

    return {
        player_id: scalarNumberOrText(
            option && (option.dataset.playerId || option.dataset.databaseId || option.value)
        ),
        mlb_player_id: scalarNumberOrText(
            option && option.dataset.mlbPlayerId
        ),
        player_name: safeDisplay(playerName, ""),
        position: scalarId(option && option.dataset.position),
        position_code: scalarId(option && option.dataset.positionCode)
    };
}


function getSelectedOutcomePayload() {
    const outcomeSelector = getOutcomeSelector();
    const option = selectedOption(outcomeSelector);

    const rawOutcome =
        outcomeSelector && outcomeSelector.value
            ? outcomeSelector.value
            : "home_run";

    const outcomeKey = normalizeOutcomeKey(rawOutcome);

    return {
        outcome_key: outcomeKey,
        outcome: outcomeKey,
        outcome_label: option ? safeDisplay(option.textContent, titleCase(outcomeKey)) : titleCase(outcomeKey)
    };
}


function collectPredictionPayload() {
    const team = getSelectedTeamPayload();
    const player = getSelectedPlayerPayload();
    const outcome = getSelectedOutcomePayload();

    const payload = {
        team_id: team.team_id,
        mlb_team_id: team.mlb_team_id,
        team_name: team.team_name,
        team: team.team_name,

        player_id: player.player_id,
        mlb_player_id: player.mlb_player_id,
        player_name: player.player_name,
        player: player.player_name,

        outcome_key: outcome.outcome_key,
        outcome: outcome.outcome_key,
        outcome_label: outcome.outcome_label,

        season: new Date().getUTCFullYear(),

        frontend_version: "phase_16_part_3c_prediction_payload_fix",
        payload_contract: "clean_scalar_prediction_payload"
    };

    AISP2_PREDICTION_STATE.lastPayload = payload;

    return payload;
}


function validatePredictionPayload(payload) {
    const errors = [];

    if (!payload.team_name || isInvalidSelectorValue(payload.team_name)) {
        errors.push("Select a valid team before running a prediction.");
    }

    if (!payload.player_name || isInvalidSelectorValue(payload.player_name)) {
        errors.push("Select a valid player before running a prediction.");
    }

    if (!payload.player_id && !payload.mlb_player_id) {
        errors.push("Selected player is missing player_id and mlb_player_id.");
    }

    if (!payload.outcome_key) {
        errors.push("Select an outcome before running a prediction.");
    }

    return {
        valid: errors.length === 0,
        errors: errors
    };
}


function updateSelectedContextPreview() {
    const payload = collectPredictionPayload();

    if (payload.player_name && !isInvalidSelectorValue(payload.player_name)) {
        setText("[data-result-player]", payload.player_name);
        setText("[data-intelligence-summary]", "Ready to generate prediction intelligence for " + payload.player_name + ".");
    } else {
        setText("[data-result-player]", "Choose Player");
        setText("[data-intelligence-summary]", "Select a team, player, and outcome to generate AISP2 prediction intelligence.");
    }

    setText("[data-result-team]", payload.team_name || "Team Pending");
    setText("[data-result-outcome]", payload.outcome_label || titleCase(payload.outcome_key));
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
        const result = await postJson(
            AISP2_PREDICTION_STATE.endpoints.prediction,
            payload
        );

        AISP2_PREDICTION_STATE.lastPrediction = result;
        AISP2_PREDICTION_STATE.lastError = null;

        renderPredictionResult(result);
    } catch (primaryError) {
        /*
           Legacy fallback remains available only as a rescue path.
           It still receives the clean scalar payload.
        */
        try {
            const legacyResult = await postJson(
                AISP2_PREDICTION_STATE.endpoints.legacyPrediction,
                payload
            );

            legacyResult.frontend_primary_error = primaryError.message;
            AISP2_PREDICTION_STATE.lastPrediction = legacyResult;
            AISP2_PREDICTION_STATE.lastError = null;

            renderPredictionResult(legacyResult);
        } catch (legacyError) {
            AISP2_PREDICTION_STATE.lastError = legacyError;
            renderPredictionError(
                legacyError.message ||
                primaryError.message ||
                "Prediction failed."
            );
        }
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
        setText("[data-intelligence-reasoning]", "AISP2 is sending clean player/team IDs to the Workbench prediction endpoint.");
    }
}


/* ============================================================
   SECTION 13 - RESULT NORMALIZATION
   ============================================================ */

function getPredictionProbability(result) {
    const prediction = result.prediction || {};

    return (
        prediction.estimated_probability ??
        prediction.probability ??
        result.probability
    );
}


function getPredictionConfidence(result) {
    const prediction = result.prediction || {};

    return (
        prediction.confidence ??
        result.confidence
    );
}


function getResolvedPlayerName(result) {
    const debug = result.debug || {};
    const dataStatus = result.data_status || {};

    return safeDisplay(
        result.player_name ||
        result.player ||
        debug.resolved_player_name ||
        dataStatus.resolved_player_name ||
        collectPredictionPayload().player_name,
        "Unknown Player"
    );
}


function getResolvedTeamName(result) {
    const team = result.team || {};
    const teamName =
        result.team_name ||
        (typeof team === "object" ? team.name : team) ||
        collectPredictionPayload().team_name;

    return safeDisplay(teamName, "Unknown Team");
}


function getResultOutcome(result) {
    const outcome = result.outcome || {};
    const fallback = collectPredictionPayload();

    return {
        key: normalizeOutcomeKey(outcome.key || result.outcome_key || fallback.outcome_key),
        label: safeDisplay(outcome.label || fallback.outcome_label, titleCase(fallback.outcome_key))
    };
}


function getFeaturePacket(result) {
    return result.feature_packet && typeof result.feature_packet === "object"
        ? result.feature_packet
        : {};
}


/* ============================================================
   SECTION 14 - RESULT RENDERING
   ============================================================ */

function renderPredictionResult(result) {
    const prediction = result.prediction || {};
    const intelligence = result.intelligence || {};
    const supporting = result.supporting_context || {};
    const dataStatus = result.data_status || {};
    const featurePacket = getFeaturePacket(result);
    const probabilityInputs = featurePacket.probability_inputs || {};
    const technicalProfile =
        intelligence.technical_profile ||
        supporting.technical_profile ||
        featurePacket.technical_profile ||
        {};

    const outcome = getResultOutcome(result);

    const probability = getPredictionProbability(result);
    const confidence = getPredictionConfidence(result);

    const playerName = getResolvedPlayerName(result);
    const teamName = getResolvedTeamName(result);

    const tier =
        intelligence.tier ||
        prediction.tier ||
        prediction.prediction_tier ||
        "Player-Specific Baseline";

    const risk =
        intelligence.risk_profile ||
        prediction.risk_profile ||
        technicalProfile.primary_risk ||
        "Normal Baseball Variance";

    const outcomeProfile =
        intelligence.outcome_profile ||
        technicalProfile.power_profile ||
        technicalProfile.contact_profile ||
        "Player-Specific Outcome Profile";

    const primaryMetric =
        intelligence.primary_metric ||
        supporting.primary_metric ||
        prediction.primary_metric ||
        result.primary_metric ||
        probabilityInputs.primary_metric ||
        "Player Observed Rate";

    const model =
        prediction.model ||
        result.model ||
        "AISP2 Player-Specific Feature Baseline";

    const dataSource =
        intelligence.data_source ||
        prediction.prediction_source ||
        result.source ||
        result.source_status ||
        featurePacket.source_status ||
        "Prediction Runtime";

    const coverage =
        intelligence.data_coverage ??
        prediction.data_coverage ??
        dataStatus.coverage ??
        dataStatus.data_coverage ??
        (
            probabilityInputs.coverage !== undefined
                ? probabilityInputs.coverage * 100
                : null
        );

    const warehouse =
        intelligence.warehouse_status ||
        prediction.warehouse_status ||
        dataStatus.warehouse_status ||
        (
            safeNumber(result.sample_size) > 0
                ? "Feature Builder Connected"
                : "No Hitting Sample"
        );

    const sampleSize =
        intelligence.sample_size ??
        prediction.sample_size ??
        result.sample_size ??
        dataStatus.sample_size ??
        featurePacket.sample_size ??
        "Pending";

    const observedRate =
        prediction.observed_rate ??
        supporting.observed_rate ??
        probabilityInputs.observed_rate;

    const leagueBaselineRate =
        prediction.league_baseline_rate ??
        supporting.league_baseline_rate ??
        probabilityInputs.league_baseline_rate;

    const explanation =
        intelligence.ai_explanation ||
        supporting.ai_explanation ||
        result.explanation ||
        buildMathExplanation(
            playerName,
            outcome.label,
            primaryMetric,
            observedRate,
            leagueBaselineRate,
            sampleSize
        );

    setText("[data-result-player]", playerName);
    setText("[data-result-team]", teamName);
    setText("[data-result-outcome]", outcome.label);
    setText("[data-result-probability]", formatPercent(probability));
    setText("[data-result-confidence]", formatPercent(confidence, "Confidence Pending"));
    setText("[data-result-tier]", tier);
    setText("[data-result-risk]", risk);
    setText("[data-result-profile]", outcomeProfile);
    setText("[data-result-supporting-metric]", primaryMetric);
    setText("[data-result-model]", model);
    setText("[data-result-model-secondary]", model);
    setText("[data-result-style]", supporting.player_style || technicalProfile.primary_strength || outcomeProfile);
    setText("[data-result-form]", supporting.recent_form || "Season-stat feature packet active");
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
        technicalProfile.model_guidance ||
        "Player-specific rate math active. Full calibration requires matchup, Statcast, and backtesting layers."
    );
    setText("[data-intelligence-reasoning]", explanation);
    setText("[data-warehouse-status]", warehouse);

    setList(
        "[data-intelligence-warnings]",
        intelligence.warnings ||
        result.warnings ||
        buildWarnings(warehouse, dataStatus, sampleSize)
    );

    setList(
        "[data-intelligence-next-data]",
        intelligence.next_data_needed ||
        result.next_data_needed ||
        buildNextDataNeeded(warehouse, dataStatus, sampleSize)
    );

    renderOutcomeLibrary(result, probability, outcome.key);
    renderTransparentRuntimeSections(model);
    exposeDebugPayload(result);
}


function buildMathExplanation(playerName, outcomeLabel, primaryMetric, observedRate, leagueBaselineRate, sampleSize) {
    const sample = safeNumber(sampleSize);

    if (sample === null || sample <= 0) {
        return (
            playerName +
            " has no usable hitting sample for " +
            outcomeLabel +
            ". AISP2 is correctly blocking a fabricated player-specific projection."
        );
    }

    const observed =
        safeNumber(observedRate) !== null
            ? formatPercent(safeNumber(observedRate) * 100)
            : "available";

    const baseline =
        safeNumber(leagueBaselineRate) !== null
            ? formatPercent(safeNumber(leagueBaselineRate) * 100)
            : "available";

    return (
        "AISP2 calculated " +
        playerName +
        " using " +
        primaryMetric +
        ". The engine blends the player's observed rate (" +
        observed +
        ") with the league baseline (" +
        baseline +
        ") using sample-size shrinkage across " +
        sample +
        " opportunities."
    );
}


function buildWarnings(warehouse, dataStatus, sampleSize) {
    const warnings = [];

    if (safeNumber(sampleSize) === null || safeNumber(sampleSize) <= 0) {
        warnings.push("No player-specific prediction was calculated because no usable hitting sample was found.");
    }

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


function buildNextDataNeeded(warehouse, dataStatus, sampleSize) {
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

    if (safeNumber(sampleSize) === null || safeNumber(sampleSize) <= 0) {
        items.push("Verify Workbench payload contains player_id and mlb_player_id.");
        items.push("Verify PlayerSeasonStat row exists for the resolved player.");
        items.push("Verify MLB Stats API fallback returns a hitting stat split.");
    }

    if (warehouse === "Pending Ingestion") {
        items.push("Connect Statcast warehouse tables.");
    }

    items.push("Connect schedule and probable pitcher data.");
    items.push("Connect matchup, ballpark, and weather context.");
    items.push("Connect Monte Carlo simulation engine.");

    return items;
}


function renderOutcomeLibrary(result, probability, outcomeKey) {
    const propProbabilities =
        result.prop_probabilities && typeof result.prop_probabilities === "object"
            ? result.prop_probabilities
            : {};

    const mapping = {
        home_run: "[data-prop-home-run]",
        hit: "[data-prop-hit]",
        rbi: "[data-prop-rbi]",
        run_scored: "[data-prop-run-scored]",
        run: "[data-prop-run-scored]",
        total_bases: "[data-prop-total-bases]",
        strikeout: "[data-prop-strikeout]"
    };

    Object.keys(mapping).forEach(function(key) {
        if (propProbabilities[key] !== undefined) {
            setText(mapping[key], formatPercent(propProbabilities[key]));
        }
    });

    const selectedKey = normalizeOutcomeKey(outcomeKey);

    if (mapping[selectedKey]) {
        setText(mapping[selectedKey], formatPercent(probability));
    }
}


function renderTransparentRuntimeSections(model) {
    setText("[data-runtime-mode]", "Player-Specific Runtime");
    setText("[data-model-state]", model || "Player-Specific Feature Baseline");
}


function exposeDebugPayload(result) {
    window.AISP2_LAST_PREDICTION_RESPONSE = result;
    window.AISP2_LAST_PREDICTION_PAYLOAD = AISP2_PREDICTION_STATE.lastPayload;
}


/* ============================================================
   SECTION 15 - ERROR AND RESET
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
   SECTION 16 - ACCOUNT INTEGRATION
   ============================================================ */

(function initializeAISP2PredictionAccountIntegration() {
    "use strict";

    const VERSION = "phase_16_part_3c_prediction_account_integration";

    const state = {
        account: null,
        authenticated: false,
        lastPrediction: null,
        initializedAt: new Date().toISOString()
    };

    function $(selector) {
        return document.querySelector(selector);
    }

    function all(selector) {
        return Array.from(document.querySelectorAll(selector));
    }

    function setStatus(message, kind) {
        const target = $("[data-prediction-account-status]");
        if (!target) {
            return;
        }

        target.textContent = message;
        target.dataset.status = kind || "info";
    }

    async function fetchAccountJson(url, options) {
        const response = await fetch(url, {
            credentials: "same-origin",
            headers: {
                Accept: "application/json",
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
            const payload = await fetchAccountJson("/api/auth/me", { method: "GET" });
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

    async function saveSearch(reason) {
        const selection = collectPredictionPayload();

        if (!selection.player_name && !selection.team_name) {
            return null;
        }

        try {
            const payload = await fetchAccountJson("/api/account/searches", {
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
                        phase: "Phase 16 Part 3C",
                        reason: reason || "manual",
                        frontend_version: VERSION
                    }
                })
            });

            setStatus("Search saved to your account memory.", "good");
            return payload;
        } catch (error) {
            if (error.status === 401 || error.status === 403) {
                setStatus("Login required to save prediction search history.", "warn");
                return null;
            }

            setStatus(`Save search failed: ${error.message}`, "danger");
            return null;
        }
    }

    async function followPlayer() {
        const selection = collectPredictionPayload();

        if (!selection.player_name && !selection.player_id) {
            setStatus("Choose a player before following.", "warn");
            return null;
        }

        try {
            const payload = await fetchAccountJson("/api/account/follow/player", {
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
                        phase: "Phase 16 Part 3C",
                        frontend_version: VERSION
                    }
                })
            });

            setStatus("Player followed. This player is now linked to your account.", "good");
            return payload;
        } catch (error) {
            if (error.status === 401 || error.status === 403) {
                setStatus("Login required to follow players.", "warn");
                return null;
            }

            setStatus(`Follow player failed: ${error.message}`, "danger");
            return null;
        }
    }

    async function followTeam() {
        const selection = collectPredictionPayload();

        if (!selection.team_name && !selection.team_id) {
            setStatus("Choose a team before following.", "warn");
            return null;
        }

        try {
            const payload = await fetchAccountJson("/api/account/follow/team", {
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
                        phase: "Phase 16 Part 3C",
                        frontend_version: VERSION
                    }
                })
            });

            setStatus("Team followed. This team is now linked to your account.", "good");
            return payload;
        } catch (error) {
            if (error.status === 401 || error.status === 403) {
                setStatus("Login required to follow teams.", "warn");
                return null;
            }

            setStatus(`Follow team failed: ${error.message}`, "danger");
            return null;
        }
    }

    function attachButtonListeners() {
        all("[data-account-action]").forEach(function(button) {
            if (button.dataset.accountActionAttached === "true") {
                return;
            }

            button.dataset.accountActionAttached = "true";

            button.addEventListener("click", async function() {
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

    function boot() {
        attachButtonListeners();
        loadAccount();

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
        getCurrentSelection: collectPredictionPayload,
        reloadAccount: loadAccount
    };
}());


/* ============================================================
   SECTION 17 - DEBUG EXPORTS
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
    },
    getLastPayload: function() {
        return AISP2_PREDICTION_STATE.lastPayload;
    },
    getLastPrediction: function() {
        return AISP2_PREDICTION_STATE.lastPrediction;
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