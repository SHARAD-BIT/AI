import json
import os
import time
from typing import Any, Dict
from urllib import error, request

from dotenv import load_dotenv

try:
    from google import genai
except Exception:
    genai = None


load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_ollama_url(raw_url: str) -> str:
    url = raw_url.rstrip("/")

    if url.endswith("/api/chat"):
        return url
    if url.endswith("/api"):
        return f"{url}/chat"
    return f"{url}/api/chat"


LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "").strip().lower()
USE_OLLAMA = _as_bool(os.getenv("USE_OLLAMA"), default=False)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_EXTRACTION_MODEL = os.getenv("OLLAMA_EXTRACTION_MODEL", OLLAMA_MODEL)
OLLAMA_REASONING_MODEL = os.getenv("OLLAMA_REASONING_MODEL", OLLAMA_MODEL)
OLLAMA_FALLBACK_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL", "").strip()
OLLAMA_BASE_URL = _normalize_ollama_url(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "90"))

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

_ollama_backoff_until = 0.0
_ollama_backoff_reason = ""
_gemini_backoff_until = 0.0
_gemini_backoff_reason = ""


def _unique_non_empty(values: list[str]) -> list[str]:
    seen = set()
    result = []

    for value in values:
        normalized = (value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)

    return result


def _ollama_models_for_task(task: str) -> list[str]:
    if task == "extraction":
        return _unique_non_empty([OLLAMA_EXTRACTION_MODEL, OLLAMA_FALLBACK_MODEL, OLLAMA_MODEL])
    if task == "reasoning":
        return _unique_non_empty([OLLAMA_REASONING_MODEL, OLLAMA_FALLBACK_MODEL, OLLAMA_MODEL])
    return _unique_non_empty([OLLAMA_MODEL, OLLAMA_FALLBACK_MODEL])


def _default_value_for_field(field_schema: Dict[str, Any]):
    field_type = field_schema.get("type")

    if field_type == "array":
        return []

    if field_type == "object":
        return {}

    if field_type in {"string", "integer", "number", "boolean"}:
        return None

    any_of = field_schema.get("anyOf")
    if isinstance(any_of, list):
        for option in any_of:
            if option.get("type") == "array":
                return []
        return None

    return None


def _fallback_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return {}

    return {
        key: _default_value_for_field(field_schema if isinstance(field_schema, dict) else {})
        for key, field_schema in properties.items()
    }


def _coerce_to_json_object(raw: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")

    if start != -1 and end != -1 and end > start:
        maybe_json = raw[start : end + 1]
        try:
            parsed = json.loads(maybe_json)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    return _fallback_from_schema(schema)


def _provider_order() -> list[str]:
    if LLM_PROVIDER in {"ollama", "gemini"}:
        return [LLM_PROVIDER, "gemini" if LLM_PROVIDER == "ollama" else "ollama"]

    if USE_OLLAMA:
        return ["ollama", "gemini"]

    return ["gemini", "ollama"]


def _set_ollama_backoff(seconds: int, reason: str, log_message: str) -> None:
    global _ollama_backoff_until, _ollama_backoff_reason

    now = time.time()
    if now >= _ollama_backoff_until or reason != _ollama_backoff_reason:
        print(log_message)

    _ollama_backoff_until = now + seconds
    _ollama_backoff_reason = reason


def _set_gemini_backoff(seconds: int, reason: str, log_message: str) -> None:
    global _gemini_backoff_until, _gemini_backoff_reason

    now = time.time()
    if now >= _gemini_backoff_until or reason != _gemini_backoff_reason:
        print(log_message)

    _gemini_backoff_until = now + seconds
    _gemini_backoff_reason = reason


def _get_gemini_client():
    if genai is None:
        raise ImportError("google-genai package is not installed")

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")

    return genai.Client(api_key=GEMINI_API_KEY)


def _ollama_request(payload: dict, *, model_name: str) -> dict:
    if time.time() < _ollama_backoff_until:
        raise RuntimeError(f"Ollama temporarily skipped: {_ollama_backoff_reason}")

    payload = dict(payload)
    payload["model"] = model_name
    req = request.Request(
        OLLAMA_BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        if exc.code == 404:
            raise RuntimeError(
                error_body
                or f"Ollama model '{model_name}' missing or endpoint unavailable"
            ) from exc

        _set_ollama_backoff(
            30,
            f"http {exc.code}",
            f"Ollama HTTP error {exc.code}, trying fallback provider.",
        )
        raise RuntimeError(error_body or f"Ollama HTTP error {exc.code}") from exc
    except error.URLError as exc:
        _set_ollama_backoff(
            60,
            "service unavailable",
            f"Ollama unavailable at {OLLAMA_BASE_URL}, trying fallback provider.",
        )
        raise RuntimeError(f"Ollama unavailable: {exc.reason}") from exc
    except Exception as exc:
        _set_ollama_backoff(
            30,
            "request failed",
            "Ollama call failed, trying fallback provider.",
        )
        raise RuntimeError(f"Ollama request failed: {exc}") from exc


def _extract_ollama_content(parsed_response: dict) -> str:
    raw_content = (
        parsed_response.get("message", {}).get("content")
        or parsed_response.get("response")
        or ""
    )

    if not raw_content:
        raise RuntimeError("Ollama returned an empty response")

    return raw_content


def _call_ollama_json(prompt: str, schema: dict, task: str = "default") -> str:
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "Return only valid JSON matching the supplied schema. Do not include markdown or commentary.",
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nJSON schema:\n{json.dumps(schema, ensure_ascii=True)}",
            },
        ],
        "stream": False,
        "format": schema,
        "options": {
            "temperature": 0,
        },
    }

    last_error = None

    for model_name in _ollama_models_for_task(task):
        try:
            parsed_response = _ollama_request(payload, model_name=model_name)
            raw_content = _extract_ollama_content(parsed_response)
            return json.dumps(_coerce_to_json_object(raw_content, schema))
        except Exception as exc:
            last_error = exc
            print(f"Ollama model '{model_name}' failed for {task}, trying next option.")

    if last_error:
        raise last_error

    raise RuntimeError("No Ollama model configured")


def _call_gemini_json(prompt: str, schema: dict) -> str:
    if time.time() < _gemini_backoff_until:
        raise RuntimeError(f"Gemini temporarily skipped: {_gemini_backoff_reason}")

    try:
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "temperature": 0,
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        )

        raw_content = getattr(response, "text", "") or ""
        return json.dumps(_coerce_to_json_object(raw_content, schema))
    except Exception as exc:
        message = str(exc)

        if "RESOURCE_EXHAUSTED" in message or "429" in message:
            _set_gemini_backoff(60, "quota exceeded", "Gemini quota exceeded, trying fallback provider for 60 seconds")
        elif "GEMINI_API_KEY is not set" in message:
            _set_gemini_backoff(3600, "API key missing", "Gemini API key is missing, trying fallback provider")
        else:
            print(f"Gemini call failed, trying fallback provider: {exc}")

        raise


def _call_ollama_text(prompt: str, task: str = "default") -> str:
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "Answer only from the provided context. If the context is insufficient, say that clearly.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "options": {
            "temperature": 0,
        },
    }

    last_error = None

    for model_name in _ollama_models_for_task(task):
        try:
            parsed_response = _ollama_request(payload, model_name=model_name)
            raw_content = _extract_ollama_content(parsed_response)
            return raw_content.strip()
        except Exception as exc:
            last_error = exc
            print(f"Ollama model '{model_name}' failed for {task}, trying next option.")

    if last_error:
        raise last_error

    raise RuntimeError("No Ollama model configured")


def _call_gemini_text(prompt: str) -> str:
    if time.time() < _gemini_backoff_until:
        raise RuntimeError(f"Gemini temporarily skipped: {_gemini_backoff_reason}")

    client = _get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "temperature": 0,
        },
    )

    raw_content = getattr(response, "text", "") or ""
    if not raw_content.strip():
        raise RuntimeError("Gemini returned an empty response")

    return raw_content.strip()


def llm_json_extract(prompt: str, schema: dict, task: str = "extraction") -> str:
    """
    Call the configured LLM provider and return a raw JSON string.
    Provider order:
    - `LLM_PROVIDER=ollama` or `USE_OLLAMA=true`: Ollama -> Gemini -> schema fallback
    - otherwise: Gemini -> Ollama -> schema fallback
    """
    last_error = None

    for provider in _provider_order():
        try:
            if provider == "ollama":
                return _call_ollama_json(prompt, schema, task=task)
            if provider == "gemini":
                return _call_gemini_json(prompt, schema)
        except Exception as exc:
            last_error = exc

    if last_error:
        print(f"All LLM providers unavailable, using schema fallback: {last_error}")

    return json.dumps(_fallback_from_schema(schema))


def llm_text_answer(prompt: str, task: str = "reasoning") -> str:
    last_error = None

    for provider in _provider_order():
        try:
            if provider == "ollama":
                return _call_ollama_text(prompt, task=task)
            if provider == "gemini":
                return _call_gemini_text(prompt)
        except Exception as exc:
            last_error = exc

    if last_error:
        print(f"All text-answer providers unavailable: {last_error}")

    return ""
