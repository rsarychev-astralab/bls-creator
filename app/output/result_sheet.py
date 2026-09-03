from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

from app.config import RESULT_FOLDER_ID, sa_path
from app.output.result_xlsx import write_result_xlsx
from app.sources.sheet import SCOPES


def _drive():
    creds = Credentials.from_service_account_file(str(sa_path()), scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _upload_as_sheet(xlsx_path: str, title: str) -> dict:
    drive = _drive()
    body = {
        "name": title,
        "mimeType": "application/vnd.google-apps.spreadsheet",
    }
    if RESULT_FOLDER_ID:
        body["parents"] = [RESULT_FOLDER_ID]
    media = MediaFileUpload(
        xlsx_path,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=False,
    )
    created = drive.files().create(
        body=body,
        media_body=media,
        fields="id,webViewLink,name",
        supportsAllDrives=True,
    ).execute()
    file_id = created["id"]
    return {
        "spreadsheet_url": created.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file_id}",
        "spreadsheet_id": file_id,
        "spreadsheet_name": created.get("name") or title,
    }


def write_result_sheet(modeled: object) -> dict:
    local = write_result_xlsx(modeled)
    if not RESULT_FOLDER_ID:
        return local
    try:
        google = _upload_as_sheet(local["path"], local["spreadsheet_name"])
        google["filename"] = local["filename"]
        return google
    except Exception as exc:
        text = str(exc)
        if "storageQuotaExceeded" in text or "storage quota" in text.lower():
            raise RuntimeError(
                "Сервисный аккаунт не может писать в обычную папку Drive. "
                "Нужен Общий диск (Shared drive): добавь туда "
                "bls-creator@bls-auto-482107.iam.gserviceaccount.com "
                "как менеджера контента и кинь ссылку на папку с диска."
            ) from exc
        raise
