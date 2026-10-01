"""Stable codes stored in the database; clients translate them (uz/ru/en/ja)."""

from enum import StrEnum


class UserRole(StrEnum):
    """Platform role. v1: user + admin. Later `staff` (resume reviewers); partner organizations get their own
    membership roles in a `partners` module — they don't change this enum."""

    USER = "user"
    ADMIN = "admin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DELETION_REQUESTED = "deletion_requested"  # can be restored within DELETION_GRACE_DAYS
    DELETED = "deleted"  # personal data anonymized; row kept so payments/orders stay consistent


class JlptLevel(StrEnum):
    NONE = "none"
    N5 = "n5"
    N4 = "n4"
    N3 = "n3"
    N2 = "n2"
    N1 = "n1"


class UserGoal(StrEnum):
    """Main reason the user is here — drives the personal next steps shown on the home screen."""

    WORK = "work"  # find a job in Japan
    STUDY = "study"  # university / language school in Japan
    LIVING = "living"  # already in Japan: visa, documents, daily life
    LEARN_JAPANESE = "learn_japanese"
