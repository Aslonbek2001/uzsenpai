"""Residence statuses and urgency levels (stable codes; the UI translates them)."""

from enum import StrEnum


class ResidenceStatus(StrEnum):
    TOKUTEI_GINO_1 = "tokutei_gino_1"
    TOKUTEI_GINO_2 = "tokutei_gino_2"
    GIJINKOKU = "gijinkoku"
    STUDENT = "student"
    DEPENDENT = "dependent"


class Urgency(StrEnum):
    OK = "ok"
    SOON = "soon"  # < 90 days
    URGENT = "urgent"  # < 30 days
    EXPIRED = "expired"
