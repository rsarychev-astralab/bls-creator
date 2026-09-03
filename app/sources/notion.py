import re

import httpx

from app.config import NOTION_TOKEN

NOTION_VERSION = "2022-06-28"
PAGE_ID_RE = re.compile(r"([0-9a-f]{32})", re.I)

INTERESTING = (
    "Рекламодатель (Бренд)",
    "Название",
    "ГЕО",
    "ЦА + Таргетирование",
    "Brand lift",
    "Бронь (Текстом)",
    "Формат",
    "Place",
    "Time",
    "CATEGORY_ID",
    "VTR (для видео форматов)",
)


def notion_page_id(url: str) -> str:
    raw = url or ""
    m = PAGE_ID_RE.search(raw.split("?")[0])
    if not m:
        return ""
    hex_id = m.group(1)
    return f"{hex_id[:8]}-{hex_id[8:12]}-{hex_id[12:16]}-{hex_id[16:20]}-{hex_id[20:]}"


def _plain(rich: list | None) -> str:
    if not rich:
        return ""
    return "".join(part.get("plain_text", "") for part in rich).strip()


def _prop_value(prop: dict) -> str:
    ptype = prop.get("type")
    val = prop.get(ptype)
    if ptype in {"title", "rich_text"}:
        return _plain(val)
    if ptype == "select" and val:
        return val.get("name", "")
    if ptype == "multi_select":
        return ", ".join(x.get("name", "") for x in (val or []))
    if ptype == "checkbox":
        return "да" if val else "нет"
    if ptype == "url":
        return val or ""
    if ptype == "number":
        return "" if val is None else str(val)
    if ptype == "date" and val:
        return val.get("start") or ""
    if ptype == "status" and val:
        return val.get("name", "")
    if ptype == "people":
        return ", ".join(x.get("name", "") for x in (val or []) if x.get("name"))
    return ""


def fetch_notion_deal(url: str) -> dict:
    page_id = notion_page_id(url)
    if not page_id:
        return {"ok": False, "error": "Нет ссылки Notion / не разобрал id страницы", "properties": {}}
    if not NOTION_TOKEN:
        return {"ok": False, "error": "Пустой NOTION_TOKEN", "properties": {}}
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
    }
    try:
        with httpx.Client(timeout=20.0, verify=False, headers=headers) as client:
            resp = client.get(f"https://api.notion.com/v1/pages/{page_id}")
            data = resp.json()
            if resp.status_code != 200:
                return {
                    "ok": False,
                    "error": data.get("message") or f"Notion {resp.status_code}",
                    "page_id": page_id,
                    "properties": {},
                }
            raw_props = data.get("properties") or {}
            props = {name: _prop_value(prop) for name, prop in raw_props.items()}
            props = {k: v for k, v in props.items() if v}
            picked = {k: props[k] for k in INTERESTING if k in props}
            return {
                "ok": True,
                "error": "",
                "source": "notion",
                "page_id": page_id,
                "url": url,
                "title": next(iter(picked.get("Название") or props.values()), ""),
                "properties": picked or props,
                "all_properties": props,
            }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "page_id": page_id, "properties": {}}
