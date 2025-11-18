import logging
from datetime import datetime, timezone
from typing import Any, Dict

import requests

from config import get_config
from i18n import t

logger = logging.getLogger(__name__)


def nuki_lock_action(action: int) -> Dict[str, Any]:
    """Call the Nuki Bridge /lockAction endpoint.

    :param action: integer action code, see Nuki HTTP API documentation.
    :return: JSON response as dict, or a dict with key "error" on failure.
    """
    cfg = get_config()
    url = f"http://{cfg.bridge_host}:{cfg.bridge_port}/lockAction"
    params = {
        "nukiId": cfg.nuki_id,
        "deviceType": cfg.device_type,
        "token": cfg.nuki_token,
        "action": action,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.debug("Nuki /lockAction response: %s", data)
        return data
    except Exception as exc:
        logger.error("Error calling Nuki /lockAction: %s", exc)
        return {"error": str(exc)}


def nuki_lock_state() -> Dict[str, Any]:
    """Call the Nuki Bridge /lockState endpoint."""
    cfg = get_config()
    url = f"http://{cfg.bridge_host}:{cfg.bridge_port}/lockState"
    params = {
        "nukiId": cfg.nuki_id,
        "deviceType": cfg.device_type,
        "token": cfg.nuki_token,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.debug("Nuki /lockState response: %s", data)
        return data
    except Exception as exc:
        logger.error("Error calling Nuki /lockState: %s", exc)
        return {"error": str(exc)}


def summarize_state(data: Dict[str, Any], lang: str = "it") -> str:
    """Return a human-readable summary of the lock state.

    This is intentionally simple and mostly language-independent, with small
    labels translated via :mod:`i18n`.
    """
    if not data:
        return t("state_no_data", lang)

    parts = []

    state = data.get("state")
    state_name = data.get("stateName", str(state))
    if state is not None:
        parts.append(t("state_header_state", lang, state_name=state_name, state=state))

    door_state = data.get("doorState")
    door_state_name = data.get("doorStateName", str(door_state))
    if door_state is not None:
        parts.append(
            t(
                "state_header_door",
                lang,
                door_state_name=door_state_name,
                door_state=door_state,
            )
        )

    batt_pct = data.get("batteryChargeState")
    if batt_pct is not None:
        parts.append(t("state_header_battery", lang, batt_pct=batt_pct))

    batt_critical = data.get("batteryCritical")
    if batt_critical is not None:
        parts.append(
            t(
                "state_header_battery_critical",
                lang,
                critical=batt_critical,
            )
        )

    ts_raw = data.get("lastActionDate") or data.get("timestamp")
    if ts_raw:
        # Nuki usually returns ISO 8601 in UTC
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            ts_str = str(ts_raw)
        parts.append(t("state_header_timestamp", lang, ts=ts_str))

    return "\n".join(parts)
