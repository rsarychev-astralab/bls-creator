from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import ROOT
from app.output.result_xlsx import RESULTS_DIR
from app.net import force_ipv4
from app.modeling.deepseek import ModelCancelled, cancel_model, fill_prompt, model_pack
from app.output.result_sheet import write_result_sheet
from app.sources.collect import collect_campaign, get_pack
from app.sources.sheet import get_campaign, list_campaigns

force_ipv4()

app = FastAPI(title="BLS Creator", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


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
    return FileResponse(ROOT / "static" / "index.html")
