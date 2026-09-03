import json

import httpx

from app.config import GAS_WEBAPP_URL


def gas_payload(modeled: object) -> list:
    if isinstance(modeled, list):
        return modeled
    if isinstance(modeled, dict):
        if isinstance(modeled.get("data"), list):
            return modeled["data"]
        if isinstance(modeled.get("payload"), list):
            return modeled["payload"]
        return [modeled]
    raise RuntimeError("Модель вернула не JSON-массив для GAS")


def send_to_gas(modeled: object) -> dict:
    if not GAS_WEBAPP_URL:
        raise RuntimeError("Пустой GAS_WEBAPP_URL")
    payload = gas_payload(modeled)
    with httpx.Client(timeout=60.0, verify=False, follow_redirects=True) as client:
        resp = client.post(
            GAS_WEBAPP_URL,
            headers={"Content-Type": "application/json"},
            content=json.dumps(payload, ensure_ascii=False),
        )
    text = resp.text
    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GAS вернул не JSON ({resp.status_code}): {text[:240]}") from exc
    if resp.status_code >= 400 or not data.get("ok"):
        raise RuntimeError(data.get("error") or f"GAS {resp.status_code}")
    return {
        "spreadsheet_url": data.get("spreadsheetUrl") or "",
        "spreadsheet_id": data.get("spreadsheetId") or "",
        "spreadsheet_name": data.get("spreadsheetName") or "",
    }
