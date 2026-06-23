/* ============================================================
   AISP2 BASEBALL
   FILE: static/js/aisp2.js
   PURPOSE: global frontend behavior, page initialization,
   UI utilities, navigation polish, status helpers, and future
   shared application functions
   ============================================================ */


/* ============================================================
   SECTION 01 - GLOBAL APP STATE
   ============================================================ */

const AISP2_APP_STATE = {
    appName: "AISP2 Baseball",
    version: "1.0.0",
    initialized: false,
    currentPage: window.location.pathname,
    startedAt: new Date().toISOString()
};


/* ============================================================
   SECTION 02 - DOM READY INITIALIZATION
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    initializeAISP2App
);


function initializeAISP2App() {

    if (AISP2_APP_STATE.initialized) {
        return;
    }

    markCurrentNavigationLink();

    initializeSmoothAnchors();

    initializeExternalLinks();

    initializeKeyboardShortcuts();

    AISP2_APP_STATE.initialized = true;

    console.log(
        "AISP2 frontend initialized:",
        AISP2_APP_STATE
    );
}


/* ============================================================
   SECTION 03 - NAVIGATION HELPERS
   ============================================================ */

function markCurrentNavigationLink() {

    const navLinks =
        document.querySelectorAll(
            ".nav-links a"
        );

    navLinks.forEach(
        function(link) {

            const linkPath =
                new URL(
                    link.href,
                    window.location.origin
                ).pathname;

            if (linkPath === window.location.pathname) {

                link.classList.add(
                    "active-nav-link"
                );
            }
        }
    );
}


/* ============================================================
   SECTION 04 - SMOOTH ANCHOR LINKS
   ============================================================ */

function initializeSmoothAnchors() {

    const anchorLinks =
        document.querySelectorAll(
            'a[href^="#"]'
        );

    anchorLinks.forEach(
        function(link) {

            link.addEventListener(
                "click",
                function(event) {

                    const targetId =
                        link.getAttribute("href");

                    if (
                        !targetId ||
                        targetId === "#"
                    ) {
                        return;
                    }

                    const targetElement =
                        document.querySelector(targetId);

                    if (!targetElement) {
                        return;
                    }

                    event.preventDefault();

                    targetElement.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                }
            );
        }
    );
}


/* ============================================================
   SECTION 05 - EXTERNAL LINK SAFETY
   ============================================================ */

function initializeExternalLinks() {

    const links =
        document.querySelectorAll("a");

    links.forEach(
        function(link) {

            const href =
                link.getAttribute("href");

            if (!href) {
                return;
            }

            if (
                href.startsWith("http") &&
                !href.includes(window.location.hostname)
            ) {

                link.setAttribute(
                    "target",
                    "_blank"
                );

                link.setAttribute(
                    "rel",
                    "noopener noreferrer"
                );
            }
        }
    );
}


/* ============================================================
   SECTION 06 - KEYBOARD SHORTCUTS
   ============================================================ */

function initializeKeyboardShortcuts() {

    document.addEventListener(
        "keydown",
        function(event) {

            if (
                event.key === "/" &&
                !isUserTyping()
            ) {

                const chatInput =
                    document.getElementById(
                        "chat-input"
                    );

                if (chatInput) {
                    event.preventDefault();
                    chatInput.focus();
                }
            }

            if (
                event.key === "Escape" &&
                document.activeElement
            ) {

                document.activeElement.blur();
            }
        }
    );
}


function isUserTyping() {

    const activeElement =
        document.activeElement;

    if (!activeElement) {
        return false;
    }

    const tagName =
        activeElement.tagName.toLowerCase();

    return (
        tagName === "input" ||
        tagName === "textarea" ||
        activeElement.isContentEditable
    );
}


/* ============================================================
   SECTION 07 - UI HELPERS
   ============================================================ */

function createElement(
    tagName,
    className,
    textContent
) {

    const element =
        document.createElement(tagName);

    if (className) {
        element.className = className;
    }

    if (textContent) {
        element.innerText = textContent;
    }

    return element;
}


function safeSetText(
    selector,
    text
) {

    const element =
        document.querySelector(selector);

    if (!element) {
        return;
    }

    element.innerText =
        text;
}


function safeSetHTML(
    selector,
    html
) {

    const element =
        document.querySelector(selector);

    if (!element) {
        return;
    }

    element.innerHTML =
        html;
}


/* ============================================================
   SECTION 08 - API HELPERS
   ============================================================ */

async function aisp2FetchJSON(
    url,
    options = {}
) {

    const response =
        await fetch(
            url,
            {
                headers: {
                    "Content-Type": "application/json",
                    ...(options.headers || {})
                },
                ...options
            }
        );

    let payload = {};

    try {

        payload =
            await response.json();

    } catch (error) {

        throw new Error(
            "AISP2 received an invalid JSON response."
        );
    }

    if (!response.ok) {

        throw new Error(
            payload.error ||
            payload.detail ||
            "AISP2 request failed."
        );
    }

    return payload;
}


/* ============================================================
   SECTION 09 - STATUS HELPERS
   ============================================================ */

async function checkAISP2Health() {

    try {

        const payload =
            await aisp2FetchJSON(
                "/health"
            );

        return {
            ok: true,
            payload: payload
        };

    } catch (error) {

        return {
            ok: false,
            error: error.message
        };
    }
}


async function updateHealthBadge() {

    const badge =
        document.querySelector(
            "[data-health-badge]"
        );

    if (!badge) {
        return;
    }

    const result =
        await checkAISP2Health();

    if (result.ok) {

        badge.innerText =
            "Online";

        badge.classList.add(
            "is-online"
        );

        badge.classList.remove(
            "is-offline"
        );

    } else {

        badge.innerText =
            "Offline";

        badge.classList.add(
            "is-offline"
        );

        badge.classList.remove(
            "is-online"
        );
    }
}


/* ============================================================
   SECTION 10 - COPY HELPERS
   ============================================================ */

async function copyTextToClipboard(text) {

    if (
        navigator.clipboard &&
        navigator.clipboard.writeText
    ) {

        await navigator.clipboard.writeText(
            text
        );

        return true;
    }

    const temporaryInput =
        document.createElement("textarea");

    temporaryInput.value =
        text;

    temporaryInput.style.position =
        "fixed";

    temporaryInput.style.opacity =
        "0";

    document.body.appendChild(
        temporaryInput
    );

    temporaryInput.select();

    document.execCommand(
        "copy"
    );

    document.body.removeChild(
        temporaryInput
    );

    return true;
}


/* ============================================================
   SECTION 11 - TOAST SYSTEM
   ============================================================ */

function showAISP2Toast(
    message,
    type = "info"
) {

    let toastContainer =
        document.querySelector(
            ".aisp2-toast-container"
        );

    if (!toastContainer) {

        toastContainer =
            document.createElement("div");

        toastContainer.className =
            "aisp2-toast-container";

        document.body.appendChild(
            toastContainer
        );
    }

    const toast =
        document.createElement("div");

    toast.className =
        "aisp2-toast " + type;

    toast.innerText =
        message;

    toastContainer.appendChild(
        toast
    );

    setTimeout(
        function() {
            toast.classList.add(
                "visible"
            );
        },
        10
    );

    setTimeout(
        function() {

            toast.classList.remove(
                "visible"
            );

            setTimeout(
                function() {

                    if (toast.parentNode) {
                        toast.parentNode.removeChild(
                            toast
                        );
                    }

                },
                250
            );

        },
        3200
    );
}


/* ============================================================
   SECTION 12 - FUTURE PAGE REGISTRY
   ============================================================ */

const AISP2_PAGE_REGISTRY = {
    home: "/",
    prediction: "/tools/prediction",
    status: "/project/status",
    roadmap: "/project/roadmap",
    sources: "/project/data-sources",
    models: "/project/ml-roadmap",
    api: "/docs"
};


/* ============================================================
   SECTION 13 - FUTURE GLOBAL ROADMAP
   ============================================================ */

/*

13.01 Move all inline page JavaScript into static files.

13.02 Add route-aware page initialization.

13.03 Add frontend state manager.

13.04 Add reusable API client.

13.05 Add component rendering helpers.

13.06 Add toast notifications.

13.07 Add loading indicators.

13.08 Add client-side error boundaries.

13.09 Add keyboard shortcut command palette.

13.10 Add user settings panel.

*/