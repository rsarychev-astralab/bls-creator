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
        "{{ADVERTISER}}": pack.get("advertiser", ""),
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


def _reasoning_text(message: dict) -> str:
    for key in ("reasoning_content", "reasoning", "thinking"):
        val = message.get(key)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, dict):
            text = val.get("content") or val.get("text") or ""
            if text.strip():
                return text
    return ""


def _extract_embedded_array(raw: str):
    text = (raw or "").strip()
    start = text.find("[")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, list) else None


def extract_json_payload(content: str, reasoning: str = ""):
    for raw in (content, reasoning):
        if not (raw or "").strip():
            continue
        try:
            return _extract_json(raw)
        except json.JSONDecodeError:
            embedded = _extract_embedded_array(raw)
            if embedded is not None:
                return embedded
    raise RuntimeError("Модель вернула пустой или не-JSON ответ")


def validate_model_payload(parsed):
    if not isinstance(parsed, list):
        raise RuntimeError("Модель вернула не JSON-массив")
    if parsed == []:
        return parsed
    if len(parsed) != 1 or not isinstance(parsed[0], dict) or not parsed[0]:
        raise RuntimeError("В корне нужен массив из одного объекта кампании")
    block = next(iter(parsed[0].values()))
    if not isinstance(block, dict):
        raise RuntimeError("Объект кампании пустой")
    questions = block.get("questions")
    if not isinstance(questions, list) or not questions:
        raise RuntimeError("В ответе нет questions")
    for question in questions:
        for row in question.get("responses") or []:
            for key in ("contact_count", "noncontact_count"):
                if not isinstance(row.get(key), int):
                    raise RuntimeError(f"{key} должен быть целым числом")
    return parsed


def _choice_message(data: dict) -> dict:
    return (data.get("choices") or [{}])[0].get("message") or {}


def _usage_from(data: dict) -> dict:
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens") or usage.get("reasoning_tokens"),
    }


def _chat_body(prompt: str, thinking: bool) -> dict:
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
    }
    if thinking:
        body["thinking"] = {"type": "enabled"}
    return body


def _post_chat(client: httpx.Client, body: dict) -> dict:
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
    return data


def model_pack(pack: dict, prompt: str | None = None) -> dict:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("Пустой DEEPSEEK_API_KEY")
    q = pack.get("questionnaire") or {}
    if not q.get("text"):
        raise RuntimeError(q.get("error") or "Нет текста анкеты, моделировать нельзя")
    prompt = resolve_prompt(pack, prompt)
    client = httpx.Client(timeout=180.0, verify=False)
    global _client
    with _lock:
        if _client is not None:
            _client.close()
        _client = client
    started = time.monotonic()
    content = ""
    data = {}
    try:
        data = _post_chat(client, _chat_body(prompt, thinking=True))
        message = _choice_message(data)
        content = message.get("content") or ""
        reasoning = _reasoning_text(message)
        try:
            parsed = validate_model_payload(extract_json_payload(content, reasoning))
        except RuntimeError:
            data = _post_chat(client, _chat_body(prompt, thinking=False))
            message = _choice_message(data)
            content = message.get("content") or ""
            reasoning = _reasoning_text(message)
            parsed = validate_model_payload(extract_json_payload(content, reasoning))
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
    return {
        "raw": content or reasoning,
        "payload": parsed,
        "prompt": prompt,
        "model": data.get("model", DEEPSEEK_MODEL),
        "elapsed_sec": elapsed,
        "usage": _usage_from(data),
    }
