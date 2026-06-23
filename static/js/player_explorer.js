/* ============================================================
   AISP2 BASEBALL
   FILE: static/js/player_explorer.js
   PURPOSE: Player Explorer interactivity, demo player switching,
   team-player selector behavior, profile rendering, and future
   live MLB player API integration
   ============================================================ */


/* ============================================================
   SECTION 01 - PLAYER EXPLORER STATE
   FILE: static/js/player_explorer.js
   PURPOSE: central state and demo data for the Player Explorer
   ============================================================ */

const AISP2_PLAYER_EXPLORER_STATE = {
    initialized: false,
    selectedTeam: "New York Yankees",
    selectedPlayer: "Aaron Judge",
    selectedFocus: "Batting Profile"
};


const AISP2_PLAYER_DEMO_DATA = {
    "New York Yankees": {
        abbreviation: "NYY",
        players: {
            "Aaron Judge": {
                team: "New York Yankees",
                position: "Outfielder",
                bats: "Right",
                throws: "Right",
                type: "Power Bat",
                role: "Home Run / RBI / Total Bases",
                summary: "Elite power hitter with premium exit velocity, barrel-rate upside, middle-of-the-order run production, and future home run probability model relevance.",
                avg: ".000",
                ops: ".000",
                hr: "0",
                rbi: "0",
                exitVelocity: "0",
                barrelRate: "0%",
                hardHitRate: "0%",
                launchAngle: "0",
                aiSummary: "Aaron Judge is the current demo profile for AISP2 player intelligence. Future models will evaluate power output, contact quality, recent form, matchup context, and Statcast signals."
            },
            "Giancarlo Stanton": {
                team: "New York Yankees",
                position: "Designated Hitter",
                bats: "Right",
                throws: "Right",
                type: "Extreme Power Bat",
                role: "Home Run / Total Bases",
                summary: "High-variance power hitter with elite raw exit velocity and future home run modeling relevance.",
                avg: ".000",
                ops: ".000",
                hr: "0",
                rbi: "0",
                exitVelocity: "0",
                barrelRate: "0%",
                hardHitRate: "0%",
                launchAngle: "0",
                aiSummary: "Giancarlo Stanton profiles as a power-first demo player where barrel rate, pitch location, and health context will matter heavily."
            }
        }
    },

    "Los Angeles Dodgers": {
        abbreviation: "LAD",
        players: {
            "Shohei Ohtani": {
                team: "Los Angeles Dodgers",
                position: "Designated Hitter",
                bats: "Left",
                throws: "Right",
                type: "Elite Two-Way Offensive Force",
                role: "Home Run / Hit / RBI",
                summary: "Elite offensive profile with power, contact quality, and future Statcast-driven probability model relevance.",
                avg: ".000",
                ops: ".000",
                hr: "0",
                rbi: "0",
                exitVelocity: "0",
                barrelRate: "0%",
                hardHitRate: "0%",
                launchAngle: "0",
                aiSummary: "Shohei Ohtani is a premium demo profile for future power, hit, and run production modeling."
            },
            "Mookie Betts": {
                team: "Los Angeles Dodgers",
                position: "Utility / Outfielder",
                bats: "Right",
                throws: "Right",
                type: "Contact-Power Blend",
                role: "Hit / Run / Total Bases",
                summary: "Balanced offensive player with contact skill, power upside, and strong future multi-outcome model fit.",
                avg: ".000",
                ops: ".000",
                hr: "0",
                rbi: "0",
                exitVelocity: "0",
                barrelRate: "0%",
                hardHitRate: "0%",
                launchAngle: "0",
                aiSummary: "Mookie Betts profiles as a flexible prediction target where hit probability, run scoring, and total bases will be strong categories."
            }
        }
    },

    "New York Mets": {
        abbreviation: "NYM",
        players: {
            "Juan Soto": {
                team: "New York Mets",
                position: "Outfielder",
                bats: "Left",
                throws: "Left",
                type: "Plate Discipline Bat",
                role: "Hit / RBI / Walk / Total Bases",
                summary: "Elite plate discipline profile with strong on-base skill, future hit probability, and run production relevance.",
                avg: ".000",
                ops: ".000",
                hr: "0",
                rbi: "0",
                exitVelocity: "0",
                barrelRate: "0%",
                hardHitRate: "0%",
                launchAngle: "0",
                aiSummary: "Juan Soto is a strong demo profile for plate discipline, hit probability, walk probability, and run production modeling."
            },
            "Pete Alonso": {
                team: "New York Mets",
                position: "First Base",
                bats: "Right",
                throws: "Right",
                type: "Power Slugger",
                role: "Home Run / RBI / Total Bases",
                summary: "Power-first hitter with strong future home run and RBI prediction relevance.",
                avg: ".000",
                ops: ".000",
                hr: "0",
                rbi: "0",
                exitVelocity: "0",
                barrelRate: "0%",
                hardHitRate: "0%",
                launchAngle: "0",
                aiSummary: "Pete Alonso is a power-focused demo player where barrel rate, matchup, and park factor will matter."
            }
        }
    },

    "Atlanta Braves": {
        abbreviation: "ATL",
        players: {
            "Ronald Acuna Jr.": {
                team: "Atlanta Braves",
                position: "Outfielder",
                bats: "Right",
                throws: "Right",
                type: "Power-Speed Star",
                role: "Hit / Run / Home Run / Stolen Base",
                summary: "Dynamic offensive profile with power-speed impact and future multi-outcome modeling relevance.",
                avg: ".000",
                ops: ".000",
                hr: "0",
                rbi: "0",
                exitVelocity: "0",
                barrelRate: "0%",
                hardHitRate: "0%",
                launchAngle: "0",
                aiSummary: "Ronald Acuna Jr. is a multi-category demo profile for power, speed, run scoring, and hit probability models."
            },
            "Matt Olson": {
                team: "Atlanta Braves",
                position: "First Base",
                bats: "Left",
                throws: "Right",
                type: "Left-Handed Power Bat",
                role: "Home Run / RBI / Total Bases",
                summary: "Left-handed power hitter with future Statcast and matchup-based home run modeling relevance.",
                avg: ".000",
                ops: ".000",
                hr: "0",
                rbi: "0",
                exitVelocity: "0",
                barrelRate: "0%",
                hardHitRate: "0%",
                launchAngle: "0",
                aiSummary: "Matt Olson profiles as a power-focused demo player with strong future home run and total bases relevance."
            }
        }
    }
};


/* ============================================================
   SECTION 02 - DOM READY INITIALIZATION
   FILE: static/js/player_explorer.js
   PURPOSE: initialize Player Explorer once the page is loaded
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    initializeAISP2PlayerExplorer
);


function initializeAISP2PlayerExplorer() {

    if (AISP2_PLAYER_EXPLORER_STATE.initialized) {
        return;
    }

    bindPlayerExplorerEvents();

    populatePlayerDropdown();

    renderSelectedPlayer();

    AISP2_PLAYER_EXPLORER_STATE.initialized = true;
}


/* ============================================================
   SECTION 03 - DOM HELPERS
   FILE: static/js/player_explorer.js
   PURPOSE: safely select and update Player Explorer elements
   ============================================================ */

function getPlayerTeamSelect() {
    return document.querySelector("[data-player-team]");
}


function getPlayerNameSelect() {
    return document.querySelector("[data-player-name]");
}


function getPlayerFocusSelect() {
    return document.querySelector("[data-player-focus]");
}


function getLoadPlayerButton() {
    return document.querySelector("[data-player-load]");
}


function setTextIfExists(selector, value) {

    const element = document.querySelector(selector);

    if (!element) {
        return;
    }

    element.innerText = String(value);
}


/* ============================================================
   SECTION 04 - EVENT BINDING
   FILE: static/js/player_explorer.js
   PURPOSE: connect dropdowns and load button to render behavior
   ============================================================ */

function bindPlayerExplorerEvents() {

    const teamSelect = getPlayerTeamSelect();
    const playerSelect = getPlayerNameSelect();
    const focusSelect = getPlayerFocusSelect();
    const loadButton = getLoadPlayerButton();

    if (teamSelect) {
        teamSelect.addEventListener(
            "change",
            function() {
                AISP2_PLAYER_EXPLORER_STATE.selectedTeam = teamSelect.value;
                populatePlayerDropdown();
                renderSelectedPlayer();
            }
        );
    }

    if (playerSelect) {
        playerSelect.addEventListener(
            "change",
            function() {
                AISP2_PLAYER_EXPLORER_STATE.selectedPlayer = playerSelect.value;
                renderSelectedPlayer();
            }
        );
    }

    if (focusSelect) {
        focusSelect.addEventListener(
            "change",
            function() {
                AISP2_PLAYER_EXPLORER_STATE.selectedFocus = focusSelect.value;
                renderSelectedPlayer();
            }
        );
    }

    if (loadButton) {
        loadButton.addEventListener(
            "click",
            renderSelectedPlayer
        );
    }
}


/* ============================================================
   SECTION 05 - PLAYER DROPDOWN MANAGEMENT
   FILE: static/js/player_explorer.js
   PURPOSE: update player options when team selection changes
   ============================================================ */

function populatePlayerDropdown() {

    const playerSelect = getPlayerNameSelect();

    if (!playerSelect) {
        return;
    }

    const teamData = AISP2_PLAYER_DEMO_DATA[
        AISP2_PLAYER_EXPLORER_STATE.selectedTeam
    ];

    if (!teamData) {
        return;
    }

    playerSelect.innerHTML = "";

    const playerNames = Object.keys(teamData.players);

    playerNames.forEach(
        function(playerName) {

            const option = document.createElement("option");

            option.value = playerName;
            option.innerText = playerName;

            playerSelect.appendChild(option);
        }
    );

    if (!teamData.players[AISP2_PLAYER_EXPLORER_STATE.selectedPlayer]) {
        AISP2_PLAYER_EXPLORER_STATE.selectedPlayer = playerNames[0];
    }

    playerSelect.value = AISP2_PLAYER_EXPLORER_STATE.selectedPlayer;
}


/* ============================================================
   SECTION 06 - PLAYER RENDERING
   FILE: static/js/player_explorer.js
   PURPOSE: render selected demo player profile into the page
   ============================================================ */

function renderSelectedPlayer() {

    const teamData = AISP2_PLAYER_DEMO_DATA[
        AISP2_PLAYER_EXPLORER_STATE.selectedTeam
    ];

    if (!teamData) {
        return;
    }

    const player = teamData.players[
        AISP2_PLAYER_EXPLORER_STATE.selectedPlayer
    ];

    if (!player) {
        return;
    }

    setTextIfExists("[data-player-hero-name]", AISP2_PLAYER_EXPLORER_STATE.selectedPlayer);
    setTextIfExists("[data-player-hero-team]", player.team);
    setTextIfExists("[data-player-hero-position]", player.position);
    setTextIfExists("[data-player-hero-type]", player.type);
    setTextIfExists("[data-player-hero-role]", player.role);
    setTextIfExists("[data-player-hero-summary]", player.summary);

    setTextIfExists("[data-player-stat-avg]", player.avg);
    setTextIfExists("[data-player-stat-ops]", player.ops);
    setTextIfExists("[data-player-stat-hr]", player.hr);
    setTextIfExists("[data-player-stat-rbi]", player.rbi);

    setTextIfExists("[data-profile-full-name]", AISP2_PLAYER_EXPLORER_STATE.selectedPlayer);
    setTextIfExists("[data-profile-team]", player.team);
    setTextIfExists("[data-profile-position]", player.position);
    setTextIfExists("[data-profile-bats]", player.bats);
    setTextIfExists("[data-profile-throws]", player.throws);
    setTextIfExists("[data-profile-prediction-category]", player.role);

    setTextIfExists("[data-statcast-exit-velocity]", player.exitVelocity);
    setTextIfExists("[data-statcast-barrel-rate]", player.barrelRate);
    setTextIfExists("[data-statcast-hard-hit-rate]", player.hardHitRate);
    setTextIfExists("[data-statcast-launch-angle]", player.launchAngle);

    setTextIfExists("[data-player-ai-summary]", player.aiSummary);
}


/* ============================================================
   SECTION 07 - FUTURE LIVE API HOOKS
   FILE: static/js/player_explorer.js
   PURPOSE: placeholder functions for real MLB player API wiring
   ============================================================ */

async function fetchPlayersForTeamFromAPI(teamName) {

    /*
    Future endpoint:
        /api/teams/{team_id}/players
    */

    return [];
}


async function fetchPlayerProfileFromAPI(playerId) {

    /*
    Future endpoint:
        /api/players/{player_id}
    */

    return null;
}


/* ============================================================
   SECTION 08 - FUTURE PLAYER EXPLORER JS ROADMAP
   FILE: static/js/player_explorer.js
   PURPOSE: future JavaScript expansion ledger
   ============================================================ */

/*
08.01 Replace demo data with live /api/players endpoint.
08.02 Add loading states.
08.03 Add error states.
08.04 Add player search autocomplete.
08.05 Add team logo rendering.
08.06 Add player image rendering.
08.07 Add Statcast percentile bars.
08.08 Add prediction workbench deep-linking.
08.09 Add local comparison state.
08.10 Add AI scouting summary fetch.
*/