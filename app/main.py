from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import ROOT
from app.output.result_xlsx import RESULTS_DIR
from app.net import force_ipv4
from app.modeling.deepseek import ModelCancelled, cancel_model, fill_prompt, model_pack
from app.output.result_sheet import write_result_sheet
from app.sources.collect import attach_questionnaire, collect_campaign, get_pack
from app.sources.questionnaire import text_from_upload
from app.sources.sheet import get_campaign, list_campaigns

force_ipv4()

app = FastAPI(title="BLS Creator", docs_url=None, redoc_url=None)
DIST = ROOT / "web" / "dist"


class RowIn(BaseModel):
    row: int


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/campaigns")
def api_campaigns():
    try:
        return {"items": list_campaigns()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/campaigns/{row}")
def api_campaign(row: int):
    try:
        return get_campaign(row)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/collect")
def api_collect(body: RowIn):
    try:
        pack = collect_campaign(body.row)
        pack["prompt"] = fill_prompt(pack)
        return pack
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/questionnaire")
async def api_questionnaire(row: int = Form(...), file: UploadFile = File(...)):
    raw = await file.read()
    name = (file.filename or "анкета").strip()
    text = text_from_upload(name, raw)
    if not text:
        raise HTTPException(400, "Не удалось прочитать файл анкеты. Нужен .xlsx, .docx, .txt, .md или .csv")
    try:
        pack = attach_questionnaire(row, name, text)
    except KeyError as exc:
        raise HTTPException(400, str(exc)) from exc
    pack["prompt"] = fill_prompt(pack)
    return pack


@app.post("/api/model")
def api_model(body: RowIn):
    pack = get_pack(body.row)
    if not pack:
        raise HTTPException(400, "Сначала собери данные исследования")
    try:
        result = model_pack(pack)
    except ModelCancelled as exc:
        raise HTTPException(499, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc
    try:
        result.update(write_result_sheet(result["payload"]))
    except Exception as exc:  # noqa: BLE001
        result["spreadsheet_url"] = ""
        result["gas_error"] = str(exc)
    return result


@app.post("/api/model/stop")
def api_model_stop():
    return {"ok": True, "stopped": cancel_model()}


@app.get("/api/results/{filename}")
def api_result_file(filename: str):
    path = (RESULTS_DIR / filename).resolve()
    if path.parent != RESULTS_DIR.resolve() or not path.is_file():
        raise HTTPException(404, "Файл результата не найден")
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/")
def index():
    index_path = DIST / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    raise HTTPException(404, "Фронт не собран. В web/: npm install && npm run build")


@app.get("/{asset_path:path}")
def frontend_asset(asset_path: str):
    if not DIST.is_dir():
        raise HTTPException(404, "Фронт не собран")
    target = (DIST / asset_path).resolve()
    if DIST.resolve() not in target.parents:
        raise HTTPException(404)
    if target.is_file():
        return FileResponse(target)
    raise HTTPException(404)
