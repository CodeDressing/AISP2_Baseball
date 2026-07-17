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
