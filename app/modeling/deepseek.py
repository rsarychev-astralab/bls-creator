import json
import re
import threading
import time

import httpx

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, PROMPT_PATH

_lock = threading.Lock()
_client: httpx.Client | None = None


class ModelCancelled(Exception):
    pass


def cancel_model() -> bool:
    global _client
    with _lock:
        if _client is None:
            return False
        _client.close()
        _client = None
        return True


def fill_prompt(pack: dict) -> str:
    campaign = pack["campaign"]
    q = pack.get("questionnaire") or {}
    text = PROMPT_PATH.read_text(encoding="utf-8")
    repl = {
        "{{CAMPAIGN_NAME}}": campaign.get("name", ""),
        "{{ADVERTISED_BRAND}}": pack.get("advertised_brand", ""),
        "{{RESEARCH_TYPE}}": campaign.get("research_type", ""),
        "{{QUESTIONNAIRE}}": q.get("text") or q.get("error") or "",
        "{{GEO}}": pack.get("geo", ""),
        "{{TARGETING}}": pack.get("targeting", ""),
    }
    for key, val in repl.items():
        text = text.replace(key, val)
    return text


def resolve_prompt(pack: dict, prompt: str | None = None) -> str:
    custom = (prompt or "").strip()
    if custom:
        return prompt
    return fill_prompt(pack)


def _extract_json(raw: str):
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def model_pack(pack: dict, prompt: str | None = None) -> dict:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("Пустой DEEPSEEK_API_KEY")
    q = pack.get("questionnaire") or {}
    if not q.get("text"):
        raise RuntimeError(q.get("error") or "Нет текста анкеты, моделировать нельзя")
    prompt = resolve_prompt(pack, prompt)
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    "Смоделируй BLS по входу выше. Верни только JSON-массив "
                    "по схеме из инструкции."
                ),
            },
        ],
        "thinking": {"type": "enabled"},
    }
    client = httpx.Client(timeout=180.0, verify=False)
    global _client
    with _lock:
        if _client is not None:
            _client.close()
        _client = client
    started = time.monotonic()
    try:
        resp = client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise RuntimeError(data.get("error", {}).get("message") or f"DeepSeek {resp.status_code}")
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    except (httpx.HTTPError, httpx.StreamError, RuntimeError) as exc:
        with _lock:
            cancelled = _client is None
        if cancelled:
            raise ModelCancelled("Моделирование остановлено") from exc
        raise
    finally:
        with _lock:
            if _client is client:
                client.close()
                _client = None
    elapsed = round(time.monotonic() - started, 1)
    parsed = _extract_json(content)
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return {
        "raw": content,
        "payload": parsed,
        "prompt": prompt,
        "model": data.get("model", DEEPSEEK_MODEL),
        "elapsed_sec": elapsed,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "reasoning_tokens": details.get("reasoning_tokens") or usage.get("reasoning_tokens"),
        },
    }
