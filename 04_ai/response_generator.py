# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/response_generator.py
# PURPOSE: generate clean chatbot responses from structured
# baseball context, demo teams, player profiles, probability
# outputs, and future real model results
# ============================================================


# ============================================================
# SECTION 01 - RESPONSE CONSTANTS
# FILE: 04_ai/response_generator.py
# PURPOSE: response labels and fallback messages
# ============================================================

DEFAULT_RESPONSE_MODE = "demo"

DEMO_DISCLAIMER = (
    "This is a demo baseball intelligence response, not betting advice."
)


# ============================================================
# SECTION 02 - SAFE TEXT HELPERS
# FILE: 04_ai/response_generator.py
# PURPOSE: format text safely and consistently
# ============================================================

def format_bullet_list(items: list[str]) -> str:
    if not items:
        return "- No items available yet."

    return "\n".join(
        f"- {item}"
        for item in items
    )


def get_demo_team_players(
    team_name: str,
    demo_teams: dict,
) -> list[str]:
    team = demo_teams.get(team_name)

    if not team:
        return []

    return team.get("players", [])


# ============================================================
# SECTION 03 - TEAM RESPONSES
# FILE: 04_ai/response_generator.py
# PURPOSE: build team, roster, and team-list responses
# ============================================================

def generate_team_list_response(demo_teams: dict) -> str:
    team_lines = [
        f"{team_name} ({team_data.get('abbreviation', 'N/A')})"
        for team_name, team_data in demo_teams.items()
    ]

    return (
        f"I currently have {len(demo_teams)} demo MLB teams loaded:\n\n"
        f"{format_bullet_list(team_lines)}\n\n"
        "The live MLB endpoint can also support all active MLB teams."
    )


def generate_team_response(
    team_name: str,
    demo_teams: dict,
) -> str:
    team_data = demo_teams.get(team_name)

    if not team_data:
        return generate_team_list_response(
            demo_teams,
        )

    players = team_data.get("players", [])

    return (
        f"{team_name}\n\n"
        f"League: {team_data.get('league')}\n"
        f"Division: {team_data.get('division')}\n"
        f"Ballpark: {team_data.get('ballpark')}\n\n"
        "Demo roster:\n"
        f"{format_bullet_list(players)}"
    )


def generate_roster_response(
    team_name: str,
    demo_teams: dict,
) -> str:
    team_data = demo_teams.get(team_name)

    if not team_data:
        return (
            "I could not find that team in the demo roster data yet. "
            "Try asking for the Yankees, Dodgers, Mets, Braves, Phillies, Cubs, or another loaded team."
        )

    players = team_data.get("players", [])

    return (
        f"{team_name} demo roster:\n\n"
        f"{format_bullet_list(players)}"
    )


# ============================================================
# SECTION 04 - PLAYER RESPONSES
# FILE: 04_ai/response_generator.py
# PURPOSE: build player profile and player-list responses
# ============================================================

def generate_player_list_response(player_profiles: dict) -> str:
    player_names = sorted(
        player_profiles.keys(),
    )

    return (
        f"I currently have {len(player_names)} demo player profiles loaded:\n\n"
        f"{format_bullet_list(player_names[:80])}"
    )


def generate_player_response(
    player_name: str,
    player_profiles: dict,
) -> str:
    profile = player_profiles.get(player_name)

    if not profile:
        return (
            "I could not find that player in the demo profile database yet. "
            "Try asking about Aaron Judge, Shohei Ohtani, Juan Soto, Bryce Harper, "
            "Mookie Betts, or another loaded demo player."
        )

    return (
        f"{player_name}\n\n"
        f"Style: {profile.get('style')}\n"
        f"Recent Form: {profile.get('recent_form')}\n"
        f"Primary Metric: {profile.get('primary_metric')}\n"
        f"Base Demo Probability: {profile.get('base_probability')}%\n"
        f"Confidence: {profile.get('confidence')}%"
    )


# ============================================================
# SECTION 05 - PROBABILITY RESPONSES
# FILE: 04_ai/response_generator.py
# PURPOSE: build probability and best-team probability responses
# ============================================================

def generate_player_probability_response(
    player_name: str,
    outcome_key: str | None,
    demo_outcomes: dict,
    build_probability_function,
) -> str:
    selected_outcome = outcome_key or "home_run"

    if selected_outcome not in demo_outcomes:
        selected_outcome = "home_run"

    prediction = build_probability_function(
        player_name=player_name,
        outcome_key=selected_outcome,
    )

    profile = prediction["profile"]

    return (
        f"{player_name}\n"
        f"Outcome: {demo_outcomes[selected_outcome]}\n\n"
        f"Estimated Demo Probability: {prediction['probability']}%\n"
        f"Confidence: {prediction['confidence']}%\n\n"
        "Reasoning:\n"
        f"- Style: {profile.get('style')}\n"
        f"- Recent Form: {profile.get('recent_form')}\n"
        f"- Primary Metric: {profile.get('primary_metric')}\n\n"
        f"{DEMO_DISCLAIMER}"
    )


def generate_best_team_probability_response(
    team_name: str,
    outcome_key: str | None,
    demo_teams: dict,
    demo_outcomes: dict,
    build_probability_function,
) -> str:
    players = get_demo_team_players(
        team_name,
        demo_teams,
    )

    if not players:
        return (
            f"I found {team_name}, but I do not have demo players loaded for that team yet. "
            "The next upgrade will connect live roster lookup for this exact request."
        )

    selected_outcome = outcome_key or "home_run"

    if selected_outcome not in demo_outcomes:
        selected_outcome = "home_run"

    scored_players = []

    for player_name in players:
        prediction = build_probability_function(
            player_name=player_name,
            outcome_key=selected_outcome,
        )

        scored_players.append(
            {
                "player": player_name,
                "probability": prediction["probability"],
                "confidence": prediction["confidence"],
                "profile": prediction["profile"],
            }
        )

    scored_players.sort(
        key=lambda item: item["probability"],
        reverse=True,
    )

    top_player = scored_players[0]

    ranked_lines = [
        f"{item['player']}: {item['probability']}% probability, {item['confidence']}% confidence"
        for item in scored_players
    ]

    return (
        f"Highest demo probability on the {team_name}\n\n"
        f"Outcome: {demo_outcomes[selected_outcome]}\n\n"
        f"Top Candidate: {top_player['player']}\n"
        f"Estimated Demo Probability: {top_player['probability']}%\n"
        f"Confidence: {top_player['confidence']}%\n\n"
        "Team ranking:\n"
        f"{format_bullet_list(ranked_lines)}\n\n"
        f"{DEMO_DISCLAIMER}"
    )


# ============================================================
# SECTION 06 - COMPARISON RESPONSES
# FILE: 04_ai/response_generator.py
# PURPOSE: build player and team comparison responses
# ============================================================

def generate_player_comparison_response(
    players: list[str],
    build_probability_function,
) -> str:
    selected_players = players[:2]

    if len(selected_players) < 2:
        return "Give me two players to compare, such as Judge vs Ohtani."

    comparison_lines = []

    for player_name in selected_players:
        prediction = build_probability_function(
            player_name=player_name,
            outcome_key="home_run",
        )

        comparison_lines.append(
            f"{player_name}: {prediction['probability']}% HR demo probability, "
            f"{prediction['confidence']}% confidence"
        )

    return (
        "Player Comparison\n\n"
        f"{format_bullet_list(comparison_lines)}\n\n"
        "This comparison is currently based on demo profile data."
    )


def generate_team_comparison_response(
    teams: list[str],
    demo_teams: dict,
) -> str:
    selected_teams = teams[:2]

    if len(selected_teams) < 2:
        return "Give me two teams to compare, such as Yankees vs Dodgers."

    response_blocks = []

    for team_name in selected_teams:
        team_data = demo_teams.get(team_name, {})

        response_blocks.append(
            f"{team_name}: {team_data.get('league', 'Unknown league')}, "
            f"{team_data.get('division', 'Unknown division')}, "
            f"Ballpark: {team_data.get('ballpark', 'Unknown')}"
        )

    return (
        "Team Comparison\n\n"
        f"{format_bullet_list(response_blocks)}\n\n"
        "Future versions will compare offense, pitching, bullpen, park factor, rest, and recent form."
    )


# ============================================================
# SECTION 07 - HELP AND FALLBACK RESPONSES
# FILE: 04_ai/response_generator.py
# PURPOSE: generate help and fallback chatbot messages
# ============================================================

def generate_help_response() -> str:
    return (
        "You can ask me questions like:\n\n"
        "- What teams do you have?\n"
        "- Show me Yankees players.\n"
        "- Tell me about Aaron Judge.\n"
        "- What is Bryce Harper's home run probability?\n"
        "- Can Juan Soto get a hit?\n"
        "- Compare Judge and Ohtani.\n"
        "- Who has the highest probability on the Chicago White Sox?\n\n"
        "I understand teams, players, rosters, outcomes, comparisons, and demo probabilities."
    )


def generate_general_fallback_response() -> str:
    return (
        "I understand this as a baseball question, but I need a little more structure. "
        "Try asking about a specific team, player, roster, comparison, or outcome probability."
    )


# ============================================================
# SECTION 08 - RESPONSE ROUTER
# FILE: 04_ai/response_generator.py
# PURPOSE: generate final chatbot response from structured context
# ============================================================

def generate_response_from_context(
    context: dict,
    demo_teams: dict,
    player_profiles: dict,
    demo_outcomes: dict,
    build_probability_function,
) -> str:
    task = context.get("task")
    team = context.get("team")
    player = context.get("player")
    outcome = context.get("outcome")
    teams = context.get("teams", [])
    players = context.get("players", [])

    if task == "help":
        return generate_help_response()

    if task == "team_lookup" and team:
        return generate_team_response(
            team,
            demo_teams,
        )

    if task == "roster_lookup" and team:
        return generate_roster_response(
            team,
            demo_teams,
        )

    if task == "player_lookup" and player:
        return generate_player_response(
            player,
            player_profiles,
        )

    if task == "player_probability" and player:
        return generate_player_probability_response(
            player_name=player,
            outcome_key=outcome,
            demo_outcomes=demo_outcomes,
            build_probability_function=build_probability_function,
        )

    if task == "best_team_probability" and team:
        return generate_best_team_probability_response(
            team_name=team,
            outcome_key=outcome,
            demo_teams=demo_teams,
            demo_outcomes=demo_outcomes,
            build_probability_function=build_probability_function,
        )

    if task == "player_comparison":
        return generate_player_comparison_response(
            players,
            build_probability_function,
        )

    if task == "team_comparison":
        return generate_team_comparison_response(
            teams,
            demo_teams,
        )

    if task == "team_list":
        return generate_team_list_response(
            demo_teams,
        )

    if task == "player_list":
        return generate_player_list_response(
            player_profiles,
        )

    return generate_general_fallback_response()


# ============================================================
# SECTION 09 - FUTURE RESPONSE GENERATOR ROADMAP
# FILE: 04_ai/response_generator.py
# PURPOSE: future response personalization, richer model
# explanations, charts, cards, and RAG-backed responses
# ============================================================

"""
09.01 Add rich response cards.
09.02 Add probability explanation templates by outcome.
09.03 Add confidence explanation templates.
09.04 Add model factor breakdowns.
09.05 Add live roster fallback for teams without demo players.
09.06 Add top 3 / top 5 player rankings.
09.07 Add short vs detailed response modes.
09.08 Add RAG-backed knowledge citations.
09.09 Add feedback-aware response refinement.
09.10 Add conversation memory summaries.
"""