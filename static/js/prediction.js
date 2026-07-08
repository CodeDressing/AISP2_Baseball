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
   SECTION 22 - LIVE MLB TEAM AND PLAYER LOADER
   FILE: static/js/prediction.js
   PURPOSE: load all MLB teams and active rosters from backend
   ============================================================ */

const AISP2_MLB_CACHE = {
    teams: [],
    teamMap: {},
    loaded: false
};


async function initializeLiveMLBSelectors() {

    try {

        const teamsResponse =
            await fetch("/api/mlb/teams");

        const teamsData =
            await teamsResponse.json();

        if (!teamsData.teams) {
            return;
        }

        AISP2_MLB_CACHE.teams =
            teamsData.teams;

        const teamSelector =
            getTeamSelector();

        if (!teamSelector) {
            return;
        }

        teamSelector.innerHTML = "";

        teamsData.teams.forEach(team => {

            AISP2_MLB_CACHE.teamMap[
                team.name
            ] = team;

            const option =
                document.createElement("option");

            option.value =
                team.name;

            option.textContent =
                team.name;

            teamSelector.appendChild(option);

        });

        AISP2_MLB_CACHE.loaded =
            true;

        if (teamsData.teams.length > 0) {

            await loadPlayersForSelectedTeam(
                teamsData.teams[0].name
            );

        }

    } catch (error) {

        console.error(
            "Failed loading MLB teams:",
            error
        );
    }
}


async function loadPlayersForSelectedTeam(teamName) {

    const team =
        AISP2_MLB_CACHE.teamMap[teamName];

    if (!team) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/mlb/teams/" +
                team.id +
                "/players"
            );

        const data =
            await response.json();

        const playerSelector =
            getPlayerSelector();

        if (!playerSelector) {
            return;
        }

        playerSelector.innerHTML = "";

        data.players.forEach(player => {

            const option =
                document.createElement("option");

            option.value =
                player.name;

            option.textContent =
                player.name;

            playerSelector.appendChild(option);

        });

    } catch (error) {

        console.error(
            "Failed loading players:",
            error
        );
    }
}