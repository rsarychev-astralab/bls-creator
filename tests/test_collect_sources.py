from app.sources.collect import brand_from_name
from app.sources.crm import deal_id_from_url, extract_deal_properties
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
