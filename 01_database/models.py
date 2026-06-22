"""
AISP2 Baseball
Section 01: Database Models

Purpose:
This file defines the first database tables for AISP2.

Current tables:
1. Team
2. Player

Rule:
Only database table structures belong here.
No API calls.
No predictions.
No data loading.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
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
    )

    abbreviation: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    league: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    division: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    venue: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    players: Mapped[list["Player"]] = relationship(
        back_populates="team",
    )


# ============================================================
# SECTION 02 - PLAYER MODEL
# ============================================================

class Player(Base):
    """
    Stores one MLB player.
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

    position: Mapped[str | None] = mapped_column(
        String(50),
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

    birth_country: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True,
    )

    team: Mapped[Team | None] = relationship(
        back_populates="players",
    )