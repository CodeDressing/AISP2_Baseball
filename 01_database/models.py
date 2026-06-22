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
# SECTION 06 - FUTURE MODEL ROADMAP
# ============================================================

"""
Future Database Models

Phase 1.01:
    Game

Phase 1.02:
    TeamSeasonStat

Phase 1.03:
    StatcastEvent

Phase 1.04:
    PlayerGameLog

Phase 1.05:
    PitcherGameLog

Phase 1.06:
    PlayerPrediction

Phase 1.07:
    GamePrediction

Phase 1.08:
    FeatureSnapshot

Phase 1.09:
    ModelRun

Phase 1.10:
    SimulationRun

Long-Term Warehouse Targets

- MLB teams
- MLB rosters
- MLB players
- Player season stats
- Team season stats
- Game schedules
- Game results
- Box scores
- Line scores
- Statcast pitch events
- Batter-vs-pitcher history
- Ballpark factors
- Weather context
- Injury context
- Transaction history
- Prediction outputs
- Simulation outputs
"""