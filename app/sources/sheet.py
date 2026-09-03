from functools import lru_cache

import gspread
from google.oauth2.service_account import Credentials

from app.config import SPREADSHEET_ID, SHEET_NAME, sa_path

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLS = {
    "submitted_at": 0,
    "email": 1,
    "research_type": 2,
    "name": 3,
    "questionnaire_url": 4,
    "creative_url": 5,
    "dl": 6,
    "comment": 7,
    "crm_url": 8,
    "test_url": 9,
    "category": 10,
    "status": 11,
    "result_url": 12,
}


@lru_cache(maxsize=1)
def _client() -> gspread.Client:
    creds = Credentials.from_service_account_file(str(sa_path()), scopes=SCOPES)
    return gspread.authorize(creds)


def _cell(row: list[str], idx: int) -> str:
    if idx >= len(row):
        return ""
    return str(row[idx]).strip()


def _to_campaign(row_num: int, row: list[str]) -> dict:
    return {
        "row": row_num,
        "submitted_at": _cell(row, COLS["submitted_at"]),
        "email": _cell(row, COLS["email"]),
        "research_type": _cell(row, COLS["research_type"]),
        "name": _cell(row, COLS["name"]),
        "questionnaire_url": _cell(row, COLS["questionnaire_url"]),
        "creative_url": _cell(row, COLS["creative_url"]),
        "dl": _cell(row, COLS["dl"]),
        "comment": _cell(row, COLS["comment"]),
        "crm_url": _cell(row, COLS["crm_url"]),
        "test_url": _cell(row, COLS["test_url"]),
        "category": _cell(row, COLS["category"]),
        "status": _cell(row, COLS["status"]),
        "result_url": _cell(row, COLS["result_url"]),
    }


def list_campaigns() -> list[dict]:
    ws = _client().open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    values = ws.get_all_values()
    out = []
    for i, row in enumerate(values[1:], start=2):
        item = _to_campaign(i, row)
        if item["name"] and item["status"] not in {"Сдан", "Можно отдавать"}:
            out.append(item)
    out.reverse()
    return out


def get_campaign(row_num: int) -> dict:
    ws = _client().open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    row = ws.row_values(row_num)
    item = _to_campaign(row_num, row)
    if not item["name"]:
        raise KeyError(f"Пустая строка {row_num}")
    return item
