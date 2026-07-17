/* ============================================================
   AISP2 BASEBALL INTELLIGENCE PLATFORM
   FILE: static/js/account.js
   PHASE: 13 PART 7.0
   PURPOSE:
   Account dashboard runtime behavior for secure account pages.

   Supports:
   - /account user dashboard
   - /ceo CEO command dashboard
   - /api/auth/me session check
   - /api/auth/admin/overview CEO metrics check
   - future saved-search capture hooks
   - future player/team subscription hooks
   - future prediction-history hooks
   - future model-feedback hooks

   Security note:
   This file never stores passwords, raw session tokens, bootstrap
   tokens, or secrets. Authentication is enforced server-side by
   HttpOnly cookies and protected FastAPI routes.
   ============================================================ */


/* ============================================================
   SECTION 01 - RUNTIME STATE
   ============================================================ */

(function initializeAISP2AccountRuntime() {
    "use strict";

    const ACCOUNT_RUNTIME_VERSION = "phase_13_part_7_0_account_dashboard_behavior";

    const state = {
        initialized: false,
        pageType: detectPageType(),
        auth: {
            checked: false,
            authenticated: false,
            account: null,
            session: null,
            error: null
        },
        admin: {
            checked: false,
            allowed: false,
            overview: null,
            error: null
        },
        hooks: {
            savedSearchReady: true,
            playerSubscriptionReady: true,
            teamSubscriptionReady: true,
            predictionHistoryReady: true,
            modelFeedbackReady: true
        },
        diagnostics: {
            startedAt: new Date().toISOString(),
            runtimeVersion: ACCOUNT_RUNTIME_VERSION,
            lastUpdatedAt: null,
            requestCount: 0,
            failedRequestCount: 0
        }
    };


    /* ========================================================
       SECTION 02 - BASIC HELPERS
       ======================================================== */

    function detectPageType() {
        const html = document.documentElement;
        const page = html ? html.getAttribute("data-aisp2-page") : "";

        if (page === "admin-dashboard") {
            return "admin";
        }

        if (page === "account-dashboard") {
            return "account";
        }

        if (window.location.pathname === "/ceo") {
            return "admin";
        }

        if (window.location.pathname === "/account") {
            return "account";
        }

        return "unknown";
    }

    function nowIso() {
        return new Date().toISOString();
    }

    function safeText(value, fallback) {
        if (value === null || value === undefined || value === "") {
            return fallback || "Not Available";
        }

        return String(value);
    }

    function safeNumber(value, fallback) {
        const numeric = Number(value);

        if (!Number.isFinite(numeric)) {
            return fallback || 0;
        }

        return numeric;
    }

    function titleCase(value) {
        return safeText(value, "")
            .replace(/[_-]+/g, " ")
            .replace(/\s+/g, " ")
            .trim()
            .replace(/\b\w/g, function capitalize(letter) {
                return letter.toUpperCase();
            });
    }

    function formatBoolean(value) {
        if (value === true || value === "true" || value === "True" || value === "1" || value === 1) {
            return "Yes";
        }

        if (value === false || value === "false" || value === "False" || value === "0" || value === 0) {
            return "No";
        }

        return "Unknown";
    }

    function formatNumber(value) {
        const numeric = safeNumber(value, 0);
        return new Intl.NumberFormat("en-US").format(numeric);
    }

    function formatDateTime(value) {
        if (!value || value === "Not Available") {
            return "Not Available";
        }

        const parsed = new Date(value);

        if (Number.isNaN(parsed.getTime())) {
            return safeText(value, "Not Available");
        }

        return parsed.toLocaleString([], {
            year: "numeric",
            month: "short",
            day: "2-digit",
            hour: "numeric",
            minute: "2-digit"
        });
    }

    function logDiagnostic(message, payload) {
        if (window.console && typeof window.console.info === "function") {
            window.console.info("[AISP2 Account]", message, payload || "");
        }
    }

    function warnDiagnostic(message, payload) {
        if (window.console && typeof window.console.warn === "function") {
            window.console.warn("[AISP2 Account]", message, payload || "");
        }
    }


    /* ========================================================
       SECTION 03 - DOM HELPERS
       ======================================================== */

    function query(selector, root) {
        return (root || document).querySelector(selector);
    }

    function queryAll(selector, root) {
        return Array.prototype.slice.call((root || document).querySelectorAll(selector));
    }

    function setText(selector, value, root) {
        const element = query(selector, root);

        if (!element) {
            return false;
        }

        element.textContent = safeText(value);
        return true;
    }

    function setDataText(key, value) {
        const nodes = queryAll("[data-account-value='" + key + "']");

        nodes.forEach(function updateNode(node) {
            node.textContent = safeText(value);
        });

        return nodes.length;
    }

    function setDataStatus(key, value, statusClass) {
        const nodes = queryAll("[data-account-status='" + key + "']");

        nodes.forEach(function updateStatus(node) {
            node.textContent = safeText(value);
            node.classList.remove("good", "warn", "danger", "info");

            if (statusClass) {
                node.classList.add(statusClass);
            }
        });

        return nodes.length;
    }

    function createStatusBanner() {
        let banner = query("[data-account-runtime-banner]");

        if (banner) {
            return banner;
        }

        banner = document.createElement("section");
        banner.setAttribute("data-account-runtime-banner", "true");
        banner.style.position = "relative";
        banner.style.zIndex = "3";
        banner.style.width = "min(1540px, calc(100vw - 38px))";
        banner.style.margin = "16px auto 0";
        banner.style.padding = "12px 14px";
        banner.style.border = "1px solid rgba(143, 211, 255, 0.14)";
        banner.style.borderRadius = "16px";
        banner.style.background = "rgba(8, 29, 47, 0.76)";
        banner.style.color = "rgba(231, 244, 255, 0.88)";
        banner.style.fontFamily = "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
        banner.style.fontSize = "0.84rem";
        banner.style.lineHeight = "1.45";

        const topbar = query(".account-topbar") || query(".admin-topbar");

        if (topbar && topbar.parentNode) {
            topbar.parentNode.insertBefore(banner, topbar.nextSibling);
        } else {
            document.body.insertBefore(banner, document.body.firstChild);
        }

        return banner;
    }

    function updateBanner(message, tone) {
        const banner = createStatusBanner();
        banner.textContent = message;

        if (tone === "good") {
            banner.style.borderColor = "rgba(137, 245, 189, 0.26)";
            banner.style.color = "#8df5bd";
        } else if (tone === "danger") {
            banner.style.borderColor = "rgba(255, 143, 143, 0.30)";
            banner.style.color = "#ff8f8f";
        } else if (tone === "warn") {
            banner.style.borderColor = "rgba(255, 226, 158, 0.30)";
            banner.style.color = "#ffe29e";
        } else {
            banner.style.borderColor = "rgba(143, 211, 255, 0.14)";
            banner.style.color = "rgba(231, 244, 255, 0.88)";
        }
    }


    /* ========================================================
       SECTION 04 - SAFE FETCH
       ======================================================== */

    async function fetchJson(url, options) {
        state.diagnostics.requestCount += 1;

        const requestOptions = Object.assign({
            method: "GET",
            credentials: "same-origin",
            headers: {
                "Accept": "application/json"
            }
        }, options || {});

        try {
            const response = await fetch(url, requestOptions);
            const text = await response.text();

            let payload = {};

            if (text) {
                try {
                    payload = JSON.parse(text);
                } catch (jsonError) {
                    payload = {
                        raw: text,
                        parse_error: String(jsonError)
                    };
                }
            }

            if (!response.ok) {
                const error = new Error("Request failed: " + response.status);
                error.status = response.status;
                error.payload = payload;
                throw error;
            }

            return payload;
        } catch (error) {
            state.diagnostics.failedRequestCount += 1;
            throw error;
        } finally {
            state.diagnostics.lastUpdatedAt = nowIso();
        }
    }


    /* ========================================================
       SECTION 05 - AUTH SESSION CHECK
       ======================================================== */

    async function loadCurrentAccount() {
        try {
            const payload = await fetchJson("/api/auth/me");

            state.auth.checked = true;
            state.auth.authenticated = Boolean(payload.authenticated);
            state.auth.account = payload.account || null;
            state.auth.session = payload.session || null;
            state.auth.error = null;

            renderCurrentAccount();

            return payload;
        } catch (error) {
            state.auth.checked = true;
            state.auth.authenticated = false;
            state.auth.account = null;
            state.auth.session = null;
            state.auth.error = String(error.message || error);

            renderCurrentAccount();

            return null;
        }
    }

    function renderCurrentAccount() {
        const account = state.auth.account || {};
        const session = state.auth.session || {};

        setDataText("username", account.username || "Not Available");
        setDataText("display_name", account.display_name || account.username || "AISP2 User");
        setDataText("role", titleCase(account.role || "user"));
        setDataText("account_status", titleCase(account.account_status || "unknown"));
        setDataText("is_ceo_master", formatBoolean(account.is_ceo_master));
        setDataText("last_login_at", formatDateTime(account.last_login_at));
        setDataText("last_seen_at", formatDateTime(account.last_seen_at));
        setDataText("session_status", titleCase(session.session_status || "unknown"));
        setDataText("session_expires_at", formatDateTime(session.expires_at));

        if (!state.auth.checked) {
            updateBanner("Checking secure account session...", "info");
            return;
        }

        if (state.auth.authenticated) {
            const role = account.role || "user";
            updateBanner("Authenticated as " + safeText(account.username, "account") + " | Role: " + titleCase(role), "good");
            setDataStatus("auth", "Authenticated", "good");
        } else {
            updateBanner("Authentication could not be confirmed. Please log in again.", "danger");
            setDataStatus("auth", "Not Authenticated", "danger");
        }
    }


    /* ========================================================
       SECTION 06 - ADMIN OVERVIEW
       ======================================================== */

    async function loadAdminOverview() {
        if (state.pageType !== "admin") {
            return null;
        }

        try {
            const payload = await fetchJson("/api/auth/admin/overview");

            state.admin.checked = true;
            state.admin.allowed = true;
            state.admin.overview = payload;
            state.admin.error = null;

            renderAdminOverview(payload);

            return payload;
        } catch (error) {
            state.admin.checked = true;
            state.admin.allowed = false;
            state.admin.overview = null;
            state.admin.error = String(error.message || error);

            renderAdminOverview(null);

            return null;
        }
    }

    function renderAdminOverview(payload) {
        if (!payload) {
            setDataStatus("admin", "Admin API Unavailable", "danger");

            if (state.pageType === "admin") {
                updateBanner("CEO dashboard loaded, but admin overview API could not be reached.", "warn");
            }

            return;
        }

        const counts = payload.counts || {};

        setDataText("user_count", formatNumber(counts.users));
        setDataText("active_user_count", formatNumber(counts.active_users));
        setDataText("session_count", formatNumber(counts.sessions));
        setDataText("active_session_count", formatNumber(counts.active_sessions));
        setDataText("search_count", formatNumber(counts.saved_searches));
        setDataText("player_subscription_count", formatNumber(counts.player_subscriptions));
        setDataText("team_subscription_count", formatNumber(counts.team_subscriptions));
        setDataText("prediction_history_count", formatNumber(counts.prediction_history));
        setDataText("feedback_count", formatNumber(counts.model_feedback_events));
        setDataText("audit_count", formatNumber(counts.audit_events));

        setDataStatus("admin", "Admin API Ready", "good");
    }


    /* ========================================================
       SECTION 07 - ACCOUNT FEATURE HOOKS
       ======================================================== */

    function initializeSavedSearchHooks() {
        queryAll("[data-save-search]").forEach(function attachSaveSearch(node) {
            if (node.dataset.aisp2Hooked === "true") {
                return;
            }

            node.dataset.aisp2Hooked = "true";

            node.addEventListener("click", function handleSaveSearch(event) {
                event.preventDefault();

                updateBanner("Saved-search API hook is ready. Backend write route is the next phase.", "warn");
            });
        });
    }

    function initializeSubscriptionHooks() {
        queryAll("[data-follow-player], [data-follow-team]").forEach(function attachSubscription(node) {
            if (node.dataset.aisp2Hooked === "true") {
                return;
            }

            node.dataset.aisp2Hooked = "true";

            node.addEventListener("click", function handleSubscription(event) {
                event.preventDefault();

                const type = node.hasAttribute("data-follow-player") ? "player" : "team";
                updateBanner("Follow-" + type + " API hook is ready. Backend write route is the next phase.", "warn");
            });
        });
    }

    function initializePredictionHistoryHooks() {
        queryAll("[data-prediction-history-action]").forEach(function attachPredictionHistory(node) {
            if (node.dataset.aisp2Hooked === "true") {
                return;
            }

            node.dataset.aisp2Hooked = "true";

            node.addEventListener("click", function handlePredictionHistory(event) {
                event.preventDefault();

                updateBanner("Prediction-history API hook is ready. Backend write route is the next phase.", "warn");
            });
        });
    }

    function initializeModelFeedbackHooks() {
        queryAll("[data-model-feedback-action]").forEach(function attachModelFeedback(node) {
            if (node.dataset.aisp2Hooked === "true") {
                return;
            }

            node.dataset.aisp2Hooked = "true";

            node.addEventListener("click", function handleModelFeedback(event) {
                event.preventDefault();

                updateBanner("Model-feedback API hook is ready. Backend approval/training route is the next phase.", "warn");
            });
        });
    }


    /* ========================================================
       SECTION 08 - DASHBOARD DIAGNOSTIC PANEL
       ======================================================== */

    function createDiagnosticsPanel() {
        if (query("[data-account-diagnostics-panel]")) {
            return;
        }

        const shell = query(".account-shell") || query(".admin-shell");

        if (!shell) {
            return;
        }

        const panel = document.createElement("section");
        panel.className = "panel";
        panel.setAttribute("data-account-diagnostics-panel", "true");

        panel.innerHTML = [
            '<div class="panel-inner">',
            '<h2 class="section-title">Runtime Diagnostics</h2>',
            '<p class="section-copy">Frontend account runtime status. No secrets are displayed here.</p>',
            '<div class="metric-grid">',
            '<div class="metric-card info"><span>Runtime</span><strong data-account-value="runtime_version">Loading</strong></div>',
            '<div class="metric-card info"><span>Page Type</span><strong data-account-value="page_type">Loading</strong></div>',
            '<div class="metric-card good"><span>Auth</span><strong data-account-status="auth">Checking</strong></div>',
            '<div class="metric-card warn"><span>Admin</span><strong data-account-status="admin">Not Checked</strong></div>',
            '<div class="metric-card"><span>Requests</span><strong data-account-value="request_count">0</strong></div>',
            '<div class="metric-card"><span>Failures</span><strong data-account-value="failed_request_count">0</strong></div>',
            '</div>',
            '</div>'
        ].join("");

        shell.appendChild(panel);
    }

    function renderDiagnosticsPanel() {
        setDataText("runtime_version", ACCOUNT_RUNTIME_VERSION);
        setDataText("page_type", titleCase(state.pageType));
        setDataText("request_count", formatNumber(state.diagnostics.requestCount));
        setDataText("failed_request_count", formatNumber(state.diagnostics.failedRequestCount));
    }


    /* ========================================================
       SECTION 09 - TEMPLATE ENHANCEMENT
       ======================================================== */

    function addDataHooksToKnownMetricLabels() {
        const labelToKey = {
            "Total Users": "user_count",
            "Active Users": "active_user_count",
            "Total Sessions": "session_count",
            "Active Sessions": "active_session_count",
            "Saved Searches": "search_count",
            "Searches": "search_count",
            "Player Follows": "player_subscription_count",
            "Team Follows": "team_subscription_count",
            "Total Predictions": "prediction_history_count",
            "Predictions": "prediction_history_count",
            "Feedback Events": "feedback_count",
            "Audit Events": "audit_count",
            "Username": "username",
            "Role": "role",
            "Account Status": "account_status",
            "CEO Master": "is_ceo_master",
            "Last Login": "last_login_at"
        };

        queryAll(".metric-card, .identity-card, .executive-card").forEach(function inspectCard(card) {
            const label = query("span", card);
            const value = query("strong", card);

            if (!label || !value) {
                return;
            }

            const key = labelToKey[label.textContent.trim()];

            if (key && !value.hasAttribute("data-account-value")) {
                value.setAttribute("data-account-value", key);
            }
        });
    }

    function markDashboardReady() {
        document.documentElement.classList.add("aisp2-account-runtime-ready");
        document.documentElement.setAttribute("data-aisp2-account-runtime-version", ACCOUNT_RUNTIME_VERSION);
    }


    /* ========================================================
       SECTION 10 - STARTUP
       ======================================================== */

    async function start() {
        if (state.initialized) {
            return;
        }

        state.initialized = true;

        createDiagnosticsPanel();
        addDataHooksToKnownMetricLabels();

        updateBanner("Loading secure account runtime...", "info");

        initializeSavedSearchHooks();
        initializeSubscriptionHooks();
        initializePredictionHistoryHooks();
        initializeModelFeedbackHooks();

        await loadCurrentAccount();

        if (state.pageType === "admin") {
            await loadAdminOverview();
        }

        renderDiagnosticsPanel();
        markDashboardReady();

        logDiagnostic("Account runtime initialized.", {
            pageType: state.pageType,
            runtimeVersion: ACCOUNT_RUNTIME_VERSION
        });
    }

    function scheduleDiagnosticsRefresh() {
        window.setInterval(function refreshDiagnostics() {
            renderDiagnosticsPanel();
        }, 5000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function onReady() {
            start();
            scheduleDiagnosticsRefresh();
        });
    } else {
        start();
        scheduleDiagnosticsRefresh();
    }

    window.AISP2AccountRuntime = {
        version: ACCOUNT_RUNTIME_VERSION,
        state: state,
        reloadAuth: loadCurrentAccount,
        reloadAdminOverview: loadAdminOverview,
        renderDiagnostics: renderDiagnosticsPanel
    };
}());


/* ============================================================
   SECTION 11 - PHASE 13 PART 7.0 COMPLETION MARKER
   ============================================================ */

window.AISP2_ACCOUNT_JS_PHASE_13_PART_7 = true;

/* ============================================================
   AISP2 BASEBALL
   FILE: static/js/account.js
   PHASE 14 PART 4.0 - LIVE ACCOUNT DASHBOARD INTEGRATION

   PURPOSE:
   Hydrate the protected account dashboard with real account data:
   - saved searches
   - followed players
   - followed teams
   - prediction history

   APIs:
   - GET /api/account/searches
   - GET /api/account/subscriptions
   - GET /api/account/predictions
   ============================================================ */

(function initializeAISP2LiveAccountDashboardIntegration() {
    "use strict";

    const VERSION = "phase_14_part_4_0_live_account_dashboard_integration";

    const state = {
        searches: [],
        players: [],
        teams: [],
        predictions: [],
        failures: [],
        loadedAt: null
    };

    function $(selector) {
        return document.querySelector(selector);
    }

    function safeText(value, fallback) {
        const text = String(value ?? "").trim();
        return text || fallback || "";
    }

    function setStatus(message, kind) {
        const target = $("[data-account-live-status]");
        if (!target) {
            return;
        }

        target.textContent = message;
        target.dataset.status = kind || "info";
    }

    function setCount(name, value) {
        const target = $(`[data-account-live-count="${name}"]`);
        if (target) {
            target.textContent = String(value || 0);
        }
    }

    function listTarget(name) {
        return $(`[data-account-live-list="${name}"]`);
    }

    function clearList(name) {
        const target = listTarget(name);
        if (!target) {
            return null;
        }

        target.innerHTML = "";
        return target;
    }

    function emptyItem(message) {
        const node = document.createElement("div");
        node.className = "account-live-empty";
        node.textContent = message;
        return node;
    }

    function item(title, meta, detail) {
        const node = document.createElement("div");
        node.className = "account-live-item";

        const titleNode = document.createElement("strong");
        titleNode.textContent = safeText(title, "Untitled");

        const metaNode = document.createElement("span");
        metaNode.textContent = safeText(meta, "No metadata");

        node.appendChild(titleNode);
        node.appendChild(metaNode);

        if (detail) {
            const detailNode = document.createElement("p");
            detailNode.textContent = detail;
            node.appendChild(detailNode);
        }

        return node;
    }

    async function fetchJson(url) {
        const response = await fetch(url, {
            method: "GET",
            credentials: "same-origin",
            headers: {
                "Accept": "application/json"
            }
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

    function renderSearches(searches) {
        const target = clearList("searches");
        if (!target) {
            return;
        }

        setCount("searches", searches.length);

        if (!searches.length) {
            target.appendChild(emptyItem("No saved searches yet."));
            return;
        }

        searches.slice(0, 12).forEach((search) => {
            target.appendChild(item(
                search.query || search.entity_name || "Saved search",
                `${search.search_type || "search"} | ${search.source_page || "unknown"}`,
                [
                    search.player_name,
                    search.team_name,
                    search.outcome_label
                ].filter(Boolean).join(" | ")
            ));
        });
    }

    function renderPlayers(players) {
        const target = clearList("players");
        if (!target) {
            return;
        }

        setCount("players", players.length);

        if (!players.length) {
            target.appendChild(emptyItem("No followed players yet."));
            return;
        }

        players.slice(0, 12).forEach((player) => {
            target.appendChild(item(
                player.player_name || `Player ${player.player_id || player.mlb_player_id || ""}`,
                player.team_name || "Team pending",
                `Status: ${player.status || "active"}`
            ));
        });
    }

    function renderTeams(teams) {
        const target = clearList("teams");
        if (!target) {
            return;
        }

        setCount("teams", teams.length);

        if (!teams.length) {
            target.appendChild(emptyItem("No followed teams yet."));
            return;
        }

        teams.slice(0, 12).forEach((team) => {
            target.appendChild(item(
                team.team_name || `Team ${team.team_id || team.mlb_team_id || ""}`,
                team.team_abbreviation || "MLB team",
                `Status: ${team.status || "active"}`
            ));
        });
    }

    function renderPredictions(predictions) {
        const target = clearList("predictions");
        if (!target) {
            return;
        }

        setCount("predictions", predictions.length);

        if (!predictions.length) {
            target.appendChild(emptyItem("No prediction history yet."));
            return;
        }

        predictions.slice(0, 20).forEach((prediction) => {
            const probability = prediction.predicted_probability;
            const confidence = prediction.confidence;

            target.appendChild(item(
                `${prediction.player_name_snapshot || "Player"} - ${prediction.outcome_label || prediction.outcome_key || "Prediction"}`,
                [
                    prediction.team_name_snapshot,
                    probability !== null && probability !== undefined ? `${probability}%` : null,
                    confidence !== null && confidence !== undefined ? `Confidence ${confidence}%` : null
                ].filter(Boolean).join(" | "),
                `Lifecycle: ${prediction.prediction_lifecycle || "pending_result"} | Model: ${prediction.model_name || "AISP2"}`
            ));
        });
    }

    function injectStyles() {
        if (document.querySelector("[data-aisp2-account-live-style]")) {
            return;
        }

        const style = document.createElement("style");
        style.dataset.aisp2AccountLiveStyle = "true";
        style.textContent = `
            .account-live-data-shell {
                margin: 24px auto;
                width: min(1180px, calc(100% - 32px));
                padding: clamp(18px, 3vw, 28px);
                border-radius: 30px;
                border: 1px solid rgba(77, 216, 255, 0.22);
                background:
                    radial-gradient(circle at 0% 0%, rgba(77, 216, 255, 0.14), transparent 36%),
                    rgba(5, 18, 38, 0.72);
                box-shadow: 0 24px 80px rgba(0,0,0,0.26);
            }
            .account-live-eyebrow {
                color: #73e8ff;
                font-size: 0.72rem;
                font-weight: 950;
                text-transform: uppercase;
                letter-spacing: 0.12em;
            }
            .account-live-header h2 {
                margin: 8px 0 8px;
                color: rgba(244,251,255,0.97);
                font-size: clamp(1.8rem, 4vw, 3.2rem);
                letter-spacing: -0.05em;
            }
            .account-live-header p {
                margin: 0;
                color: rgba(220, 238, 250, 0.68);
                line-height: 1.55;
            }
            .account-live-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 14px;
                margin-top: 18px;
            }
            .account-live-panel {
                min-height: 220px;
                padding: 16px;
                border-radius: 22px;
                border: 1px solid rgba(77, 216, 255, 0.18);
                background: rgba(255,255,255,0.045);
            }
            .account-live-panel.wide {
                grid-column: 1 / -1;
            }
            .account-live-panel-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                margin-bottom: 12px;
            }
            .account-live-panel-header span {
                color: rgba(225,242,255,0.72);
                font-weight: 950;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                font-size: 0.74rem;
            }
            .account-live-panel-header strong {
                color: #8df5bd;
                font-size: 1.4rem;
            }
            .account-live-list {
                display: grid;
                gap: 10px;
            }
            .account-live-item,
            .account-live-empty {
                padding: 12px;
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.08);
                background: rgba(0,0,0,0.16);
            }
            .account-live-item strong {
                display: block;
                color: rgba(244,251,255,0.96);
                margin-bottom: 4px;
            }
            .account-live-item span,
            .account-live-item p,
            .account-live-empty {
                color: rgba(220,238,250,0.66);
                font-size: 0.88rem;
                line-height: 1.45;
            }
            .account-live-item p {
                margin: 6px 0 0;
            }
            .account-live-status {
                margin-top: 14px;
                color: rgba(220,238,250,0.68);
                font-weight: 850;
            }
            .account-live-status[data-status="good"] { color: #8df5bd; }
            .account-live-status[data-status="warn"] { color: #ffe29e; }
            .account-live-status[data-status="danger"] { color: #ff9f9f; }
            @media (max-width: 980px) {
                .account-live-grid {
                    grid-template-columns: 1fr;
                }
            }
        `;
        document.head.appendChild(style);
    }

    async function loadSearches() {
        const payload = await fetchJson("/api/account/searches?limit=25");
        state.searches = payload.searches || [];
        renderSearches(state.searches);
    }

    async function loadSubscriptions() {
        const payload = await fetchJson("/api/account/subscriptions?kind=all&limit=100");
        state.players = payload.players || [];
        state.teams = payload.teams || [];
        renderPlayers(state.players);
        renderTeams(state.teams);
    }

    async function loadPredictions() {
        const payload = await fetchJson("/api/account/predictions?limit=25");
        state.predictions = payload.predictions || [];
        renderPredictions(state.predictions);
    }

    async function reloadLiveAccountDashboard() {
        injectStyles();
        setStatus("Loading live account data...", "info");

        const jobs = [
            loadSearches(),
            loadSubscriptions(),
            loadPredictions()
        ];

        const results = await Promise.allSettled(jobs);

        state.failures = results
            .filter((result) => result.status === "rejected")
            .map((result) => String(result.reason && result.reason.message ? result.reason.message : result.reason));

        state.loadedAt = new Date().toISOString();

        if (state.failures.length) {
            if (state.failures.some((message) => message.toLowerCase().includes("authentication"))) {
                setStatus("Login required to load live account data.", "warn");
            } else {
                setStatus(`Some account data could not load: ${state.failures.join(" | ")}`, "danger");
            }
        } else {
            setStatus("Live account data loaded.", "good");
        }

        return state;
    }

    function boot() {
        if (!$("[data-account-live-data-shell]")) {
            return;
        }

        reloadLiveAccountDashboard();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.AISP2LiveAccountDashboardIntegration = {
        version: VERSION,
        state,
        reload: reloadLiveAccountDashboard,
        renderSearches,
        renderPlayers,
        renderTeams,
        renderPredictions
    };

    window.AISP2_LIVE_ACCOUNT_DASHBOARD_PHASE_14_PART_4 = true;
}());

