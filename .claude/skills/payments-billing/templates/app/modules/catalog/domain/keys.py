"""Entitlement keys — the vocabulary between catalog (what is sold) and features (what is unlocked)."""

from enum import StrEnum


class Key(StrEnum):
    RESUME_PDF_EXPORT = "resume.pdf_export"
    RESUME_EXPERT_REVIEW = "resume.expert_review"
    INTERVIEW_MOCK_SESSION = "interview.mock_session"
    VISA_CONSULTATION = "visa.consultation"
    LEARN_PREMIUM = "learn.premium"
