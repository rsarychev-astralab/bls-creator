from app.modeling.deepseek import resolve_prompt

_PACK = {
    "campaign": {"name": "DNS TCL SuperSkin", "research_type": "BLS"},
    "advertiser": "DNS",
    "advertised_brand": "TCL",
    "geo": "Москва",
    "targeting": "25-54",
    "questionnaire": {"text": "текст анкеты"},
}


def test_resolve_prompt_keeps_custom():
    custom = "мой промпт, не шаблон"
    assert resolve_prompt(_PACK, custom) == custom


def test_resolve_prompt_falls_back_when_empty():
    filled = resolve_prompt(_PACK, "   ")
    assert "{{ADVERTISED_BRAND}}" not in filled
    assert "{{ADVERTISER}}" not in filled
    assert "TCL" in filled
    assert "DNS" in filled
    assert "текст анкеты" in filled
