/* ============================================================
   AISP2 BASEBALL
   FILE: static/js/prediction.js
   PURPOSE: prediction workbench behavior, selector handling,
   demo probability rendering, API hooks, and future real model
   integration support
   ============================================================ */


/* ============================================================
   SECTION 01 - PREDICTION STATE
   ============================================================ */
/* ============================================================
   SECTION 01 - ENTERPRISE PREDICTION STATE
   FILE: static/js/prediction.js
   PURPOSE: runtime state for live prediction endpoint,
   prediction workbench controls, model response rendering,
   and safe fallback behavior.
   ============================================================ */

const AISP2_PREDICTION_STATE = {
    initialized: false,
    isRunning: false,
    endpoint: "/predict/player",
    method: "POST",
    lastPrediction: null
};


/* ============================================================
   SECTION 02 - DOM READY INITIALIZATION
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    initializeAISP2Prediction
);


async function initializeAISP2Prediction() {

    if (AISP2_PREDICTION_STATE.initialized) {
        return;
    }

    bindPredictionEvents();

    await initializeLiveMLBSelectors();

    AISP2_PREDICTION_STATE.initialized = true;
}


/* ============================================================
   SECTION 03 - DOM HELPERS
   ============================================================ */

function getPredictionForm() {
    return document.querySelector("[data-prediction-form]");
}


function getTeamSelector() {
    return document.querySelector("[data-prediction-team]");
}


function getPlayerSelector() {
    return document.querySelector("[data-prediction-player]");
}


function getOutcomeSelector() {
    return document.querySelector("[data-prediction-outcome]");
}


function getPredictionButton() {
    return document.querySelector("[data-prediction-submit]");
}


/* ============================================================
   SECTION 04 - EVENT BINDING
   ============================================================ */

/* ============================================================
   SECTION 04 - ENTERPRISE EVENT BINDING
   FILE: static/js/prediction.js
   PURPOSE: bind Run Prediction button, optional form submit,
   team selector changes, reset behavior, and prevent duplicate
   event binding across hot reloads or page reinitialization.
   ============================================================ */

function bindPredictionEvents() {

    const form = getPredictionForm();

    if (form && !form.dataset.aisp2Bound) {

        form.addEventListener(
            "submit",
            handlePredictionSubmit
        );

        form.dataset.aisp2Bound = "true";
    }

    const predictionButton = getPredictionButton();

    if (predictionButton && !predictionButton.dataset.aisp2Bound) {

        predictionButton.addEventListener(
            "click",
            function(event) {

                event.preventDefault();

                runPrediction();
            }
        );

        predictionButton.dataset.aisp2Bound = "true";
    }

    const teamSelector = getTeamSelector();

    if (teamSelector && !teamSelector.dataset.aisp2Bound) {

        teamSelector.addEventListener(
            "change",
            handleTeamChange
        );

        teamSelector.dataset.aisp2Bound = "true";
    }

    const resetButton =
        document.querySelector("[data-prediction-reset]");

    if (resetButton && !resetButton.dataset.aisp2Bound) {

        resetButton.addEventListener(
            "click",
            function(event) {

                event.preventDefault();

                resetPredictionWorkbench();
            }
        );

        resetButton.dataset.aisp2Bound = "true";
    }
}


function resetPredictionWorkbench() {

    AISP2_PREDICTION_STATE.lastPrediction = null;

    setTextIfExists(
        "[data-result-player]",
        "Selected Player"
    );

    setTextIfExists(
        "[data-result-outcome]",
        "Selected Outcome"
    );

    setTextIfExists(
        "[data-result-probability]",
        "0%"
    );

    setTextIfExists(
        "[data-result-confidence]",
        "Confidence Pending"
    );

    setTextIfExists(
        "[data-result-tier]",
        "Pending"
    );

    setTextIfExists(
        "[data-result-risk]",
        "Pending"
    );

    setTextIfExists(
        "[data-result-profile]",
        "Pending"
    );

    setTextIfExists(
        "[data-result-supporting-metric]",
        "Pending"
    );

    setTextIfExists(
        "[data-result-ai-explanation]",
        "Select a player and outcome to generate AISP2 prediction intelligence."
    );

    clearPredictionResultNotice();
}
/* ============================================================
   SECTION 05 - FORM SUBMISSION
   ============================================================ */

function handlePredictionSubmit(event) {

    event.preventDefault();

    runPrediction();
}


/* ============================================================
   SECTION 06 - TEAM CHANGE HANDLER
   ============================================================ */

async function handleTeamChange() {

    const teamSelector =
        getTeamSelector();

    if (teamSelector) {

        await loadPlayersForSelectedTeam(
            teamSelector.value
        );
    }

    clearPredictionResultNotice();
}

/* ============================================================
   SECTION 07 - RUN PREDICTION FLOW
   ============================================================ */

async function runPrediction() {

    if (AISP2_PREDICTION_STATE.isRunning) {
        return;
    }

    const payload =
        collectPredictionPayload();

    setPredictionLoading(true);

    try {

        const result =
            await fetchPredictionResult(payload);

        AISP2_PREDICTION_STATE.lastPrediction =
            result;

        renderPredictionResult(result);

    } catch (error) {

        console.error(
            "AISP2 prediction error:",
            error
        );

        renderPredictionError(
            error.message
        );

    } finally {

        setPredictionLoading(false);
    }
}


/* ============================================================
   SECTION 08 - COLLECT FORM PAYLOAD
   ============================================================ */

function collectPredictionPayload() {

    const teamSelector = getTeamSelector();
    const playerSelector = getPlayerSelector();
    const outcomeSelector = getOutcomeSelector();

    return {
        team: teamSelector ? teamSelector.value : "",
        player: playerSelector ? playerSelector.value : "",
        outcome: outcomeSelector ? outcomeSelector.value : ""
    };
}


/* ============================================================
   SECTION 09 - API REQUEST
   ============================================================ */

/* ============================================================
   SECTION 09 - ENTERPRISE PREDICTION API REQUEST
   FILE: static/js/prediction.js
   PURPOSE: send selected team, player, and outcome to the real
   backend prediction endpoint and return structured model output.
   ============================================================ */

async function fetchPredictionResult(payload) {

    const response =
        await fetch(
            AISP2_PREDICTION_STATE.endpoint,
            {
                method: AISP2_PREDICTION_STATE.method,
                headers: {
                    "Content-Type": "application/json"
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

        data =
            await response.json();

    } catch (error) {

        throw new Error(
            "Prediction endpoint returned invalid JSON."
        );
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

/* ============================================================
   SECTION 10 - RENDER RESULT
   ============================================================ */
/* ============================================================
   SECTION 10 - ENTERPRISE PREDICTION RESULT RENDERER
   FILE: static/js/prediction.js
   PURPOSE: render probability, confidence, model name, risk,
   outcome profile, primary metric, and AI explanation from
   backend prediction responses.
   ============================================================ */

function renderPredictionResult(result) {

    const prediction =
        result.prediction || {};

    const outcome =
        result.outcome || {};

    const team =
        result.team || {};

    const supportingContext =
        result.supporting_context || {};

    const intelligence =
        result.intelligence || {};

    setTextIfExists(
        "[data-result-player]",
        result.player || "Unknown Player"
    );

    setTextIfExists(
        "[data-result-team]",
        team.name || result.team || "Unknown Team"
    );

    setTextIfExists(
        "[data-result-outcome]",
        outcome.label || "Unknown Outcome"
    );

    setTextIfExists(
        "[data-result-probability]",
        formatPercent(
            prediction.estimated_probability
        )
    );

    setTextIfExists(
        "[data-result-confidence]",
        formatPercent(
            prediction.confidence
        )
    );

    setTextIfExists(
        "[data-result-model]",
        prediction.model || "AISP2 Baseline Model"
    );

    setTextIfExists(
        "[data-result-style]",
        supportingContext.player_style || "Warehouse Baseline"
    );

    setTextIfExists(
        "[data-result-form]",
        supportingContext.recent_form || "Pending"
    );

    setTextIfExists(
        "[data-result-metric]",
        supportingContext.primary_metric || "Feature Score"
    );

    setTextIfExists(
        "[data-result-tier]",
        prediction.tier || intelligence.tier || "Pending"
    );

    setTextIfExists(
        "[data-result-risk]",
        prediction.risk_profile || intelligence.risk_profile || "Pending"
    );

    setTextIfExists(
        "[data-result-profile]",
        intelligence.outcome_profile || supportingContext.player_style || "Pending"
    );

    setTextIfExists(
        "[data-result-supporting-metric]",
        intelligence.primary_metric || supportingContext.primary_metric || "Pending"
    );

    setTextIfExists(
        "[data-result-ai-explanation]",
        intelligence.ai_explanation ||
        supportingContext.ai_explanation ||
        "AISP2 generated a baseline prediction from currently available player and warehouse context."
    );

    setPredictionResultVisible(true);
}

/* ============================================================
   SECTION 11 - RENDER ERROR
   ============================================================ */

function renderPredictionError(message) {

    setTextIfExists(
        "[data-prediction-error]",
        message || "Prediction failed."
    );

    const errorPanel =
        document.querySelector(
            "[data-prediction-error-panel]"
        );

    if (errorPanel) {
        errorPanel.classList.add("visible");
    }
}


/* ============================================================
   SECTION 12 - RESULT VISIBILITY
   ============================================================ */

function setPredictionResultVisible(isVisible) {

    const resultPanels =
        document.querySelectorAll(
            "[data-prediction-result]"
        );

    resultPanels.forEach(
        function(panel) {

            panel.style.display =
                isVisible
                    ? "block"
                    : "none";
        }
    );
}


function clearPredictionResultNotice() {

    const errorPanel =
        document.querySelector(
            "[data-prediction-error-panel]"
        );

    if (errorPanel) {
        errorPanel.classList.remove("visible");
    }
}


/* ============================================================
   SECTION 13 - LOADING STATE
   ============================================================ */

function setPredictionLoading(isLoading) {

    AISP2_PREDICTION_STATE.isRunning =
        isLoading;

    const button =
        getPredictionButton();

    if (button) {

        button.disabled =
            isLoading;

        button.innerText =
            isLoading
                ? "Running..."
                : "Run Prediction";
    }

    const loadingElements =
        document.querySelectorAll(
            "[data-prediction-loading]"
        );

    loadingElements.forEach(
        function(element) {

            element.style.display =
                isLoading
                    ? "inline-flex"
                    : "none";
        }
    );
}


/* ============================================================
   SECTION 14 - FORMAT HELPERS
   ============================================================ */

function formatPercent(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "0%";
    }

    return String(value) + "%";
}


function setTextIfExists(
    selector,
    value
) {

    const element =
        document.querySelector(selector);

    if (!element) {
        return;
    }

    element.innerText =
        String(value);
}


/* ============================================================
   SECTION 15 - FUTURE REAL DATA HOOKS
   ============================================================ */

async function fetchTeamsForPrediction() {

    /*
    Future endpoint:
        /api/teams
    */

    return [];
}


async function fetchPlayersForTeam(teamId) {

    /*
    Future endpoint:
        /api/teams/{teamId}/players
    */

    return [];
}


async function fetchAvailableOutcomes() {

    /*
    Future endpoint:
        /api/predictions/outcomes
    */

    return [];
}


/* ============================================================
   SECTION 16 - FUTURE ADVANCED RENDERING
   ============================================================ */

function renderFutureProbabilityBreakdown(payload) {

    /*
    Future use:
        - baseline probability
        - matchup adjustment
        - park factor adjustment
        - weather adjustment
        - recent form adjustment
        - final probability
    */

    return null;
}


function renderFutureModelExplanation(payload) {

    /*
    Future use:
        - model name
        - model confidence
        - important features
        - plain-English explanation
        - data sources used
    */

    return null;
}


function renderFutureSimulationDistribution(payload) {

    /*
    Future use:
        - Monte Carlo outcomes
        - confidence intervals
        - percentile ranges
        - risk bands
    */

    return null;
}


/* ============================================================
   SECTION 17 - PREDICTION ROADMAP
   ============================================================ */

/*

17.01 Real team selector

17.02 Real player selector

17.03 Real outcome selector

17.04 Real prediction endpoint

17.05 Probability breakdown

17.06 Model explanation cards

17.07 Monte Carlo simulation display

17.08 Confidence interval visualization

17.09 Similar player comparison

17.10 Batter-vs-pitcher matchup panel

17.11 Statcast trend integration

17.12 Exportable prediction report

*/

/* ============================================================
   SECTION 18 - DEMO PREDICTION ENGINE
   FILE: static/js/prediction.js
   PURPOSE: frontend fallback prediction logic for demo mode
   when future live model endpoints are not yet connected
   ============================================================ */

function buildDemoPredictionIntelligence(payload) {

    const outcome =
        payload.outcome || "Home Run";

    const player =
        payload.player || "Selected Player";

    const team =
        payload.team || "Selected Team";

    let baseProbability = 52;

    if (outcome.includes("Home Run")) {
        baseProbability = 28;
    }

    if (outcome.includes("Hit")) {
        baseProbability = 64;
    }

    if (outcome.includes("RBI")) {
        baseProbability = 46;
    }

    if (outcome.includes("Run")) {
        baseProbability = 51;
    }

    if (outcome.includes("Total Bases")) {
        baseProbability = 57;
    }

    if (outcome.includes("Strikeout")) {
        baseProbability = 42;
    }

    return {
        player: player,
        team: team,
        outcome: outcome,
        probability: baseProbability,
        confidence: calculateDemoConfidence(baseProbability),
        tier: getPredictionTier(baseProbability)
    };
}


function calculateDemoConfidence(probability) {

    if (probability >= 75) {
        return 88;
    }

    if (probability >= 60) {
        return 76;
    }

    if (probability >= 45) {
        return 64;
    }

    return 52;
}


/* ============================================================
   SECTION 19 - OUTCOME INTELLIGENCE
   FILE: static/js/prediction.js
   PURPOSE: classify selected prediction into readable baseball
   intelligence categories
   ============================================================ */

function buildOutcomeIntelligence(outcome) {

    if (outcome.includes("Home Run")) {
        return {
            profile: "Power Profile",
            metric: "Exit velocity, barrel rate, launch angle",
            risk: "High variance",
            angle: "Power outcomes depend heavily on contact quality and matchup."
        };
    }

    if (outcome.includes("Hit")) {
        return {
            profile: "Contact Profile",
            metric: "AVG, OBP, contact rate, recent form",
            risk: "Moderate",
            angle: "Hit outcomes are more stable than home run outcomes."
        };
    }

    if (outcome.includes("RBI")) {
        return {
            profile: "Run Production Profile",
            metric: "Lineup context, team offense, runners-on-base expectation",
            risk: "Context dependent",
            angle: "RBI outcomes depend on both player quality and opportunity."
        };
    }

    if (outcome.includes("Total Bases")) {
        return {
            profile: "Slugging Profile",
            metric: "OPS, SLG, extra-base-hit rate",
            risk: "Moderate-high",
            angle: "Total bases combine hit probability with power upside."
        };
    }

    if (outcome.includes("Strikeout")) {
        return {
            profile: "Pitching / Whiff Profile",
            metric: "K rate, whiff rate, chase rate, pitch mix",
            risk: "Matchup dependent",
            angle: "Strikeout outcomes require pitcher and batter context."
        };
    }

    return {
        profile: "General Outcome Profile",
        metric: "Player form, matchup, and team context",
        risk: "Unknown",
        angle: "AISP2 will refine this with live data."
    };
}


/* ============================================================
   SECTION 20 - AI EXPLANATION GENERATOR
   FILE: static/js/prediction.js
   PURPOSE: generate readable demo explanations for prediction
   result cards before live AI model integration
   ============================================================ */

function buildDemoAIExplanation(prediction) {

    const intelligence =
        buildOutcomeIntelligence(prediction.outcome);

    return (
        prediction.player +
        " projects as a " +
        intelligence.profile.toLowerCase() +
        " candidate for this outcome. " +
        "The selected result is supported by " +
        intelligence.metric +
        ". Risk level is currently classified as " +
        intelligence.risk +
        ". " +
        intelligence.angle
    );
}


function getPredictionTier(probability) {

    if (probability >= 90) {
        return "Elite";
    }

    if (probability >= 75) {
        return "High";
    }

    if (probability >= 60) {
        return "Moderate";
    }

    if (probability >= 40) {
        return "Risky";
    }

    return "Longshot";
}


/* ============================================================
   SECTION 21 - PREDICTION VISUAL ENHANCEMENTS
   FILE: static/js/prediction.js
   PURPOSE: update optional future DOM targets for probability
   tier, AI explanation, risk profile, and model context
   ============================================================ */

function renderDemoPredictionEnhancements(payload) {

    const demoPrediction =
        buildDemoPredictionIntelligence(payload);

    const explanation =
        buildDemoAIExplanation(demoPrediction);

    const intelligence =
        buildOutcomeIntelligence(demoPrediction.outcome);

    setTextIfExists(
        "[data-result-tier]",
        demoPrediction.tier
    );

    setTextIfExists(
        "[data-result-ai-explanation]",
        explanation
    );

    setTextIfExists(
        "[data-result-risk]",
        intelligence.risk
    );

    setTextIfExists(
        "[data-result-profile]",
        intelligence.profile
    );

    setTextIfExists(
        "[data-result-supporting-metric]",
        intelligence.metric
    );

    return demoPrediction;
}

/* ============================================================
   SECTION 22 - DATABASE-BACKED PREDICTION TEAM/PLAYER SELECTORS
   FILE: static/js/prediction.js
   PURPOSE:
   Restore the Prediction Workbench player dropdown by loading
   teams and players from /api/player-explorer/bootstrap.

   FIXES:
   - Empty player dropdown
   - Old demo-only player list
   - Mismatch between player.name and player.full_name
   - Team/player selector desync
   - Team changes not refreshing player choices
   ============================================================ */

const AISP2_PREDICTION_SELECTOR_STATE = {
    bootstrapLoaded: false,
    bootstrap: null,
    teams: [],
    playersByTeam: {},
    teamByName: {},
    teamById: {},
    lastTeamKey: null
};


function getPredictionTeamSelectorSafe() {
    return (
        document.querySelector("[data-prediction-team]") ||
        document.querySelector("[data-team-select]") ||
        document.querySelector("[data-player-team]") ||
        document.querySelector("select[name='team']") ||
        document.querySelector("#team")
    );
}


function getPredictionPlayerSelectorSafe() {
    return (
        document.querySelector("[data-prediction-player]") ||
        document.querySelector("[data-player-select]") ||
        document.querySelector("[data-player-name]") ||
        document.querySelector("select[name='player']") ||
        document.querySelector("#player")
    );
}


function normalizePredictionSelectorText(value) {
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


function clearPredictionSelect(selectElement, placeholderText) {
    if (!selectElement) {
        return;
    }

    selectElement.innerHTML = "";

    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholderText || "Pending Ingestion";
    selectElement.appendChild(option);
}


function addPredictionOption(selectElement, value, label, dataset) {
    if (!selectElement || !value || !label) {
        return;
    }

    const option = document.createElement("option");

    option.value = String(value);
    option.textContent = String(label);

    if (dataset && typeof dataset === "object") {
        Object.keys(dataset).forEach(function(key) {
            if (dataset[key] !== undefined && dataset[key] !== null) {
                option.dataset[key] = String(dataset[key]);
            }
        });
    }

    selectElement.appendChild(option);
}


function buildPredictionTeamIndexes(teams) {
    AISP2_PREDICTION_SELECTOR_STATE.teamByName = {};
    AISP2_PREDICTION_SELECTOR_STATE.teamById = {};

    teams.forEach(function(team) {
        if (!team) {
            return;
        }

        const teamId = team.id;
        const mlbTeamId = team.mlb_team_id;
        const name = team.name;
        const abbreviation = team.abbreviation;
        const clubName = team.club_name;
        const shortName = team.short_name;
        const locationName = team.location_name;

        const keys = [
            teamId,
            mlbTeamId,
            name,
            abbreviation,
            clubName,
            shortName,
            locationName
        ];

        keys.forEach(function(key) {
            if (key === undefined || key === null || key === "") {
                return;
            }

            const rawKey = String(key);
            const normalizedKey = normalizePredictionSelectorText(rawKey);

            AISP2_PREDICTION_SELECTOR_STATE.teamByName[rawKey] = team;
            AISP2_PREDICTION_SELECTOR_STATE.teamByName[normalizedKey] = team;
        });

        if (teamId !== undefined && teamId !== null) {
            AISP2_PREDICTION_SELECTOR_STATE.teamById[String(teamId)] = team;
        }

        if (mlbTeamId !== undefined && mlbTeamId !== null) {
            AISP2_PREDICTION_SELECTOR_STATE.teamById[String(mlbTeamId)] = team;
        }
    });
}


function resolvePredictionTeamFromSelectorValue(teamValue) {
    const teamSelector = getPredictionTeamSelectorSafe();

    let team = null;

    if (teamSelector && teamSelector.selectedOptions && teamSelector.selectedOptions.length > 0) {
        const selectedOption = teamSelector.selectedOptions[0];

        if (selectedOption.dataset.teamId) {
            team = AISP2_PREDICTION_SELECTOR_STATE.teamById[selectedOption.dataset.teamId];
        }

        if (!team && selectedOption.dataset.mlbTeamId) {
            team = AISP2_PREDICTION_SELECTOR_STATE.teamById[selectedOption.dataset.mlbTeamId];
        }
    }

    if (team) {
        return team;
    }

    const rawValue = String(teamValue || "");
    const normalizedValue = normalizePredictionSelectorText(rawValue);

    return (
        AISP2_PREDICTION_SELECTOR_STATE.teamByName[rawValue] ||
        AISP2_PREDICTION_SELECTOR_STATE.teamByName[normalizedValue] ||
        AISP2_PREDICTION_SELECTOR_STATE.teamById[rawValue] ||
        null
    );
}


function getPredictionPlayersForTeam(team) {
    if (!team) {
        return [];
    }

    const playersByTeam = AISP2_PREDICTION_SELECTOR_STATE.playersByTeam || {};

    const possibleKeys = [
        team.id,
        team.mlb_team_id,
        team.name,
        team.abbreviation,
        normalizePredictionSelectorText(team.name),
        normalizePredictionSelectorText(team.abbreviation)
    ];

    for (let index = 0; index < possibleKeys.length; index += 1) {
        const key = possibleKeys[index];

        if (key === undefined || key === null || key === "") {
            continue;
        }

        const players = playersByTeam[String(key)];

        if (Array.isArray(players) && players.length > 0) {
            return players;
        }
    }

    return [];
}


function renderPredictionTeamsFromBootstrap() {
    const teamSelector = getPredictionTeamSelectorSafe();

    if (!teamSelector) {
        console.error("Prediction team selector not found.");
        return;
    }

    const teams = AISP2_PREDICTION_SELECTOR_STATE.teams || [];

    teamSelector.innerHTML = "";

    if (!Array.isArray(teams) || teams.length === 0) {
        clearPredictionSelect(teamSelector, "No teams loaded");
        return;
    }

    teams.forEach(function(team) {
        if (!team || !team.name) {
            return;
        }

        addPredictionOption(
            teamSelector,
            team.name,
            team.name,
            {
                teamId: team.id,
                mlbTeamId: team.mlb_team_id,
                abbreviation: team.abbreviation || ""
            }
        );
    });

    const defaultTeam =
        AISP2_PREDICTION_SELECTOR_STATE.bootstrap &&
        AISP2_PREDICTION_SELECTOR_STATE.bootstrap.default_team
            ? AISP2_PREDICTION_SELECTOR_STATE.bootstrap.default_team
            : teams[0];

    if (defaultTeam && defaultTeam.name) {
        teamSelector.value = defaultTeam.name;
        renderPredictionPlayersForTeam(defaultTeam);
    }
}


function renderPredictionPlayersForTeam(team) {
    const playerSelector = getPredictionPlayerSelectorSafe();

    if (!playerSelector) {
        console.error("Prediction player selector not found.");
        return;
    }

    playerSelector.innerHTML = "";

    const players = getPredictionPlayersForTeam(team);

    if (!Array.isArray(players) || players.length === 0) {
        clearPredictionSelect(playerSelector, "No players loaded for this team");

        console.warn(
            "No players found for selected team.",
            {
                selectedTeam: team,
                availablePlayerKeys: Object.keys(AISP2_PREDICTION_SELECTOR_STATE.playersByTeam || {})
            }
        );

        return;
    }

    players.forEach(function(player) {
        if (!player) {
            return;
        }

        const playerName =
            player.full_name ||
            player.player_name ||
            player.name ||
            "";

        if (!playerName) {
            return;
        }

        addPredictionOption(
            playerSelector,
            playerName,
            playerName,
            {
                playerId: player.id,
                mlbPlayerId: player.mlb_player_id,
                position: player.position || "",
                positionCode: player.position_code || ""
            }
        );
    });

    if (playerSelector.options.length > 0) {
        playerSelector.selectedIndex = 0;
    }
}


async function loadPredictionPlayerExplorerBootstrap() {
    const response = await fetch("/api/player-explorer/bootstrap", {
        method: "GET",
        headers: {
            "Accept": "application/json"
        }
    });

    let data = null;

    try {
        data = await response.json();
    } catch (error) {
        throw new Error("Bootstrap endpoint returned invalid JSON.");
    }

    if (!response.ok) {
        throw new Error(
            data.message ||
            data.error ||
            "Bootstrap endpoint failed."
        );
    }

    if (!Array.isArray(data.teams)) {
        throw new Error("Bootstrap endpoint did not return a teams array.");
    }

    return data;
}


async function initializePredictionDatabaseSelectors() {
    const teamSelector = getPredictionTeamSelectorSafe();
    const playerSelector = getPredictionPlayerSelectorSafe();

    if (!teamSelector || !playerSelector) {
        console.error(
            "Prediction selector initialization blocked.",
            {
                hasTeamSelector: Boolean(teamSelector),
                hasPlayerSelector: Boolean(playerSelector)
            }
        );
        return;
    }

    clearPredictionSelect(playerSelector, "Loading players...");

    try {
        const bootstrap = await loadPredictionPlayerExplorerBootstrap();

        AISP2_PREDICTION_SELECTOR_STATE.bootstrap = bootstrap;
        AISP2_PREDICTION_SELECTOR_STATE.teams = bootstrap.teams || [];
        AISP2_PREDICTION_SELECTOR_STATE.playersByTeam = bootstrap.players_by_team || {};
        AISP2_PREDICTION_SELECTOR_STATE.bootstrapLoaded = true;

        buildPredictionTeamIndexes(
            AISP2_PREDICTION_SELECTOR_STATE.teams
        );

        renderPredictionTeamsFromBootstrap();

        if (!teamSelector.dataset.aisp2PredictionPlayersBound) {
            teamSelector.addEventListener("change", function(event) {
                const selectedTeam = resolvePredictionTeamFromSelectorValue(
                    event.target.value
                );

                renderPredictionPlayersForTeam(selectedTeam);
            });

            teamSelector.dataset.aisp2PredictionPlayersBound = "true";
        }

        const selectedTeam = resolvePredictionTeamFromSelectorValue(teamSelector.value);
        renderPredictionPlayersForTeam(selectedTeam);

        console.info(
            "AISP2 Prediction selectors loaded.",
            {
                teamCount: AISP2_PREDICTION_SELECTOR_STATE.teams.length,
                playerGroups: Object.keys(AISP2_PREDICTION_SELECTOR_STATE.playersByTeam).length
            }
        );

    } catch (error) {
        console.error("Prediction selector bootstrap failed:", error);

        clearPredictionSelect(playerSelector, "Player list unavailable");

        if (typeof renderPredictionError === "function") {
            renderPredictionError(
                "Could not load players. Check /api/player-explorer/bootstrap."
            );
        }
    }
}


document.addEventListener("DOMContentLoaded", function() {
    initializePredictionDatabaseSelectors();
});


window.AISP2PredictionSelectors = {
    state: AISP2_PREDICTION_SELECTOR_STATE,
    reload: initializePredictionDatabaseSelectors,
    renderPlayersForTeam: function(teamValue) {
        const team = resolvePredictionTeamFromSelectorValue(teamValue);
        renderPredictionPlayersForTeam(team);
    }
};