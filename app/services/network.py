import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _read_windows_system_proxy() -> Optional[str]:
    """Read enabled HTTP(S) proxy from Windows Internet Settings."""
    try:
        import winreg
    except ImportError:
        return None

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not proxy_enable:
                return None
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except OSError:
        return None

    if not proxy_server:
        return None

    proxy_server = str(proxy_server).strip()
    if not proxy_server:
        return None

    # Formats: "127.0.0.1:7890" or "http=127.0.0.1:7890;https=..."
    if "=" in proxy_server or ";" in proxy_server:
        parts = {}
        for chunk in proxy_server.split(";"):
            if "=" not in chunk:
                continue
            scheme, address = chunk.split("=", 1)
            parts[scheme.strip().lower()] = address.strip()
        proxy_server = parts.get("https") or parts.get("http") or next(
            iter(parts.values()), ""
        )

    if not proxy_server:
        return None
    if "://" not in proxy_server:
        proxy_server = f"http://{proxy_server}"
    return proxy_server


def resolve_telegram_proxy() -> Optional[str]:
    """
    Resolve proxy for Telegram API.

    Priority:
    1. BOT_PROXY_URL environment variable
    2. Enabled Windows system proxy (for example Karing / Clash)
    """
    explicit = (os.environ.get("BOT_PROXY_URL") or "").strip()
    if explicit:
        logger.info("Using proxy from BOT_PROXY_URL")
        return explicit

    system_proxy = _read_windows_system_proxy()
    if system_proxy:
        logger.info("Using Windows system proxy for Telegram API: %s", system_proxy)
        return system_proxy

    logger.warning(
        "No proxy configured. If api.telegram.org is blocked, set BOT_PROXY_URL "
        "or enable a local proxy (for example Karing)."
    )
    return None
