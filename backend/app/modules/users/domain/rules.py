"""Pure rules for the users domain."""

DELETION_GRACE_DAYS = 30  # after a deletion request, personal data is anonymized once this many days passed
DEFAULT_TIMEZONE = "Asia/Tashkent"
DISPLAY_NAME_MAX = 100
ANONYMIZED_DISPLAY_NAME = "deleted"  # clients show a translated "Deleted user"
ANONYMIZE_BATCH = 100
