import logging
from typing import Dict, Any

import requests

from config import get_config

logger = logging.getLogger(__name__)


def nuki_lock_action(action: int) -> Dict[str, Any]:
    """
    Esegue un'azione di lock sul Nuki Bridge.

    action:
      1 = unlock
      2 = lock
      3 = unlatch (apri porta)
      4 = lock'n'go
      5 = lock'n'go + unlatch
    """
    cfg = get_config()
    try:
        resp = requests.get(
            f"http://{cfg.bridge_host}:{cfg.bridge_port}/lockAction",
            params={
                "nukiId": cfg.nuki_id,
                "deviceType": cfg.device_type,
                "action": action,
                "token": cfg.nuki_token,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Errore lockAction: %s", e)
        return {"error": str(e)}


def nuki_lock_state() -> Dict[str, Any]:
    """
    Legge lo stato corrente della serratura dal Nuki Bridge.
    """
    cfg = get_config()
    try:
        resp = requests.get(
            f"http://{cfg.bridge_host}:{cfg.bridge_port}/lockState",
            params={
                "nukiId": cfg.nuki_id,
                "deviceType": cfg.device_type,
                "token": cfg.nuki_token,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("lockState raw: %s", data)
        return data
    except Exception as e:
        logger.error("Errore lockState: %s", e)
        return {"error": str(e)}


def summarize_state(data: Dict[str, Any]) -> str:
    """
    Converte il JSON di stato Nuki in un riassunto leggibile.
    """
    if "error" in data:
        return f"Errore: {data['error']}"

    parts = []

    state = data.get("state")
    state_name = data.get("stateName")
    if state_name:
        parts.append(f"Stato serratura: {state_name} (state={state})")
    elif state is not None:
        parts.append(f"Stato serratura: state={state}")

    door_state = data.get("doorState")
    door_state_name = data.get("doorStateName")
    if door_state_name:
        parts.append(f"Stato porta: {door_state_name} (doorState={door_state})")
    elif door_state is not None:
        parts.append(f"Stato porta: doorState={door_state}")

    batt_pct = None
    if isinstance(data.get("batteryCharge"), (int, float)):
        batt_pct = data["batteryCharge"]
    else:
        bcs = data.get("batteryChargeState")
        if isinstance(bcs, dict) and isinstance(bcs.get("chargeLevel"), (int, float)):
            batt_pct = bcs["chargeLevel"]
        elif isinstance(data.get("batteryLevel"), (int, float)):
            batt_pct = data["batteryLevel"]

    if batt_pct is not None:
        parts.append(f"Batteria: {batt_pct}%")
    else:
        if "batteryCritical" in data:
            parts.append(f"Batteria critica: {data['batteryCritical']}")
        if "batteryChargeState" in data:
            parts.append(f"batteryChargeState: {data['batteryChargeState']}")
        if "batteryLevel" in data and not isinstance(data.get("batteryLevel"), (int, float)):
            parts.append(f"batteryLevel: {data['batteryLevel']}")

    ts = data.get("timestamp")
    if ts:
        parts.append(f"Ultimo aggiornamento (UTC): {ts}")

    if not parts:
        return "Nessun dato di stato disponibile."

    return "\n".join(parts)
