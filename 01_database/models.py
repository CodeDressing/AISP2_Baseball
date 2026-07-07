# ============================================================
# AISP2 BASEBALL
# PHASE 1.00 PART 2
# ENTERPRISE DATABASE MODELS
# FILE: 01_database/models.py
# PURPOSE: core database entities for MLB teams, players,
# rosters, season statistics, and future prediction foundation
# ============================================================


# ============================================================
# SECTION 01 - ENTERPRISE DATABASE IMPORTS
# FILE: 01_database/models.py
# PURPOSE:
# Centralized imports for the AISP2 Enterprise Baseball
# Warehouse.
#
# Every database model in the platform shares these imports.
#
# Supported Systems
# -----------------
# • MLB Teams
# • Players
# • Rosters
# • Games
# • Chat Memory
# • Continuous Learning
# • Prediction Engine
# • NLP
# • AI Chatbot
# • Future ML Pipelines
# • Data Warehouse
# ============================================================

from __future__ import annotations

from datetime import UTC
from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from database import Base


# ============================================================
# SECTION 01.01 - SHARED DATABASE DEFAULTS
# ============================================================

DEFAULT_STRING_LENGTH = 120

SHORT_STRING_LENGTH = 40

LONG_STRING_LENGTH = 255


# ============================================================
# SECTION 01.02 - SHARED TIMESTAMP FACTORY
# ============================================================

def utc_now() -> datetime:
    """
    Enterprise UTC timestamp.

    Every future model should use the same timestamp source.

    This replaces scattered timestamp generation throughout
    the project and keeps warehouse records consistent.
    """

    return datetime.now(UTC)


# ============================================================
# SECTION 01.03 - COMMON INDEX NAMES
# ============================================================

IDX_PLAYER = "idx_player"

IDX_TEAM = "idx_team"

IDX_SEASON = "idx_season"

IDX_GAME = "idx_game"

IDX_CREATED = "idx_created"

IDX_UPDATED = "idx_updated"


# ============================================================
# SECTION 01.04 - DATABASE VERSION
# ============================================================

DATABASE_MODEL_VERSION = "Phase_11_Part_1"

DATABASE_MODEL_DESCRIPTION = (
    "Enterprise Baseball Warehouse "
    "Continuous Learning Schema"
)
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

    This table serves as the central player record used by every
    subsystem throughout AISP2 Baseball.

    Current Consumers
    -----------------
    • Team Rosters
    • Schedule Engine
    • Game Engine
    • Season Statistics
    • Advanced Statistics
    • Prediction Engine
    • AI Chatbot
    • Semantic Search
    • Future Statcast Integration
    • Future Betting Models
    • Future Machine Learning Pipelines
    """

    __tablename__ = "players"

    # --------------------------------------------------------
    # PRIMARY KEY
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # PLAYER IDENTITY
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # POSITION
    # --------------------------------------------------------

    position: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    position_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # --------------------------------------------------------
    # PLAYER ATTRIBUTES
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # BIRTH INFORMATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # TEAM RELATIONSHIP
    # --------------------------------------------------------

    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True,
        index=True,
    )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    team: Mapped[Team | None] = relationship(
        back_populates="players",
    )

    roster_entries: Mapped[list["RosterEntry"]] = relationship(
        back_populates="player",
    )

    season_stats: Mapped[list["PlayerSeasonStat"]] = relationship(
        back_populates="player",
    )

    advanced_batting_stats: Mapped[list["PlayerAdvancedBattingStat"]] = relationship(
        back_populates="player",
    )

    # Reserved for upcoming phases

    game_stats: Mapped[list["PlayerGameStat"]] = relationship(
        back_populates="player",
    )

    pitch_events: Mapped[list["PitchEvent"]] = relationship(
        back_populates="player",
    )

    plate_appearances: Mapped[list["PlateAppearance"]] = relationship(
        back_populates="player",
    )

    statcast_events: Mapped[list["StatcastEvent"]] = relationship(
        back_populates="player",
    )

    prediction_results: Mapped[list["PredictionResult"]] = relationship(
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


# ============================================================
# SECTION 12 - PLAYER ADVANCED BATTING STAT MODEL
# ============================================================

class PlayerAdvancedBattingStat(Base):
    """
    Stores advanced player hitting metrics from Joe's stats CSV.

    This table powers:
        - chatbot player stat lookup
        - home run prediction
        - hit probability
        - strikeout risk
        - walk probability
        - contact quality scoring
        - matchup analysis
        - future ML feature generation
    """

    __tablename__ = "player_advanced_batting_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"),
        nullable=True,
        index=True,
    )

    mlb_player_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    plate_appearances: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    strikeout_percent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
    )

    walk_percent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
    )

    woba: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
    )

    expected_woba: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
    )

    barrel_batted_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
    )

    hard_hit_percent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
    )

    whiff_percent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
    )

    swing_percent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        index=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(120),
        default="joe_stats_csv",
        nullable=True,
        index=True,
    )

    raw_stat_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    updated_at: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    player: Mapped[Player | None] = relationship(
        back_populates="advanced_batting_stats",
    )

# ============================================================
# SECTION 13 - PLAYER PERCENTILE RANKING MODEL
# ============================================================

class PlayerPercentileRanking(Base):
    """
    Stores Statcast percentile rankings by player and season.
    """

    __tablename__ = "player_percentile_rankings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True, index=True)
    mlb_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    xwoba_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    xba_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    xslg_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    barrel_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    hard_hit_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    exit_velocity_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    sprint_speed_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    arm_strength_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    whiff_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    chase_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    walk_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    strikeout_percentile: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    source_file: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    raw_stat_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)


# ============================================================
# SECTION 14 - PLAYER PITCH ARSENAL MODEL
# ============================================================

class PlayerPitchArsenal(Base):
    """
    Stores pitcher pitch-mix, velocity, movement, usage, and result data.
    """

    __tablename__ = "player_pitch_arsenals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True, index=True)
    mlb_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    pitch_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    pitch_name: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    pitch_usage_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    average_velocity: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    max_velocity: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    spin_rate: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    horizontal_movement: Mapped[float | None] = mapped_column(Float, nullable=True)
    vertical_movement: Mapped[float | None] = mapped_column(Float, nullable=True)

    whiff_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    put_away_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    hard_hit_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    source_file: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    raw_stat_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)


# ============================================================
# SECTION 15 - PLAYER PITCH TEMPO MODEL
# ============================================================

class PlayerPitchTempo(Base):
    """
    Stores pitcher pace and pitch-tempo metrics.
    """

    __tablename__ = "player_pitch_tempo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True, index=True)
    mlb_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    pitch_tempo: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    tempo_empty: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    tempo_runners_on: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    pitch_timer_violations: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    source_file: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    raw_stat_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)


# ============================================================
# SECTION 16 - PLAYER BATTED BALL PROFILE MODEL
# ============================================================

class PlayerBattedBallProfile(Base):
    """
    Stores exit velocity, launch angle, hard-hit, barrel, and contact-quality data.
    """

    __tablename__ = "player_batted_ball_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True, index=True)
    mlb_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    average_exit_velocity: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    max_exit_velocity: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    launch_angle: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    barrel_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    hard_hit_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    sweet_spot_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    expected_batting_average: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    expected_slugging: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    expected_woba: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    source_file: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    raw_stat_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)


# ============================================================
# SECTION 17 - PLAYER BATTING STANCE MODEL
# ============================================================

class PlayerBattingStance(Base):
    """
    Stores batting stance, handedness, stance profile, and physical setup data.
    """

    __tablename__ = "player_batting_stances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True, index=True)
    mlb_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    bats: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    stance_side: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    stance_description: Mapped[str | None] = mapped_column(String(180), nullable=True)

    source_file: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    raw_stat_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)


# ============================================================
# SECTION 18 - PLAYER HOME RUN PROFILE MODEL
# ============================================================

class PlayerHomeRunProfile(Base):
    """
    Stores home run profile and power-event data.
    """

    __tablename__ = "player_home_run_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True, index=True)
    mlb_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    home_runs: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    average_home_run_distance: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    max_home_run_distance: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    average_exit_velocity: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    max_exit_velocity: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    average_launch_angle: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    source_file: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    raw_stat_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)


# ============================================================
# SECTION 19 - TEAM PLATE DISCIPLINE MODEL
# ============================================================

class TeamPlateDiscipline(Base):
    """
    Stores team-level plate discipline data.
    """

    __tablename__ = "team_plate_discipline"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    mlb_team_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    team_abbreviation: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    pitches: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    zone_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    zone_swing_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    zone_contact_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    chase_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    chase_contact_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    edge_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    first_pitch_swing_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    swing_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    whiff_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    meatball_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    meatball_swing_percent: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    source_file: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    raw_stat_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)


# ============================================================
# SECTION 20 - RAW DATA IMPORT LOG MODEL
# ============================================================

class RawDataImportLog(Base):
    """
    Tracks every CSV/data import so AISP2 can audit warehouse growth.
    """

    __tablename__ = "raw_data_import_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    source_file: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    source_category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    rows_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(String(80), default="pending", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    completed_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

# ============================================================
# SECTION 21 - PREDICTION AND EVENT ORM MODELS
# FILE: 01_database/models.py
# PURPOSE: define missing mapped classes referenced by Player
# relationships so SQLAlchemy can initialize cleanly.
# ============================================================

class PlayerGameStat(Base):
    """
    Stores player-level game results.

    This table supports future:
        - rolling form
        - player game logs
        - matchup history
        - trend features
        - prediction training labels
    """

    __tablename__ = "player_game_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )

    game_id: Mapped[int | None] = mapped_column(
        ForeignKey("games.id"),
        nullable=True,
        index=True,
    )

    game_pk: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    game_date: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    opponent_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)

    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    opponent_team_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    games_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plate_appearances: Mapped[int | None] = mapped_column(Integer, nullable=True)
    at_bats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hits: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    doubles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_runs: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rbi: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    walks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strikeouts: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    stolen_bases: Mapped[int | None] = mapped_column(Integer, nullable=True)

    innings_pitched: Mapped[float | None] = mapped_column(Float, nullable=True)
    earned_runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pitcher_strikeouts: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    walks_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hits_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raw_game_stat_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    player: Mapped[Player] = relationship(
        back_populates="game_stats",
    )


class PitchEvent(Base):
    """
    Stores pitch-level event data.

    This table supports future pitch modeling, pitch sequencing,
    batter-vs-pitcher analysis, whiff modeling, and deep learning
    sequence features.
    """

    __tablename__ = "pitch_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"),
        nullable=True,
        index=True,
    )

    pitcher_mlb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    batter_mlb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id"), nullable=True, index=True)
    game_pk: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    game_date: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    inning: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inning_half: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    pitch_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    pitch_name: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    pitch_result: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    event_type: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    velocity: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    spin_rate: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    horizontal_break: Mapped[float | None] = mapped_column(Float, nullable=True)
    vertical_break: Mapped[float | None] = mapped_column(Float, nullable=True)

    balls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strikes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outs: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_swing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_whiff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_called_strike: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_in_play: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    raw_pitch_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    player: Mapped[Player | None] = relationship(
        back_populates="pitch_events",
    )


class PlateAppearance(Base):
    """
    Stores plate appearance level outcomes.

    This table bridges pitch-level data and game-level stats.
    """

    __tablename__ = "plate_appearances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"),
        nullable=True,
        index=True,
    )

    batter_mlb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    pitcher_mlb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id"), nullable=True, index=True)
    game_pk: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    game_date: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    inning: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inning_half: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    result: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    event_type: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    pitches_seen: Mapped[int | None] = mapped_column(Integer, nullable=True)
    balls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strikes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outs: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_home_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_walk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_strikeout: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_rbi_event: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    rbi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_bases: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    raw_plate_appearance_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    player: Mapped[Player | None] = relationship(
        back_populates="plate_appearances",
    )


class StatcastEvent(Base):
    """
    Stores Statcast event-level batted-ball and pitch outcome data.

    This table is intended for future ML feature engineering and
    deep learning sequence modeling.
    """

    __tablename__ = "statcast_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"),
        nullable=True,
        index=True,
    )

    batter_mlb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    pitcher_mlb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id"), nullable=True, index=True)
    game_pk: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    game_date: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    event_type: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(String(180), nullable=True)

    launch_speed: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    launch_angle: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    hit_distance: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    barrel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    hard_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    expected_batting_average: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    expected_slugging: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    expected_woba: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    pitch_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    pitch_velocity: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    pitch_spin_rate: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    raw_statcast_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    player: Mapped[Player | None] = relationship(
        back_populates="statcast_events",
    )


class PredictionResult(Base):
    """
    Stores model prediction outputs.

    This table gives AISP2 an auditable record of predictions,
    model versions, input features, confidence, and outcomes.
    """

    __tablename__ = "prediction_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"),
        nullable=True,
        index=True,
    )

    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True,
        index=True,
    )

    game_id: Mapped[int | None] = mapped_column(
        ForeignKey("games.id"),
        nullable=True,
        index=True,
    )

    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    game_pk: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    prediction_scope: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    prediction_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    outcome_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    probability: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    prediction_tier: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    risk_profile: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    feature_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_prediction_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    actual_result: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    was_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)

    created_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    player: Mapped[Player | None] = relationship(
        back_populates="prediction_results",
    )
    # ============================================================
    # SECTION 22 - ORM MAPPING VERIFICATION
    # FILE: 01_database/models.py
    # PURPOSE:
    # Verify SQLAlchemy model registration, relationship mappings,
    # table metadata, critical columns, prediction-readiness models,
    # and ingestion-readiness models without redesigning the schema.
    #
    # This section does not create new tables by itself.
    # It gives AISP2 a safe diagnostic layer so ingestion, chatbot,
    # warehouse, and prediction systems can prove the ORM is valid
    # before attempting database writes.
    # ============================================================

    from typing import Any

    # ============================================================
    # SECTION 22.01 - EXPECTED MODEL REGISTRY
    # ============================================================

    EXPECTED_CORE_MODEL_NAMES = [
        "Team",
        "Player",
        "RosterEntry",
        "Game",
    ]

    EXPECTED_STAT_MODEL_NAMES = [
        "PlayerSeasonStat",
        "PlayerAdvancedBattingStat",
        "PlayerPercentileRanking",
        "PlayerPitchArsenal",
        "PlayerPitchTempo",
        "PlayerBattedBallProfile",
        "PlayerBattingStance",
        "PlayerHomeRunProfile",
        "TeamPlateDiscipline",
        "RawDataImportLog",
    ]

    EXPECTED_MEMORY_MODEL_NAMES = [
        "ChatMemory",
        "LearningSignal",
        "TrainingExample",
        "EntityAlias",
        "UserFeedback",
    ]

    EXPECTED_EVENT_AND_PREDICTION_MODEL_NAMES = [
        "PlayerGameStat",
        "PitchEvent",
        "PlateAppearance",
        "StatcastEvent",
        "PredictionResult",
    ]

    EXPECTED_MODEL_NAMES = (
            EXPECTED_CORE_MODEL_NAMES
            + EXPECTED_STAT_MODEL_NAMES
            + EXPECTED_MEMORY_MODEL_NAMES
            + EXPECTED_EVENT_AND_PREDICTION_MODEL_NAMES
    )

    # ============================================================
    # SECTION 22.02 - EXPECTED TABLE REGISTRY
    # ============================================================

    EXPECTED_CORE_TABLES = [
        "teams",
        "players",
        "roster_entries",
        "games",
    ]

    EXPECTED_STAT_TABLES = [
        "player_season_stats",
        "player_advanced_batting_stats",
        "player_percentile_rankings",
        "player_pitch_arsenals",
        "player_pitch_tempo",
        "player_batted_ball_profiles",
        "player_batting_stances",
        "player_home_run_profiles",
        "team_plate_discipline",
        "raw_data_import_logs",
    ]

    EXPECTED_MEMORY_TABLES = [
        "chat_memory",
        "learning_signals",
        "training_examples",
        "entity_aliases",
        "user_feedback",
    ]

    EXPECTED_EVENT_AND_PREDICTION_TABLES = [
        "player_game_stats",
        "pitch_events",
        "plate_appearances",
        "statcast_events",
        "prediction_results",
    ]

    EXPECTED_TABLES = (
            EXPECTED_CORE_TABLES
            + EXPECTED_STAT_TABLES
            + EXPECTED_MEMORY_TABLES
            + EXPECTED_EVENT_AND_PREDICTION_TABLES
    )

    # ============================================================
    # SECTION 22.03 - CRITICAL MODEL COLUMN REQUIREMENTS
    # ============================================================

    CRITICAL_MODEL_COLUMNS = {
        "Team": [
            "id",
            "mlb_team_id",
            "name",
            "abbreviation",
            "league",
            "division",
            "is_active",
        ],
        "Player": [
            "id",
            "mlb_player_id",
            "full_name",
            "position",
            "current_team_id",
            "active_status",
        ],
        "RosterEntry": [
            "id",
            "season",
            "roster_type",
            "team_id",
            "player_id",
        ],
        "Game": [
            "id",
            "game_pk",
            "season",
            "home_team_id",
            "away_team_id",
            "home_team_name",
            "away_team_name",
        ],
        "PlayerSeasonStat": [
            "id",
            "player_id",
            "season",
            "stat_group",
            "hits",
            "home_runs",
            "strikeouts",
            "batting_average",
            "ops",
        ],
        "PlayerAdvancedBattingStat": [
            "id",
            "player_id",
            "mlb_player_id",
            "season",
            "plate_appearances",
            "strikeout_percent",
            "walk_percent",
            "woba",
            "expected_woba",
            "barrel_batted_rate",
            "hard_hit_percent",
            "whiff_percent",
        ],
        "PlayerPercentileRanking": [
            "id",
            "player_id",
            "mlb_player_id",
            "season",
            "player_name",
            "xwoba_percentile",
            "barrel_percentile",
            "hard_hit_percentile",
            "whiff_percentile",
            "chase_percentile",
        ],
        "PlayerPitchArsenal": [
            "id",
            "player_id",
            "mlb_player_id",
            "season",
            "pitch_type",
            "pitch_name",
            "average_velocity",
            "whiff_percent",
        ],
        "PlayerPitchTempo": [
            "id",
            "player_id",
            "mlb_player_id",
            "season",
            "pitch_tempo",
            "tempo_empty",
            "tempo_runners_on",
        ],
        "PlayerBattedBallProfile": [
            "id",
            "player_id",
            "mlb_player_id",
            "season",
            "average_exit_velocity",
            "max_exit_velocity",
            "launch_angle",
            "barrel_percent",
            "hard_hit_percent",
            "expected_woba",
        ],
        "PlayerBattingStance": [
            "id",
            "player_id",
            "mlb_player_id",
            "season",
            "player_name",
            "bats",
            "stance_side",
        ],
        "PlayerHomeRunProfile": [
            "id",
            "player_id",
            "mlb_player_id",
            "season",
            "player_name",
            "home_runs",
            "average_home_run_distance",
            "average_exit_velocity",
        ],
        "TeamPlateDiscipline": [
            "id",
            "team_id",
            "mlb_team_id",
            "season",
            "team_name",
            "zone_percent",
            "chase_percent",
            "whiff_percent",
        ],
        "RawDataImportLog": [
            "id",
            "source_file",
            "source_category",
            "rows_seen",
            "rows_inserted",
            "rows_updated",
            "rows_skipped",
            "status",
        ],
        "ChatMemory": [
            "id",
            "user_message",
            "assistant_response",
            "detected_intent",
            "detected_task",
            "detected_team",
            "detected_player",
            "detected_outcome",
        ],
        "LearningSignal": [
            "id",
            "chat_memory_id",
            "signal_type",
            "signal_status",
            "intent",
            "task",
            "entity_type",
            "entity_value",
        ],
        "TrainingExample": [
            "id",
            "chat_memory_id",
            "input_text",
            "target_intent",
            "target_task",
            "target_team",
            "target_player",
            "target_outcome",
        ],
        "EntityAlias": [
            "id",
            "entity_type",
            "canonical_value",
            "alias_value",
            "usage_count",
            "is_active",
            "is_trusted",
        ],
        "UserFeedback": [
            "id",
            "chat_memory_id",
            "feedback_type",
            "feedback_value",
        ],
        "PlayerGameStat": [
            "id",
            "player_id",
            "game_id",
            "game_pk",
            "season",
            "game_date",
            "hits",
            "home_runs",
            "rbi",
            "strikeouts",
        ],
        "PitchEvent": [
            "id",
            "player_id",
            "pitcher_mlb_id",
            "batter_mlb_id",
            "game_pk",
            "season",
            "pitch_type",
            "velocity",
            "spin_rate",
            "is_swing",
            "is_whiff",
        ],
        "PlateAppearance": [
            "id",
            "player_id",
            "batter_mlb_id",
            "pitcher_mlb_id",
            "game_pk",
            "season",
            "result",
            "event_type",
            "is_hit",
            "is_home_run",
            "is_walk",
            "is_strikeout",
        ],
        "StatcastEvent": [
            "id",
            "player_id",
            "batter_mlb_id",
            "pitcher_mlb_id",
            "game_pk",
            "season",
            "event_type",
            "launch_speed",
            "launch_angle",
            "expected_woba",
        ],
        "PredictionResult": [
            "id",
            "player_id",
            "team_id",
            "game_id",
            "prediction_scope",
            "prediction_type",
            "outcome_key",
            "probability",
            "confidence",
            "model_name",
            "model_version",
        ],
    }

    # ============================================================
    # SECTION 22.04 - CRITICAL RELATIONSHIP REQUIREMENTS
    # ============================================================

    CRITICAL_MODEL_RELATIONSHIPS = {
        "Team": [
            "players",
            "roster_entries",
            "home_games",
            "away_games",
        ],
        "Player": [
            "team",
            "roster_entries",
            "season_stats",
            "advanced_batting_stats",
            "game_stats",
            "pitch_events",
            "plate_appearances",
            "statcast_events",
            "prediction_results",
        ],
        "RosterEntry": [
            "team",
            "player",
        ],
        "PlayerSeasonStat": [
            "player",
        ],
        "PlayerAdvancedBattingStat": [
            "player",
        ],
        "ChatMemory": [
            "learning_signals",
            "training_examples",
            "feedback_entries",
        ],
        "LearningSignal": [
            "chat_memory",
        ],
        "TrainingExample": [
            "chat_memory",
        ],
        "UserFeedback": [
            "chat_memory",
        ],
        "Game": [
            "home_team",
            "away_team",
        ],
        "PlayerGameStat": [
            "player",
        ],
        "PitchEvent": [
            "player",
        ],
        "PlateAppearance": [
            "player",
        ],
        "StatcastEvent": [
            "player",
        ],
        "PredictionResult": [
            "player",
        ],
    }

    # ============================================================
    # SECTION 22.05 - MODEL REGISTRY HELPERS
    # ============================================================

    def get_model_class_by_name(
            model_name: str,
    ):
        return globals().get(model_name)

    def get_available_model_names() -> list[str]:
        available_model_names = []

        for model_name in EXPECTED_MODEL_NAMES:
            model_class = get_model_class_by_name(model_name)

            if model_class is not None:
                available_model_names.append(model_name)

        return available_model_names

    def get_missing_model_names() -> list[str]:
        return [
            model_name
            for model_name in EXPECTED_MODEL_NAMES
            if get_model_class_by_name(model_name) is None
        ]

    def get_metadata_table_names() -> list[str]:
        return sorted(
            Base.metadata.tables.keys(),
        )

    def get_missing_metadata_tables() -> list[str]:
        metadata_tables = set(
            get_metadata_table_names(),
        )

        return [
            table_name
            for table_name in EXPECTED_TABLES
            if table_name not in metadata_tables
        ]

    def get_present_metadata_tables() -> list[str]:
        metadata_tables = set(
            get_metadata_table_names(),
        )

        return [
            table_name
            for table_name in EXPECTED_TABLES
            if table_name in metadata_tables
        ]

    # ============================================================
    # SECTION 22.06 - MODEL INSPECTION HELPERS
    # ============================================================

    def inspect_model_columns(
            model_name: str,
    ) -> dict[str, Any]:
        model_class = get_model_class_by_name(model_name)

        if model_class is None:
            return {
                "model": model_name,
                "exists": False,
                "columns": [],
                "missing_columns": CRITICAL_MODEL_COLUMNS.get(model_name, []),
                "valid": False,
            }

        try:
            mapper = model_class.__mapper__

            columns = sorted(
                mapper.columns.keys(),
            )

            required_columns = CRITICAL_MODEL_COLUMNS.get(
                model_name,
                [],
            )

            missing_columns = [
                column_name
                for column_name in required_columns
                if column_name not in columns
            ]

            return {
                "model": model_name,
                "exists": True,
                "columns": columns,
                "required_columns": required_columns,
                "missing_columns": missing_columns,
                "valid": len(missing_columns) == 0,
            }

        except Exception as error:
            return {
                "model": model_name,
                "exists": True,
                "columns": [],
                "missing_columns": CRITICAL_MODEL_COLUMNS.get(model_name, []),
                "valid": False,
                "error": str(error),
            }

    def inspect_model_relationships(
            model_name: str,
    ) -> dict[str, Any]:
        model_class = get_model_class_by_name(model_name)

        if model_class is None:
            return {
                "model": model_name,
                "exists": False,
                "relationships": [],
                "missing_relationships": CRITICAL_MODEL_RELATIONSHIPS.get(model_name, []),
                "valid": False,
            }

        try:
            mapper = model_class.__mapper__

            relationships = sorted(
                mapper.relationships.keys(),
            )

            required_relationships = CRITICAL_MODEL_RELATIONSHIPS.get(
                model_name,
                [],
            )

            missing_relationships = [
                relationship_name
                for relationship_name in required_relationships
                if relationship_name not in relationships
            ]

            return {
                "model": model_name,
                "exists": True,
                "relationships": relationships,
                "required_relationships": required_relationships,
                "missing_relationships": missing_relationships,
                "valid": len(missing_relationships) == 0,
            }

        except Exception as error:
            return {
                "model": model_name,
                "exists": True,
                "relationships": [],
                "missing_relationships": CRITICAL_MODEL_RELATIONSHIPS.get(model_name, []),
                "valid": False,
                "error": str(error),
            }

    def inspect_model_table_mapping(
            model_name: str,
    ) -> dict[str, Any]:
        model_class = get_model_class_by_name(model_name)

        if model_class is None:
            return {
                "model": model_name,
                "exists": False,
                "table_name": None,
                "mapped": False,
                "valid": False,
            }

        try:
            table_name = model_class.__tablename__

            mapped = table_name in Base.metadata.tables

            return {
                "model": model_name,
                "exists": True,
                "table_name": table_name,
                "mapped": mapped,
                "valid": mapped,
            }

        except Exception as error:
            return {
                "model": model_name,
                "exists": True,
                "table_name": None,
                "mapped": False,
                "valid": False,
                "error": str(error),
            }

    # ============================================================
    # SECTION 22.07 - ORM CONFIGURATION CHECK
    # ============================================================

    def verify_sqlalchemy_mapper_configuration() -> dict[str, Any]:
        try:
            from sqlalchemy.orm import configure_mappers

            configure_mappers()

            return {
                "configured": True,
                "valid": True,
                "error": None,
            }

        except Exception as error:
            return {
                "configured": False,
                "valid": False,
                "error": str(error),
            }

    # ============================================================
    # SECTION 22.08 - DATABASE PURPOSE READINESS CHECKS
    # ============================================================

    def calculate_orm_readiness_score(
            missing_models: list[str],
            missing_tables: list[str],
            column_reports: dict[str, dict[str, Any]],
            relationship_reports: dict[str, dict[str, Any]],
            mapper_report: dict[str, Any],
    ) -> int:
        score = 100

        if not mapper_report.get("valid"):
            score -= 40

        score -= min(
            len(missing_models) * 5,
            25,
        )

        score -= min(
            len(missing_tables) * 4,
            20,
        )

        for report in column_reports.values():
            if not report.get("valid"):
                score -= 2

        for report in relationship_reports.values():
            if not report.get("valid"):
                score -= 2

        return max(
            0,
            min(score, 100),
        )

    def classify_orm_readiness(
            score: int,
            mapper_valid: bool,
    ) -> str:
        if not mapper_valid:
            return "blocked_mapper_configuration"

        if score >= 95:
            return "enterprise_ready"

        if score >= 85:
            return "ready_with_minor_warnings"

        if score >= 70:
            return "partial_ready"

        if score >= 50:
            return "needs_schema_attention"

        return "not_ready"

    def build_database_system_readiness(
            missing_models: list[str],
            missing_tables: list[str],
            mapper_report: dict[str, Any],
    ) -> dict[str, Any]:
        model_set = set(
            get_available_model_names(),
        )

        table_set = set(
            get_metadata_table_names(),
        )

        core_ready = all(
            model_name in model_set
            for model_name in EXPECTED_CORE_MODEL_NAMES
        ) and all(
            table_name in table_set
            for table_name in EXPECTED_CORE_TABLES
        )

        stats_ready = all(
            model_name in model_set
            for model_name in EXPECTED_STAT_MODEL_NAMES
        ) and all(
            table_name in table_set
            for table_name in EXPECTED_STAT_TABLES
        )

        memory_ready = all(
            model_name in model_set
            for model_name in EXPECTED_MEMORY_MODEL_NAMES
        ) and all(
            table_name in table_set
            for table_name in EXPECTED_MEMORY_TABLES
        )

        event_prediction_ready = all(
            model_name in model_set
            for model_name in EXPECTED_EVENT_AND_PREDICTION_MODEL_NAMES
        ) and all(
            table_name in table_set
            for table_name in EXPECTED_EVENT_AND_PREDICTION_TABLES
        )

        mapper_ready = bool(
            mapper_report.get("valid"),
        )

        ingestion_ready = (
                mapper_ready
                and core_ready
                and stats_ready
        )

        chatbot_ready = (
                mapper_ready
                and core_ready
                and memory_ready
        )

        prediction_ready = (
                mapper_ready
                and core_ready
                and stats_ready
                and event_prediction_ready
        )

        return {
            "mapper_ready": mapper_ready,
            "core_ready": core_ready,
            "stats_ready": stats_ready,
            "memory_ready": memory_ready,
            "event_prediction_ready": event_prediction_ready,
            "ingestion_ready": ingestion_ready,
            "chatbot_ready": chatbot_ready,
            "prediction_ready": prediction_ready,
            "missing_models": missing_models,
            "missing_tables": missing_tables,
        }

    # ============================================================
    # SECTION 22.09 - FULL ORM VERIFICATION REPORT
    # ============================================================

    def verify_orm_mappings() -> dict[str, Any]:
        mapper_report = verify_sqlalchemy_mapper_configuration()

        available_models = get_available_model_names()
        missing_models = get_missing_model_names()

        present_tables = get_present_metadata_tables()
        missing_tables = get_missing_metadata_tables()

        table_mapping_reports = {
            model_name: inspect_model_table_mapping(model_name)
            for model_name in EXPECTED_MODEL_NAMES
        }

        column_reports = {
            model_name: inspect_model_columns(model_name)
            for model_name in EXPECTED_MODEL_NAMES
        }

        relationship_reports = {
            model_name: inspect_model_relationships(model_name)
            for model_name in EXPECTED_MODEL_NAMES
        }

        readiness_score = calculate_orm_readiness_score(
            missing_models=missing_models,
            missing_tables=missing_tables,
            column_reports=column_reports,
            relationship_reports=relationship_reports,
            mapper_report=mapper_report,
        )

        readiness_status = classify_orm_readiness(
            score=readiness_score,
            mapper_valid=mapper_report.get("valid", False),
        )

        system_readiness = build_database_system_readiness(
            missing_models=missing_models,
            missing_tables=missing_tables,
            mapper_report=mapper_report,
        )

        failed_column_models = [
            model_name
            for model_name, report in column_reports.items()
            if not report.get("valid")
        ]

        failed_relationship_models = [
            model_name
            for model_name, report in relationship_reports.items()
            if not report.get("valid")
        ]

        failed_table_mappings = [
            model_name
            for model_name, report in table_mapping_reports.items()
            if not report.get("valid")
        ]

        return {
            "database_model_version": DATABASE_MODEL_VERSION,
            "database_model_description": DATABASE_MODEL_DESCRIPTION,
            "checked_at": utc_now().isoformat(),
            "valid": (
                    mapper_report.get("valid", False)
                    and len(missing_models) == 0
                    and len(missing_tables) == 0
                    and len(failed_column_models) == 0
                    and len(failed_relationship_models) == 0
                    and len(failed_table_mappings) == 0
            ),
            "readiness_score": readiness_score,
            "readiness_status": readiness_status,
            "mapper": mapper_report,
            "expected_model_count": len(EXPECTED_MODEL_NAMES),
            "available_model_count": len(available_models),
            "missing_model_count": len(missing_models),
            "available_models": available_models,
            "missing_models": missing_models,
            "expected_table_count": len(EXPECTED_TABLES),
            "present_table_count": len(present_tables),
            "missing_table_count": len(missing_tables),
            "present_tables": present_tables,
            "missing_tables": missing_tables,
            "failed_column_models": failed_column_models,
            "failed_relationship_models": failed_relationship_models,
            "failed_table_mappings": failed_table_mappings,
            "table_mapping_reports": table_mapping_reports,
            "column_reports": column_reports,
            "relationship_reports": relationship_reports,
            "system_readiness": system_readiness,
            "next_required_action": (
                "ORM mappings are valid. Run database initialization and then ingestion."
                if mapper_report.get("valid") and len(missing_models) == 0
                else "Fix missing models, missing tables, or mapper configuration errors before ingestion."
            ),
        }

    # ============================================================
    # SECTION 22.10 - HUMAN-READABLE VERIFICATION SUMMARY
    # ============================================================

    def build_orm_verification_summary(
            report: dict[str, Any] | None = None,
    ) -> str:
        report = report or verify_orm_mappings()

        summary_lines = [
            "AISP2 ORM Mapping Verification",
            "=" * 42,
            f"Valid: {report.get('valid')}",
            f"Readiness Score: {report.get('readiness_score')}",
            f"Readiness Status: {report.get('readiness_status')}",
            f"Mapper Configured: {report.get('mapper', {}).get('configured')}",
            f"Expected Models: {report.get('expected_model_count')}",
            f"Available Models: {report.get('available_model_count')}",
            f"Missing Models: {report.get('missing_model_count')}",
            f"Expected Tables: {report.get('expected_table_count')}",
            f"Present Tables: {report.get('present_table_count')}",
            f"Missing Tables: {report.get('missing_table_count')}",
            "",
            "System Readiness",
            "-" * 42,
            f"Core Ready: {report.get('system_readiness', {}).get('core_ready')}",
            f"Stats Ready: {report.get('system_readiness', {}).get('stats_ready')}",
            f"Memory Ready: {report.get('system_readiness', {}).get('memory_ready')}",
            f"Event/Prediction Ready: {report.get('system_readiness', {}).get('event_prediction_ready')}",
            f"Ingestion Ready: {report.get('system_readiness', {}).get('ingestion_ready')}",
            f"Chatbot Ready: {report.get('system_readiness', {}).get('chatbot_ready')}",
            f"Prediction Ready: {report.get('system_readiness', {}).get('prediction_ready')}",
        ]

        if report.get("missing_models"):
            summary_lines.append("")
            summary_lines.append("Missing Models")
            summary_lines.append("-" * 42)

            for model_name in report["missing_models"]:
                summary_lines.append(f"- {model_name}")

        if report.get("missing_tables"):
            summary_lines.append("")
            summary_lines.append("Missing Tables")
            summary_lines.append("-" * 42)

            for table_name in report["missing_tables"]:
                summary_lines.append(f"- {table_name}")

        if report.get("mapper", {}).get("error"):
            summary_lines.append("")
            summary_lines.append("Mapper Error")
            summary_lines.append("-" * 42)
            summary_lines.append(str(report["mapper"]["error"]))

        summary_lines.append("")
        summary_lines.append("Next Required Action")
        summary_lines.append("-" * 42)
        summary_lines.append(str(report.get("next_required_action")))

        return "\n".join(summary_lines)

    def print_orm_verification_report() -> dict[str, Any]:
        report = verify_orm_mappings()

        print(
            build_orm_verification_summary(
                report,
            )
        )

        return report