"""
AISP2 Baseball
Section 01: Database Models

Purpose:
This file defines the first database tables for AISP2.

Current tables:
1. Team
2. Player
3. PlayerSeasonStat

Rule:
Only database table structures belong here.
No API calls.
No predictions.
No data loading.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ============================================================
# SECTION 01 - TEAM MODEL
# ============================================================

class Team(Base):
    """
    Stores one MLB team.
    """

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    mlb_team_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)

    abbreviation: Mapped[str | None] = mapped_column(String(10), nullable=True)

    league: Mapped[str | None] = mapped_column(String(80), nullable=True)

    division: Mapped[str | None] = mapped_column(String(80), nullable=True)

    venue: Mapped[str | None] = mapped_column(String(120), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    players: Mapped[list["Player"]] = relationship(back_populates="team")


# ============================================================
# SECTION 02 - PLAYER MODEL
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

    position: Mapped[str | None] = mapped_column(String(50), nullable=True)

    bats: Mapped[str | None] = mapped_column(String(10), nullable=True)

    throws: Mapped[str | None] = mapped_column(String(10), nullable=True)

    height: Mapped[str | None] = mapped_column(String(20), nullable=True)

    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)

    birth_country: Mapped[str | None] = mapped_column(String(80), nullable=True)

    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True,
    )

    team: Mapped[Team | None] = relationship(back_populates="players")

    season_stats: Mapped[list["PlayerSeasonStat"]] = relationship(
        back_populates="player",
    )


# ============================================================
# SECTION 03 - PLAYER SEASON STAT MODEL
# ============================================================

class PlayerSeasonStat(Base):
    """
    Stores one player's season-level batting or pitching statistics.

    This table will let AISP2 begin answering questions like:
    - What is this player's hit probability?
    - What is this player's home run profile?
    - What is this player's strikeout tendency?
    """

    __tablename__ = "player_season_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )

    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    stat_group: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    games_played: Mapped[int | None] = mapped_column(Integer, nullable=True)

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

    player: Mapped[Player] = relationship(back_populates="season_stats")