/* ============================================================
   AISP2 BASEBALL
   FILE: static/js/dashboard.js
   PURPOSE: dashboard initialization, KPI rendering,
   analytics placeholders, health checks, future chart hooks,
   and live database status panel support
   ============================================================ */


/* ============================================================
   SECTION 01 - DASHBOARD STATE
   ============================================================ */

const AISP2_DASHBOARD_STATE = {
    initialized: false,
    refreshIntervalMs: 30000,
    lastUpdatedAt: null,
    health: null,
    status: null,
    kpis: {
        teamsLoaded: 0,
        playersLoaded: 0,
        rosterEntries: 0,
        predictionsRun: 0
    }
};


/* ============================================================
   SECTION 02 - DOM READY INITIALIZATION
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    initializeAISP2Dashboard
);


async function initializeAISP2Dashboard() {

    if (AISP2_DASHBOARD_STATE.initialized) {
        return;
    }

    await refreshDashboardData();

    bindDashboardEvents();

    startDashboardAutoRefresh();

    AISP2_DASHBOARD_STATE.initialized = true;
}


/* ============================================================
   SECTION 03 - EVENT BINDING
   ============================================================ */

function bindDashboardEvents() {

    const refreshButtons =
        document.querySelectorAll(
            "[data-dashboard-refresh]"
        );

    refreshButtons.forEach(
        function(button) {

            button.addEventListener(
                "click",
                refreshDashboardData
            );
        }
    );
}


/* ============================================================
   SECTION 04 - DASHBOARD REFRESH FLOW
   ============================================================ */

async function refreshDashboardData() {

    setDashboardLoading(true);

    try {

        const health =
            await fetchDashboardHealth();

        const status =
            await fetchProjectStatus();

        AISP2_DASHBOARD_STATE.health =
            health;

        AISP2_DASHBOARD_STATE.status =
            status;

        AISP2_DASHBOARD_STATE.lastUpdatedAt =
            new Date().toISOString();

        renderDashboardHealth();

        renderProjectStatus();

        renderKpiCards();

        renderLastUpdated();

    } catch (error) {

        console.error(
            "AISP2 dashboard refresh error:",
            error
        );

        renderDashboardError(
            error.message
        );

    } finally {

        setDashboardLoading(false);
    }
}


/* ============================================================
   SECTION 05 - API REQUESTS
   ============================================================ */

async function fetchDashboardHealth() {

    return fetchDashboardJSON(
        "/health"
    );
}


async function fetchProjectStatus() {

    return fetchDashboardJSON(
        "/project/status"
    );
}


async function fetchDashboardJSON(url) {

    const response =
        await fetch(url);

    let payload = {};

    try {

        payload =
            await response.json();

    } catch (error) {

        throw new Error(
            "Dashboard received invalid JSON from " + url
        );
    }

    if (!response.ok) {

        throw new Error(
            payload.detail ||
            payload.error ||
            "Dashboard request failed for " + url
        );
    }

    return payload;
}


/* ============================================================
   SECTION 06 - HEALTH RENDERING
   ============================================================ */

function renderDashboardHealth() {

    const health =
        AISP2_DASHBOARD_STATE.health;

    if (!health) {
        return;
    }

    setTextIfExists(
        "[data-dashboard-health]",
        health.status || "unknown"
    );

    setTextIfExists(
        "[data-dashboard-service]",
        health.service || "aisp2-baseball"
    );

    setTextIfExists(
        "[data-dashboard-phase]",
        health.phase || "unknown"
    );
}


/* ============================================================
   SECTION 07 - PROJECT STATUS RENDERING
   ============================================================ */

function renderProjectStatus() {

    const status =
        AISP2_DASHBOARD_STATE.status;

    if (!status) {
        return;
    }

    setTextIfExists(
        "[data-project-name]",
        status.project || "AISP2 Baseball"
    );

    setTextIfExists(
        "[data-project-status]",
        status.status || "ACTIVE DEVELOPMENT"
    );

    setTextIfExists(
        "[data-project-focus]",
        status.current_focus || "Baseball intelligence platform"
    );

    setTextIfExists(
        "[data-project-next-target]",
        status.next_target || "Real data-backed tools"
    );
}


/* ============================================================
   SECTION 08 - KPI RENDERING
   ============================================================ */

function renderKpiCards() {

    setTextIfExists(
        "[data-kpi-teams]",
        AISP2_DASHBOARD_STATE.kpis.teamsLoaded
    );

    setTextIfExists(
        "[data-kpi-players]",
        AISP2_DASHBOARD_STATE.kpis.playersLoaded
    );

    setTextIfExists(
        "[data-kpi-rosters]",
        AISP2_DASHBOARD_STATE.kpis.rosterEntries
    );

    setTextIfExists(
        "[data-kpi-predictions]",
        AISP2_DASHBOARD_STATE.kpis.predictionsRun
    );
}


/* ============================================================
   SECTION 09 - LAST UPDATED RENDERING
   ============================================================ */

function renderLastUpdated() {

    if (!AISP2_DASHBOARD_STATE.lastUpdatedAt) {
        return;
    }

    const formattedTime =
        new Date(
            AISP2_DASHBOARD_STATE.lastUpdatedAt
        ).toLocaleString();

    setTextIfExists(
        "[data-dashboard-last-updated]",
        formattedTime
    );
}


/* ============================================================
   SECTION 10 - ERROR RENDERING
   ============================================================ */

function renderDashboardError(message) {

    setTextIfExists(
        "[data-dashboard-error]",
        message || "Dashboard error"
    );

    const errorPanels =
        document.querySelectorAll(
            "[data-dashboard-error-panel]"
        );

    errorPanels.forEach(
        function(panel) {
            panel.classList.add(
                "visible"
            );
        }
    );
}


/* ============================================================
   SECTION 11 - LOADING STATE
   ============================================================ */

function setDashboardLoading(isLoading) {

    const loadingNodes =
        document.querySelectorAll(
            "[data-dashboard-loading]"
        );

    loadingNodes.forEach(
        function(node) {

            node.style.display =
                isLoading
                    ? "inline-flex"
                    : "none";
        }
    );

    const refreshButtons =
        document.querySelectorAll(
            "[data-dashboard-refresh]"
        );

    refreshButtons.forEach(
        function(button) {

            button.disabled =
                isLoading;

            button.innerText =
                isLoading
                    ? "Refreshing..."
                    : "Refresh";
        }
    );
}


/* ============================================================
   SECTION 12 - AUTO REFRESH
   ============================================================ */

function startDashboardAutoRefresh() {

    setInterval(
        refreshDashboardData,
        AISP2_DASHBOARD_STATE.refreshIntervalMs
    );
}


/* ============================================================
   SECTION 13 - DOM UTILITY HELPERS
   ============================================================ */

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


function setHTMLIfExists(
    selector,
    value
) {

    const element =
        document.querySelector(selector);

    if (!element) {
        return;
    }

    element.innerHTML =
        value;
}


/* ============================================================
   SECTION 14 - FUTURE CHART HOOKS
   ============================================================ */

function initializeDashboardCharts() {

    /*
    Future use:
        - Win probability charts
        - Player trend charts
        - Team strength charts
        - Statcast charts
        - Model performance charts
    */

    return null;
}


function renderPlaceholderChart(
    selector,
    label
) {

    const element =
        document.querySelector(selector);

    if (!element) {
        return;
    }

    element.innerHTML =
        "<div class='chart-placeholder'>" +
        label +
        "</div>";
}


/* ============================================================
   SECTION 15 - FUTURE DATA HOOKS
   ============================================================ */

async function fetchTeamCounts() {

    /*
    Future endpoint:
        /api/teams/count
    */

    return {
        teamsLoaded: 0
    };
}


async function fetchPlayerCounts() {

    /*
    Future endpoint:
        /api/players/count
    */

    return {
        playersLoaded: 0
    };
}


async function fetchPredictionCounts() {

    /*
    Future endpoint:
        /api/predictions/count
    */

    return {
        predictionsRun: 0
    };
}


/* ============================================================
   SECTION 16 - DASHBOARD ROADMAP
   ============================================================ */

/*

16.01 Live database counts

16.02 Team ingestion status

16.03 Player ingestion status

16.04 Roster ingestion status

16.05 Statcast ingestion status

16.06 Probability model health

16.07 ML model performance charts

16.08 User-friendly analytics panels

16.09 Advanced dashboard filters

16.10 Exportable reports

*/
/* ============================================================
   PHASE 14 PART 7.1 - DASHBOARD SCROLL RESTORE FIX
   FILE: static/js/dashboard.js
   PURPOSE:
   Prevent the browser from reopening the dashboard halfway down
   the page after reload/navigation.
   ============================================================ */

(function initializeAISP2DashboardScrollRestoreFix() {
    "use strict";

    try {
        if ("scrollRestoration" in window.history) {
            window.history.scrollRestoration = "manual";
        }

        document.body.classList.add("aisp2-disable-scroll-restore");

        window.addEventListener("load", function resetDashboardScrollPosition() {
            const path = String(window.location.pathname || "").toLowerCase();

            if (
                path === "/" ||
                path.includes("dashboard") ||
                path.includes("chat")
            ) {
                window.requestAnimationFrame(function scrollToTopFrameOne() {
                    window.scrollTo(0, 0);
                    window.requestAnimationFrame(function scrollToTopFrameTwo() {
                        window.scrollTo(0, 0);
                    });
                });
            }
        });
    } catch (error) {
        return null;
    }
}());

window.AISP2_DASHBOARD_SCROLL_RESTORE_FIX_PHASE_14_PART_7_1 = true;

