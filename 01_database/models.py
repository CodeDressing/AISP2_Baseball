# ============================================================
# AISP2 BASEBALL
# PHASE 1.00 PART 2
# ENTERPRISE DATABASE MODELS
# FILE: 01_database/models.py
# PURPOSE: core database entities for MLB teams, players,
# rosters, season statistics, and future prediction foundation
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

from sqlalchemy import Boolean
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from database import Base


# ============================================================
# SECTION 02 - TEAM MODEL
# ============================================================

class Team(Base):
    """
    Stores one MLB franchise/team.

    This table is the foundation for:
        - roster ownership
        - player-team relationships
        - home/away game relationships
        - team statistics
        - matchup analysis
        - future win probability models
    """

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    mlb_team_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    abbreviation: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )

    team_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    file_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    franchise_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    club_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    short_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    location_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    league: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )

    division: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )

    venue: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    first_year_of_play: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    players: Mapped[list["Player"]] = relationship(
        back_populates="team",
    )

    roster_entries: Mapped[list["RosterEntry"]] = relationship(
        back_populates="team",
    )

    home_games: Mapped[list["Game"]] = relationship(
        foreign_keys="Game.home_team_id",
        back_populates="home_team",
    )

    away_games: Mapped[list["Game"]] = relationship(
        foreign_keys="Game.away_team_id",
        back_populates="away_team",
    )
# ============================================================
# SECTION 03 - PLAYER MODEL
# ============================================================

class Player(Base):
    """
    Stores one MLB player.

    This table is the foundation for:
        - player search
        - roster membership
        - player statistics
        - player outcome prediction
        - future Statcast profile linking
    """

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    mlb_player_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    primary_number: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    position: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    position_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    bats: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    throws: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    height: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    weight: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    birth_date: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    birth_city: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    birth_state_province: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    birth_country: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    mlb_debut_date: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    active_status: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True,
        index=True,
    )

    team: Mapped[Team | None] = relationship(
        back_populates="players",
    )

    roster_entries: Mapped[list["RosterEntry"]] = relationship(
        back_populates="player",
    )

    season_stats: Mapped[list["PlayerSeasonStat"]] = relationship(
        back_populates="player",
    )


# ============================================================
# SECTION 04 - ROSTER ENTRY MODEL
# ============================================================

class RosterEntry(Base):
    """
    Stores one player-team-season roster relationship.

    This table allows AISP2 to track:
        - active rosters
        - 40-man rosters
        - historical roster membership
        - player-team-season context
    """

    __tablename__ = "roster_entries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    roster_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    jersey_number: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    status_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    status_description: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        nullable=False,
        index=True,
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )

    team: Mapped[Team] = relationship(
        back_populates="roster_entries",
    )

    player: Mapped[Player] = relationship(
        back_populates="roster_entries",
    )


# ============================================================
# SECTION 05 - PLAYER SEASON STAT MODEL
# ============================================================

class PlayerSeasonStat(Base):
    """
    Stores season-level player statistics.

    This table is the first prediction-ready statistical table.

    It supports future probabilities for:
        - gets a hit
        - hits a home run
        - walks
        - strikes out
        - records RBI
        - steals a base
        - pitching outcomes
    """

    __tablename__ = "player_season_stats"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )

    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    stat_group: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    games_played: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    plate_appearances: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    at_bats: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    hits: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    doubles: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    triples: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    home_runs: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    runs: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    rbi: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    walks: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    strikeouts: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    stolen_bases: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    batting_average: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    on_base_percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    slugging_percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    ops: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    wins: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    losses: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    era: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    whip: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    saves: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    innings_pitched: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    raw_stat_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    player: Mapped[Player] = relationship(
        back_populates="season_stats",
    )


# ============================================================
# SECTION 06 - CHAT MEMORY MODEL
# ============================================================

class ChatMemory(Base):
    """
    Stores every user question and assistant response.
    """

    __tablename__ = "chat_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    conversation_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    detected_intent: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    detected_task: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    detected_team: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    detected_player: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    detected_outcome: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    nlu_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    importance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raw_context_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_nlu_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_semantic_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    learning_signals: Mapped[list["LearningSignal"]] = relationship(
        back_populates="chat_memory",
    )

    training_examples: Mapped[list["TrainingExample"]] = relationship(
        back_populates="chat_memory",
    )

    feedback_entries: Mapped[list["UserFeedback"]] = relationship(
        back_populates="chat_memory",
    )


# ============================================================
# SECTION 07 - LEARNING SIGNAL MODEL
# ============================================================

class LearningSignal(Base):
    """
    Stores structured learning signals extracted from chatbot interactions.
    """

    __tablename__ = "learning_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    chat_memory_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_memory.id"),
        nullable=True,
        index=True,
    )

    signal_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    signal_status: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    intent: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    task: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    entity_value: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    outcome: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_needed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_signal_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    chat_memory: Mapped[ChatMemory | None] = relationship(
        back_populates="learning_signals",
    )


# ============================================================
# SECTION 08 - TRAINING EXAMPLE MODEL
# ============================================================

class TrainingExample(Base):
    """
    Stores supervised NLP training examples generated from real user questions.
    """

    __tablename__ = "training_examples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    chat_memory_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_memory.id"),
        nullable=True,
        index=True,
    )

    input_text: Mapped[str] = mapped_column(Text, nullable=False)

    target_intent: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    target_task: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    target_team: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    target_player: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    target_outcome: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    correction_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_needed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    approved_for_training: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    chat_memory: Mapped[ChatMemory | None] = relationship(
        back_populates="training_examples",
    )


# ============================================================
# SECTION 09 - ENTITY ALIAS MODEL
# ============================================================

class EntityAlias(Base):
    """
    Stores aliases, misspellings, nicknames, abbreviations, and learned phrases.
    """

    __tablename__ = "entity_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    canonical_value: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    alias_value: Mapped[str] = mapped_column(String(160), nullable=False, index=True)

    source: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    usage_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    confirmation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    review_needed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    last_seen_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)


# ============================================================
# SECTION 10 - USER FEEDBACK MODEL
# ============================================================

class UserFeedback(Base):
    """
    Stores user feedback about chatbot answers.
    """

    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    chat_memory_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_memory.id"),
        nullable=True,
        index=True,
    )

    feedback_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    feedback_value: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    feedback_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    chat_memory: Mapped[ChatMemory | None] = relationship(
        back_populates="feedback_entries",
    )


# ============================================================
# SECTION 11 - GAME MODEL
# ============================================================

class Game(Base):
    """
    Stores one MLB scheduled game.

    This table powers:
        - schedule lookup
        - game-specific chatbot questions
        - team matchup prediction
        - player-in-game prediction
        - gamePk-based boxscore/feed ingestion
    """

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    game_pk: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    game_date: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    official_date: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    game_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    series_description: Mapped[str | None] = mapped_column(String(120), nullable=True)

    status_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    status_description: Mapped[str | None] = mapped_column(String(120), nullable=True)
    abstract_game_state: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    coded_game_state: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    detailed_state: Mapped[str | None] = mapped_column(String(120), nullable=True)

    venue_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)

    home_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True,
        index=True,
    )

    away_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True,
        index=True,
    )

    home_mlb_team_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    away_mlb_team_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    home_team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    away_team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    home_probable_pitcher_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    away_probable_pitcher_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    home_probable_pitcher_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    away_probable_pitcher_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    double_header: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    game_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    day_night: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    scheduled_innings: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_postponed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    raw_schedule_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    home_team: Mapped[Team | None] = relationship(
        foreign_keys=[home_team_id],
    )

    away_team: Mapped[Team | None] = relationship(
        foreign_keys=[away_team_id],
    )