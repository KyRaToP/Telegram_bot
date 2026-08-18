import logging
import os

logger = logging.getLogger(__name__)


def allowed_user_ids() -> set[int]:
    raw = os.getenv("ALLOWED_TELEGRAM_IDS", "")
    return {
        int(item.strip())
        for item in raw.split(",")
        if item.strip().isdigit()
    }


def is_allowed(user_id: int) -> bool:
    """Empty allowlist means nobody (fail-closed), same idea as Smart_Utility."""
    allowed = allowed_user_ids()
    if not allowed:
        return False
    return user_id in allowed


def log_allowlist_status() -> None:
    allowed = allowed_user_ids()
    if not allowed:
        logger.error(
            "ALLOWED_TELEGRAM_IDS is empty — the bot will reject every user. "
            "Set comma-separated numeric Telegram IDs in the environment."
        )
    else:
        logger.info("Allowlist size: %s", len(allowed))
