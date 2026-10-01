"""bot/app/services/errors.py — backend error codes → translated text (static msgids, so pybabel extracts them)."""
from aiogram.utils.i18n import lazy_gettext as __

from app.services.api_client import BackendError

# Keys are backend error codes; values are English msgids translated in locales/{uz,ru,en,ja}.
ERRORS = {
    "common.unknown": __("Something went wrong. Please try again."),
    "common.unavailable": __("Service is temporarily unavailable. Please try again in a minute."),
    "common.unauthorized": __("Please start the bot again with /start."),
    "common.rate_limited": __("Too many requests. Please wait a moment."),
    "billing.no_entitlement": __("This feature is part of a paid service. Open /services to see options."),
    "visa.expiry_in_past": __("The expiry date is in the past. Please check the date."),
}


def error_text(err: BackendError) -> str:
    return str(ERRORS.get(err.code, ERRORS["common.unknown"]))
