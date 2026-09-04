import json

import pytest

from app.modeling.deepseek import extract_json_payload, validate_model_payload

_OK = [
    {
        "DNS TCL SuperSkin": {
            "metadata": {"total_contact_group": 400, "total_noncontact_group": 400},
            "questions": [
                {
                    "question_text": "Какие бренды знакомы?",
                    "responses": [
                        {"option": "TCL", "contact_count": 213, "noncontact_count": 178},
                    ],
                }
            ],
        }
    }
]


def test_extract_from_content():
    assert extract_json_payload(json.dumps(_OK, ensure_ascii=False), "") == _OK


def test_extract_from_reasoning_when_content_empty():
    raw = "думаю...\n" + json.dumps(_OK, ensure_ascii=False) + "\nготово"
    assert extract_json_payload("", raw) == _OK


def test_extract_empty_fails():
    with pytest.raises(RuntimeError, match="не-JSON"):
        extract_json_payload("", "   ")


def test_validate_empty_array():
    assert validate_model_payload([]) == []


def test_validate_ok():
    assert validate_model_payload(_OK) == _OK


def test_validate_rejects_non_int_counts():
    bad = [
        {
            "X": {
                "questions": [
                    {"responses": [{"option": "TCL", "contact_count": "213", "noncontact_count": 1}]}
                ]
            }
        }
    ]
    with pytest.raises(RuntimeError, match="целым"):
        validate_model_payload(bad)
