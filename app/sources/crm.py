import re
import threading
from urllib.parse import unquote

import httpx

from app.config import CRM_API_URL, CRM_LOGIN, CRM_PASSWORD
from app.sources.notion import notion_page_id
from app.sources.questionnaire import docx_to_text, drive_file_id, fetch_questionnaire

DEAL_URL_RE = re.compile(r"(?:/deals/|/deal/)([a-f0-9]{24})", re.I)
DEAL_QUERY_RE = re.compile(r"[?&]deal=([a-f0-9]{24})", re.I)
MONGO_ID_RE = re.compile(r"^[a-f0-9]{24}$", re.I)

_lock = threading.Lock()
_token = ""
_refresh = ""


def _base() -> str:
    return CRM_API_URL or "https://crm.al-ad.tech/api"


def deal_id_from_url(url: str) -> str:
    raw = (url or "").strip()
    if MONGO_ID_RE.match(raw):
        return raw.lower()
    q = DEAL_QUERY_RE.search(raw)
    if q:
        return q.group(1).lower()
    m = DEAL_URL_RE.search(raw.split("?")[0])
    return (m.group(1).lower() if m else "")


def section_field(deal: dict, key: str) -> dict:
    for sec in deal.get("sections") or []:
        for field in sec.get("fields") or []:
            if field.get("key") == key:
                return field
    return {}


def field_text(field: dict | None) -> str:
    if not field:
        return ""
    if field.get("value") not in (None, ""):
        return str(field["value"]).strip()
    values = field.get("values")
    if values:
        return ", ".join(str(x) for x in values if x)
    if field.get("checked") is True:
        return "да"
    if field.get("checked") is False:
        return "нет"
    return ""


def extract_deal_properties(deal: dict) -> dict:
    flags = deal.get("flags") or {}
    content = deal.get("dealContent") or {}
    booking = (content.get("bookingText") or field_text(section_field(deal, "bookingText"))).strip()
    props = {
        "Название": (deal.get("title") or "").strip(),
        "Рекламодатель (Бренд)": (deal.get("brand") or "").strip(),
        "ГЕО": (deal.get("geo") or field_text(section_field(deal, "geo"))).strip(),
        "ЦА + Таргетирование": (
            deal.get("targetAudience") or field_text(section_field(deal, "targetAudience"))
        ).strip(),
        "Brand lift": "да" if flags.get("brandLift") else "нет",
        "Бронь (Текстом)": booking,
        "Формат": field_text(section_field(deal, "formats")),
        "Time": field_text(section_field(deal, "timeSpent")),
        "VTR (для видео форматов)": field_text(section_field(deal, "vtr")),
    }
    return {k: v for k, v in props.items() if v}


def survey_files(deal: dict) -> list[dict]:
    return list(section_field(deal, "brandLiftSurvey").get("files") or [])


def _store_session(resp: httpx.Response, data: dict) -> str:
    global _token, _refresh
    token = data.get("accessToken") or data.get("access_token") or ""
    refresh = data.get("refreshToken") or ""
    cookie = resp.cookies.get("crm_refresh") or ""
    _token = token
    _refresh = refresh or cookie or _refresh
    return token


def _login(client: httpx.Client) -> str:
    if not CRM_LOGIN or not CRM_PASSWORD:
        raise RuntimeError("Пустые CRM_LOGIN / CRM_PASSWORD")
    resp = client.post(
        f"{_base()}/auth/login",
        json={"login": CRM_LOGIN, "password": CRM_PASSWORD},
    )
    data = resp.json() if resp.content else {}
    if resp.status_code != 200:
        raise RuntimeError(data.get("message") or f"CRM login {resp.status_code}")
    token = _store_session(resp, data)
    if not token:
        raise RuntimeError("CRM login: нет accessToken")
    return token


def _refresh_access(client: httpx.Client) -> str:
    if not _refresh:
        return _login(client)
    resp = client.post(
        f"{_base()}/auth/refresh",
        json={"refreshToken": _refresh},
    )
    data = resp.json() if resp.content else {}
    if resp.status_code != 200:
        return _login(client)
    token = _store_session(resp, data)
    return token or _login(client)


def _request(method: str, path: str, **kwargs) -> httpx.Response:
    global _token
    with _lock:
        with httpx.Client(timeout=40.0, follow_redirects=True) as client:
            if not _token:
                _login(client)
            headers = dict(kwargs.pop("headers", None) or {})
            headers["Authorization"] = f"Bearer {_token}"
            resp = client.request(method, f"{_base()}{path}", headers=headers, **kwargs)
            if resp.status_code == 401:
                _refresh_access(client)
                headers["Authorization"] = f"Bearer {_token}"
                resp = client.request(method, f"{_base()}{path}", headers=headers, **kwargs)
            return resp


def _json(method: str, path: str, **kwargs):
    resp = _request(method, path, **kwargs)
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        raise RuntimeError(data.get("message") or f"CRM {resp.status_code} {path}")
    return data


def resolve_deal_id(url: str, campaign_name: str = "") -> tuple[str, str]:
    direct = deal_id_from_url(url)
    if direct:
        return direct, "url"

    page_id = notion_page_id(url)
    if page_id:
        try:
            data = _json("GET", f"/pipedrive/notion-page/{page_id}/crm-deal")
            found = data.get("crmDealId") or data.get("id") or ""
            if found:
                return str(found), "notion-page"
        except Exception:  # noqa: BLE001
            pass

    title = (campaign_name or "").strip()
    if title:
        data = _json("GET", "/search", params={"q": title, "scope": "all"})
        deals = ((data.get("groups") or {}).get("deal") or [])
        exact = [x for x in deals if (x.get("title") or "").strip() == title]
        pick = (exact or deals)
        if pick:
            return str(pick[0].get("id") or pick[0].get("navId") or ""), "search"
        listed = _json(
            "GET",
            "/deals",
            params={"limit": "10", "scope": "all", "search": title, "searchFields": "title"},
        )
        items = listed.get("items") or []
        exact = [x for x in items if (x.get("title") or "").strip() == title]
        pick = exact or items
        if pick:
            return str(pick[0].get("_id") or pick[0].get("id") or ""), "search"

    return "", "none"


def fetch_deal(deal_id: str) -> dict:
    return _json("GET", f"/deals/{deal_id}")


def _file_is_external(item: dict) -> bool:
    fid = str(item.get("id") or "")
    return bool(item.get("isExternal")) or fid.startswith("external:")


def _google_url(item: dict) -> str:
    for raw in (item.get("fileName"), item.get("downloadUrl"), item.get("id")):
        text = unquote(str(raw or ""))
        if drive_file_id(text) or "docs.google.com" in text or "drive.google.com" in text:
            return text
    return ""


def _download_bytes(item: dict) -> tuple[bytes, str]:
    fid = str(item.get("id") or "")
    name = item.get("fileName") or ""
    if fid and not _file_is_external(item):
        resp = _request("GET", f"/deals/files/{fid}/content")
        if resp.status_code == 200 and resp.content:
            return resp.content, resp.headers.get("content-type", "")
    url = item.get("downloadUrl") or ""
    if url.startswith("/"):
        resp = _request("GET", url[4:] if url.startswith("/api") else url)
        if resp.status_code == 200:
            return resp.content, resp.headers.get("content-type", "")
    if url.startswith("http"):
        with httpx.Client(timeout=30.0, follow_redirects=True, verify=False) as raw:
            downloaded = raw.get(url)
        if downloaded.status_code == 200:
            return downloaded.content, downloaded.headers.get("content-type", "")
    if fid.startswith("external:"):
        hidden = unquote(fid[len("external:") :])
        if hidden.startswith("http"):
            with httpx.Client(timeout=30.0, follow_redirects=True, verify=False) as raw:
                downloaded = raw.get(hidden)
            if downloaded.status_code == 200:
                return downloaded.content, downloaded.headers.get("content-type", "")
    return b"", ""


def _file_to_text(item: dict) -> tuple[str, str]:
    name = item.get("fileName") or ""
    google = _google_url(item)
    if google:
        drive = fetch_questionnaire(google)
        if drive.get("ok") and drive.get("text"):
            return drive["text"], ""
        return "", drive.get("error") or f"Drive: {name or google}"

    fid = str(item.get("id") or "")
    if fid and not _file_is_external(item):
        try:
            data = _json("GET", f"/deals/files/{fid}/text")
            text = (data.get("content") or "").strip()
            if text:
                return text, ""
        except Exception as exc:  # noqa: BLE001
            text_err = str(exc)
        else:
            text_err = ""
    else:
        text_err = ""

    data, ctype = _download_bytes(item)
    if not data:
        return "", text_err or f"Не скачался файл {name or fid}"
    if "wordprocessingml" in ctype or name.lower().endswith(".docx"):
        return docx_to_text(data), ""
    try:
        return data.decode("utf-8", errors="replace").strip(), ""
    except Exception as exc:  # noqa: BLE001
        return "", str(exc)


def fetch_questionnaire_from_crm_deal(deal: dict) -> dict:
    files = survey_files(deal)
    if not files:
        return {
            "ok": False,
            "error": "В CRM пустое поле «Анкета Brand lift»",
            "text": "",
            "source": "crm",
        }
    texts = []
    names = []
    errors = []
    for item in files:
        name = item.get("fileName") or item.get("id") or "файл"
        names.append(name)
        text, err = _file_to_text(item)
        if text:
            texts.append(text)
        elif err:
            errors.append(err)
    joined = "\n\n".join(t for t in texts if t).strip()
    if not joined:
        return {
            "ok": False,
            "error": "; ".join(errors) or "Не удалось прочитать анкету из CRM",
            "name": ", ".join(names),
            "text": "",
            "source": "crm",
        }
    return {
        "ok": True,
        "error": "; ".join(errors),
        "name": ", ".join(names),
        "text": joined,
        "source": "crm",
    }


def fetch_crm(url: str, campaign_name: str = "") -> dict:
    if not CRM_LOGIN or not CRM_PASSWORD:
        return {"ok": False, "error": "Пустые CRM_LOGIN / CRM_PASSWORD", "properties": {}}
    try:
        deal_id, via = resolve_deal_id(url, campaign_name)
        if not deal_id:
            return {
                "ok": False,
                "error": "Сделку в CRM не нашёл по ссылке и названию РК",
                "properties": {},
                "resolved_via": via,
            }
        deal = fetch_deal(deal_id)
        props = extract_deal_properties(deal)
        questionnaire = fetch_questionnaire_from_crm_deal(deal)
        return {
            "ok": True,
            "error": "",
            "source": "crm",
            "deal_id": deal_id,
            "resolved_via": via,
            "url": f"https://crm.al-ad.tech/deals?deal={deal_id}",
            "title": deal.get("title") or props.get("Название") or "",
            "properties": props,
            "questionnaire": questionnaire,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "properties": {}}
