# ============================================================
# AISP2 BASEBALL
# PHASE 1.01 PART 1
# ENTERPRISE DATABASE MODELS
# FILE: 01_database/models.py
# PURPOSE: core database entities for MLB teams, players,
# rosters, season statistics, MLB schedule games, and future
# prediction foundation
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
    """

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    mlb_team_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    abbreviation: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    team_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    franchise_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    club_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    league: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    division: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    venue: Mapped[str | None] = mapped_column(String(120), nullable=True)

    first_year_of_play: Mapped[str | None] = mapped_column(String(10), nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    players: Mapped[list["Player"]] = relationship(back_populates="team")
    roster_entries: Mapped[list["RosterEntry"]] = relationship(back_populates="team")

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
    """

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    mlb_player_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    primary_number: Mapped[str | None] = mapped_column(String(10), nullable=True)

    position: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    position_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    bats: Mapped[str | None] = mapped_column(String(10), nullable=True)
    throws: Mapped[str | None] = mapped_column(String(10), nullable=True)
    height: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)

    birth_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    birth_city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    birth_state_province: Mapped[str | None] = mapped_column(String(80), nullable=True)
    birth_country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mlb_debut_date: Mapped[str | None] = mapped_column(String(30), nullable=True)

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

    team: Mapped[Team | None] = relationship(back_populates="players")
    roster_entries: Mapped[list["RosterEntry"]] = relationship(back_populates="player")
    season_stats: Mapped[list["PlayerSeasonStat"]] = relationship(back_populates="player")


# ============================================================
# SECTION 04 - ROSTER ENTRY MODEL
# ============================================================

class RosterEntry(Base):
    """
    Stores one player-team-season roster relationship.
    """

    __tablename__ = "roster_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    roster_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    jersey_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status_description: Mapped[str | None] = mapped_column(String(120), nullable=True)

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

    team: Mapped[Team] = relationship(back_populates="roster_entries")
    player: Mapped[Player] = relationship(back_populates="roster_entries")


# ============================================================
# SECTION 05 - PLAYER SEASON STAT MODEL
# ============================================================

class PlayerSeasonStat(Base):
    """
    Stores season-level player statistics.
    """

    __tablename__ = "player_season_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    stat_group: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    games_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plate_appearances: Mapped[int | None] = mapped_column(Integer, nullable=True)
    at_bats: Mapped[int | None] = mapped_column(Integer, nullable=True)

    hits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doubles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rbi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    walks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strikeouts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stolen_bases: Mapped[int | None] = mapped_column(Integer, nullable=True)

    batting_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_base_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    slugging_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    ops: Mapped[float | None] = mapped_column(Float, nullable=True)

    wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    era: Mapped[float | None] = mapped_column(Float, nullable=True)
    whip: Mapped[float | None] = mapped_column(Float, nullable=True)
    saves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    innings_pitched: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_stat_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    player: Mapped[Player] = relationship(back_populates="season_stats")


# ============================================================
# SECTION 06 - GAME MODEL
# ============================================================

class Game(Base):
    """
    Stores one MLB scheduled game.

    This table turns the MLB schedule endpoint into a permanent
    database layer.

    It supports:
        - schedule display
        - matchup analysis
        - game result tracking
        - probable pitcher tracking
        - completed game stat ingestion
        - prediction model feature generation
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

    game_date: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    official_date: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

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
        back_populates="home_games",
    )

    away_team: Mapped[Team | None] = relationship(
        foreign_keys=[away_team_id],
        back_populates="away_games",
    )


# ============================================================
# SECTION 07 - FUTURE MODEL ROADMAP
# ============================================================

"""
Immediate Next Steps

Phase 1.01 Part 2:
    Create/upgrade init_db.py so Base.metadata.create_all(engine)
    creates the new games table.

Phase 3.04 Part 1:
    Create 03_ingestion/schedule_ingestion.py.

Phase 3.04 Part 2:
    Pull MLB schedule data using:
        MLBStatsAPIClient.get_schedule_games()

Phase 3.04 Part 3:
    Normalize schedule payloads into Game records.

Phase 3.04 Part 4:
    Upsert games by game_pk.

Phase 3.05:
    Use game_pk to load:
        /game/{gamePk}/feed/live
        /game/{gamePk}/boxscore

Future Database Models

- GameFeedSnapshot
- GameBoxScore
- PlayerGameStat
- TeamGameStat
- PitchEvent
- PlateAppearance
- ProbablePitcherSnapshot
- LineupSnapshot
- WeatherSnapshot
- BettingMarketSnapshot
- PredictionResult
"""