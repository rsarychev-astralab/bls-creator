from pathlib import Path

from dotenv import load_dotenv
from os import getenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

GOOGLE_SERVICE_ACCOUNT_FILE = getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE", "bls-auto-482107-115571563f33.json"
)
SPREADSHEET_ID = getenv("SPREADSHEET_ID", "")
SHEET_NAME = getenv("SHEET_NAME", "2026 год")
NOTION_TOKEN = getenv("NOTION_TOKEN", "")
CRM_API_URL = (getenv("CRM_API_URL") or "https://crm.al-ad.tech/api").rstrip("/")
CRM_LOGIN = (getenv("CRM_LOGIN") or "").strip()
CRM_PASSWORD = (getenv("CRM_PASSWORD") or "").strip()
DEEPSEEK_API_KEY = getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
GAS_WEBAPP_URL = getenv(
    "GAS_WEBAPP_URL",
    "https://script.google.com/macros/s/AKfycbxMhU5qa4o61pAkkT8X8QxUgfvLCLq6N3qZyKeYKWU_tc_YC9R5hKgqywYBbbTF4fRZ/exec",
)
RESULT_FOLDER_ID = getenv("RESULT_FOLDER_ID", "")
RESULT_SHARE_EMAIL = getenv("RESULT_SHARE_EMAIL", "")
PROMPT_PATH = ROOT / "prompts" / "bls_model.md"


def sa_path() -> Path:
    path = Path(GOOGLE_SERVICE_ACCOUNT_FILE)
    if not path.is_absolute():
        path = ROOT / path
    return path
