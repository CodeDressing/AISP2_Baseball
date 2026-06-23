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

const AISP2_PREDICTION_STATE = {
    initialized: false,
    isRunning: false,
    endpoint: "/api/demo/prediction",
    lastPrediction: null
};


/* ============================================================
   SECTION 02 - DOM READY INITIALIZATION
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    initializeAISP2Prediction
);


function initializeAISP2Prediction() {

    if (AISP2_PREDICTION_STATE.initialized) {
        return;
    }

    bindPredictionEvents();

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

function bindPredictionEvents() {

    const form = getPredictionForm();

    if (form) {

        form.addEventListener(
            "submit",
            handlePredictionSubmit
        );
    }

    const teamSelector = getTeamSelector();

    if (teamSelector) {

        teamSelector.addEventListener(
            "change",
            handleTeamChange
        );
    }
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

function handleTeamChange() {

    /*
    Future use:
        - Fetch players for selected team.
        - Rebuild player dropdown.
        - Refresh matchup context.
    */

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

async function fetchPredictionResult(payload) {

    const params =
        new URLSearchParams();

    if (payload.team) {
        params.set("team", payload.team);
    }

    if (payload.player) {
        params.set("player", payload.player);
    }

    if (payload.outcome) {
        params.set("outcome", payload.outcome);
    }

    const response =
        await fetch(
            AISP2_PREDICTION_STATE.endpoint + "?" + params.toString()
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
            "Prediction request failed."
        );
    }

    return data;
}


/* ============================================================
   SECTION 10 - RENDER RESULT
   ============================================================ */

function renderPredictionResult(result) {

    setTextIfExists(
        "[data-result-player]",
        result.player || "Unknown Player"
    );

    setTextIfExists(
        "[data-result-team]",
        result.team?.name || "Unknown Team"
    );

    setTextIfExists(
        "[data-result-outcome]",
        result.outcome?.label || "Unknown Outcome"
    );

    setTextIfExists(
        "[data-result-probability]",
        formatPercent(
            result.prediction?.estimated_probability
        )
    );

    setTextIfExists(
        "[data-result-confidence]",
        formatPercent(
            result.prediction?.confidence
        )
    );

    setTextIfExists(
        "[data-result-model]",
        result.prediction?.model || "AISP2 Demo Model"
    );

    setTextIfExists(
        "[data-result-style]",
        result.supporting_context?.player_style || "Pending"
    );

    setTextIfExists(
        "[data-result-form]",
        result.supporting_context?.recent_form || "Pending"
    );

    setTextIfExists(
        "[data-result-metric]",
        result.supporting_context?.primary_metric || "Pending"
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