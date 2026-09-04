from app.sources.collect import _PACKS, attach_questionnaire, brand_from_name, crm_deal_url, notion_deal_url
from app.sources.questionnaire import text_from_upload
from app.sources.crm import deal_id_from_url, extract_bt_url, extract_closing, extract_deal_properties
from app.sources.notion import notion_page_id


def test_notion_page_id():
    url = "https://www.notion.so/AstraLab/Pikador-abcdef0123456789abcdef0123456789"
    assert notion_page_id(url) == "abcdef01-2345-6789-abcd-ef0123456789"


def test_deal_id_from_url():
    assert deal_id_from_url("https://crm.al-ad.tech/deals?deal=6a6d2d0580f24d55c66442fc") == "6a6d2d0580f24d55c66442fc"
    assert deal_id_from_url("https://crm.al-ad.tech/deals/6a6d2d0580f24d55c66442fc") == "6a6d2d0580f24d55c66442fc"
    assert deal_id_from_url("6a6d2d0580f24d55c66442fc") == "6a6d2d0580f24d55c66442fc"


def test_extract_deal_properties():
    deal = {
        "title": "I / Pikador AstraCTV",
        "brand": "Heinz",
        "geo": "Москва",
        "targetAudience": "25-54",
        "flags": {"brandLift": True},
        "dealContent": {"bookingText": "бронь"},
        "sections": [
            {
                "fields": [
                    {"key": "formats", "values": ["SmartTube CTV"]},
                    {"key": "vtr", "value": "75%"},
                    {"key": "timeSpent", "value": "> 1 минуты"},
                ]
            }
        ],
    }
    props = extract_deal_properties(deal)
    assert props["Рекламодатель (Бренд)"] == "Heinz"
    assert props["ГЕО"] == "Москва"
    assert props["ЦА + Таргетирование"] == "25-54"
    assert props["Формат"] == "SmartTube CTV"
    assert props["Brand lift"] == "да"


def test_brand_from_name():
    assert brand_from_name("I / Pikador AstraCTV Мск Лето-Осень 2026 | jul-sep") == "Pikador"


def test_extract_closing():
    deal = {
        "sections": [
            {
                "key": "closing",
                "fields": [
                    {"key": "ctrActual", "value": "0.55"},
                    {"key": "vtrActual", "value": "76.07"},
                    {"key": "volumeActual", "value": "3338402"},
                ],
            }
        ]
    }
    rows = {x["key"]: x["value"] for x in extract_closing(deal)}
    assert rows["ctrActual"] == "0.55"
    assert rows["vtrActual"] == "76.07"
    assert rows["volumeActual"] == "3338402"
    assert rows["feedback"] == ""


def test_extract_bt_url():
    deal = {
        "sections": [
            {
                "fields": [
                    {
                        "key": "btUrl",
                        "files": [
                            {
                                "id": "legacy:0:1Gr3tWy1wchBQWj9tp_n8c7dL-h1lbr8eXuueohUnLuM",
                                "downloadUrl": "https://docs.google.com/spreadsheets/d/1Gr3tWy1wchBQWj9tp_n8c7dL-h1lbr8eXuueohUnLuM#gid=750773902",
                            }
                        ],
                    }
                ]
            }
        ]
    }
    assert extract_bt_url(deal).endswith("1Gr3tWy1wchBQWj9tp_n8c7dL-h1lbr8eXuueohUnLuM#gid=750773902")


def test_deal_urls():
    sheet = "https://app.notion.com/p/a-lab-ai/DNS-TCL-3bb756004aa880ec954be704e9572980"
    crm = {"deal_id": "6a7e507bed6862fdb3e7259f", "url": "https://crm.al-ad.tech/deals?deal=6a7e507bed6862fdb3e7259f"}
    assert notion_deal_url(sheet, crm) == sheet
    assert crm_deal_url(crm) == "https://crm.al-ad.tech/deals?deal=6a7e507bed6862fdb3e7259f"
    assert crm_deal_url({"deal_id": "6a7e507bed6862fdb3e7259f"}) == "https://crm.al-ad.tech/deals?deal=6a7e507bed6862fdb3e7259f"


def test_text_from_upload_txt():
    assert "бренд" in text_from_upload("q.txt", "Вопрос про бренд\n".encode("utf-8"))


def test_text_from_upload_empty():
    assert text_from_upload("q.txt", b"") == ""


def test_text_from_upload_xlsx():
    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    sheet = wb.active
    sheet.title = "Анкета"
    sheet["A1"] = "Рекламируемый бренд"
    sheet["B1"] = "TCL"
    buf = BytesIO()
    wb.save(buf)
    text = text_from_upload("anketa.xlsx", buf.getvalue())
    assert "Рекламируемый бренд" in text
    assert "TCL" in text


def test_attach_questionnaire():
    _PACKS[1] = {"questionnaire": {"ok": False}, "sources": {}}
    try:
        pack = attach_questionnaire(1, "anketa.txt", "текст")
        assert pack["questionnaire"]["ok"] is True
        assert pack["questionnaire"]["name"] == "anketa.txt"
        assert pack["sources"]["questionnaire"] == "upload"
    finally:
        _PACKS.pop(1, None)
