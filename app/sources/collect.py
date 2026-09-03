from app.sources.crm import fetch_crm
from app.sources.questionnaire import fetch_questionnaire, fetch_questionnaire_from_notion
from app.sources.sheet import get_campaign

_PACKS: dict[int, dict] = {}


def brand_from_name(name: str) -> str:
    text = (name or "").strip()
    if text.startswith("I /"):
        text = text[3:].strip()
    for sep in (" Astra", " Smart", " Attention", " White", " Reach", " In-"):
        idx = text.find(sep)
        if idx > 0:
            return text[:idx].strip(" /|-")
    return text.split("|")[0].strip()


def collect_campaign(row_num: int) -> dict:
    campaign = get_campaign(row_num)
    questionnaire = fetch_questionnaire_from_notion(campaign["crm_url"])
    if not questionnaire.get("ok"):
        drive = fetch_questionnaire(campaign["questionnaire_url"])
        if drive.get("ok"):
            questionnaire = drive
        else:
            drive_err = drive.get("error") or ""
            notion_err = questionnaire.get("error") or ""
            questionnaire = {
                "ok": False,
                "error": " / ".join(x for x in (notion_err, drive_err) if x),
                "text": "",
                "source": "none",
            }
    crm = fetch_crm(campaign["crm_url"])
    props = crm.get("properties") or {}
    brand = props.get("Рекламодатель (Бренд)") or brand_from_name(campaign["name"])
    pack = {
        "row": row_num,
        "campaign": campaign,
        "advertised_brand": brand,
        "geo": props.get("ГЕО", ""),
        "targeting": props.get("ЦА + Таргетирование", ""),
        "questionnaire": questionnaire,
        "crm": crm,
    }
    _PACKS[row_num] = pack
    return pack


def get_pack(row_num: int) -> dict | None:
    return _PACKS.get(row_num)
