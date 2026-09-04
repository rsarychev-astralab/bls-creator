import re

from app.sources.crm import fetch_crm
from app.sources.notion import fetch_notion_deal
from app.sources.questionnaire import fetch_questionnaire, fetch_questionnaire_from_notion
from app.sources.sheet import get_campaign

_PACKS: dict[int, dict] = {}

_PROP_GEO = "ГЕО"
_PROP_TARGET = "ЦА + Таргетирование"
_PROP_BRAND = "Рекламодатель (Бренд)"


def notion_deal_url(sheet_url: str, crm: dict | None = None) -> str:
    raw = (sheet_url or "").strip()
    if "notion." in raw.lower():
        return raw
    page_id = ((crm or {}).get("page_id") or "").replace("-", "")
    if page_id:
        return f"https://www.notion.so/{page_id}"
    return ""


def crm_deal_url(crm: dict | None) -> str:
    if not crm:
        return ""
    url = (crm.get("url") or "").strip()
    if "crm.al-ad.tech" in url:
        return url
    deal_id = crm.get("deal_id") or ""
    if deal_id:
        return f"https://crm.al-ad.tech/deals?deal={deal_id}"
    return ""


_FORMAT_SEPS = (
    " Astra",
    " Smart",
    " Attention",
    " White",
    " Reach",
    " In-",
    " SuperSkin",
    " Super ",
    " CTV",
)
_SKIP_NAME_TOKENS = {"i", "мск", "рф", "tv", "ctv"}


def brand_from_name(name: str) -> str:
    text = (name or "").strip()
    if text.startswith("I /"):
        text = text[3:].strip()
    for sep in _FORMAT_SEPS:
        idx = text.find(sep)
        if idx > 0:
            return text[:idx].strip(" /|-")
    return text.split("|")[0].strip()


def brand_from_questionnaire(text: str, name: str, advertiser: str = "") -> str:
    if not (text or "").strip():
        return ""
    candidates = []
    for part in re.findall(r"[A-Za-zА-Яа-яЁё0-9&]{2,}", brand_from_name(name)):
        if part.lower() not in _SKIP_NAME_TOKENS:
            candidates.append(part)
    if advertiser and advertiser.strip() not in candidates:
        candidates.append(advertiser.strip())
    scored = []
    for cand in candidates:
        count = len(re.findall(re.escape(cand), text, re.I))
        if count:
            scored.append((count, cand))
    if not scored:
        return ""
    scored.sort(key=lambda item: item[0], reverse=True)
    advert = (advertiser or "").strip().lower()
    for count, cand in scored:
        if cand.lower() != advert:
            return cand
    return scored[0][1]


def resolve_brands(name: str, advertiser: str = "", questionnaire_text: str = "") -> dict:
    advert = (advertiser or "").strip()
    from_name = brand_from_name(name)
    from_q = brand_from_questionnaire(questionnaire_text, name, advert)
    advertised = from_q or from_name
    source = "questionnaire" if from_q else "name"
    if advert and advertised.lower().startswith(advert.lower()):
        rest = advertised[len(advert) :].strip(" /|-")
        if rest:
            advertised = rest
            if not from_q:
                source = "name"
    if not advertised:
        advertised = advert
        source = "crm" if advert else ""
    if not advert:
        advert = from_name or advertised
    return {
        "advertiser": advert,
        "advertised_brand": advertised,
        "advertised_source": source,
    }


def _fill_from_notion(props: dict, sources: dict, crm_url: str) -> dict:
    needed = [_PROP_BRAND, _PROP_GEO, _PROP_TARGET]
    if all(props.get(key) for key in needed):
        return {"ok": False, "skipped": True, "properties": {}}
    notion = fetch_notion_deal(crm_url)
    nprops = notion.get("properties") or {}
    if not notion.get("ok"):
        return notion
    for key in needed:
        if not props.get(key) and nprops.get(key):
            props[key] = nprops[key]
            sources[key] = "notion"
    return notion


def _questionnaire_with_fallback(crm_q: dict, campaign: dict) -> dict:
    if crm_q.get("ok") and crm_q.get("text"):
        return crm_q
    notion_q = fetch_questionnaire_from_notion(campaign["crm_url"])
    if notion_q.get("ok") and notion_q.get("text"):
        notion_q["fallback_from"] = crm_q.get("error") or "crm empty"
        return notion_q
    drive = fetch_questionnaire(campaign["questionnaire_url"])
    if drive.get("ok") and drive.get("text"):
        drive["source"] = drive.get("source") or "drive"
        drive["fallback_from"] = notion_q.get("error") or crm_q.get("error") or ""
        return drive
    errors = [crm_q.get("error"), notion_q.get("error"), drive.get("error")]
    return {
        "ok": False,
        "error": " / ".join(x for x in errors if x),
        "text": "",
        "source": "none",
    }


def collect_campaign(row_num: int) -> dict:
    campaign = get_campaign(row_num)
    crm = fetch_crm(campaign["crm_url"], campaign_name=campaign["name"])
    props = dict(crm.get("properties") or {})
    sources = {
        _PROP_BRAND: "crm" if props.get(_PROP_BRAND) else "",
        _PROP_GEO: "crm" if props.get(_PROP_GEO) else "",
        _PROP_TARGET: "crm" if props.get(_PROP_TARGET) else "",
        "questionnaire": "",
    }

    if crm.get("ok"):
        questionnaire = _questionnaire_with_fallback(crm.pop("questionnaire", None) or {}, campaign)
    else:
        questionnaire = _questionnaire_with_fallback({"ok": False, "error": crm.get("error"), "text": ""}, campaign)

    notion = _fill_from_notion(props, sources, campaign["crm_url"])
    if not crm.get("ok") and notion.get("ok"):
        crm = {
            **crm,
            "ok": True,
            "source": "notion",
            "crm_error": crm.get("error"),
            "title": notion.get("title") or crm.get("title") or "",
            "properties": props or notion.get("properties") or {},
            "page_id": notion.get("page_id"),
        }
    elif notion.get("ok") and any(v == "notion" for v in sources.values()):
        crm["source"] = "crm+notion"
        crm["notion_fallback"] = True
    if crm.get("ok"):
        crm["properties"] = props

    sources["questionnaire"] = questionnaire.get("source") or ""
    brands = resolve_brands(
        campaign["name"],
        props.get(_PROP_BRAND) or "",
        questionnaire.get("text") or "",
    )
    if not sources[_PROP_BRAND]:
        sources[_PROP_BRAND] = "name" if brands["advertiser"] else ""
    pack = {
        "row": row_num,
        "campaign": campaign,
        "advertiser": brands["advertiser"],
        "advertised_brand": brands["advertised_brand"],
        "geo": props.get(_PROP_GEO, ""),
        "targeting": props.get(_PROP_TARGET, ""),
        "crm_deal_url": crm_deal_url(crm),
        "notion_url": notion_deal_url(campaign.get("crm_url") or "", crm),
        "bt_url": crm.get("bt_url") or "",
        "closing": crm.get("closing") or [],
        "respondents_contact": 400,
        "respondents_noncontact": 400,
        "questionnaire": questionnaire,
        "crm": crm,
        "sources": {
            "advertiser": sources[_PROP_BRAND],
            "brand": brands["advertised_source"],
            "geo": sources[_PROP_GEO],
            "targeting": sources[_PROP_TARGET],
            "questionnaire": sources["questionnaire"],
            "bt": crm.get("bt_source") or ("crm" if crm.get("bt_url") else ""),
            "closing": "crm" if any((x.get("value") for x in (crm.get("closing") or []))) else "",
        },
    }
    _PACKS[row_num] = pack
    return pack


def get_pack(row_num: int) -> dict | None:
    return _PACKS.get(row_num)


def attach_questionnaire(row_num: int, name: str, text: str) -> dict:
    pack = _PACKS.get(row_num)
    if not pack:
        raise KeyError(f"Сначала собери данные исследования")
    pack["questionnaire"] = {
        "ok": True,
        "error": "",
        "name": name,
        "text": text,
        "source": "upload",
    }
    pack["sources"]["questionnaire"] = "upload"
    brands = resolve_brands(
        (pack.get("campaign") or {}).get("name") or "",
        pack.get("advertiser") or "",
        text,
    )
    pack["advertiser"] = brands["advertiser"]
    pack["advertised_brand"] = brands["advertised_brand"]
    pack["sources"]["brand"] = brands["advertised_source"]
    return pack
