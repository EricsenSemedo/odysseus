"""Shared per-model runtime settings for local model backends."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MODEL_RUNTIME_STATE = Path(os.environ.get("DATA_DIR", "data")) / "model_runtime.json"


def runtime_defaults() -> Dict[str, Any]:
    return {
        "gpu_layers": "auto",
        "keep_alive": "30m",
        "warm_on_select": True,
    }


def load_runtime_state() -> Dict[str, Any]:
    try:
        if MODEL_RUNTIME_STATE.exists():
            data = json.loads(MODEL_RUNTIME_STATE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        logger.warning("Failed to load model runtime state", exc_info=True)
    return {}


def runtime_settings_for(ep_id: str, model: str) -> Dict[str, Any]:
    state = load_runtime_state()
    settings = (
        state.get(str(ep_id), {})
        .get("models", {})
        .get(str(model), {})
    )
    out = runtime_defaults()
    if isinstance(settings, dict):
        out.update({k: v for k, v in settings.items() if k in out})
    return out


def runtime_settings_if_saved(ep_id: str, model: str) -> Optional[Dict[str, Any]]:
    state = load_runtime_state()
    settings = (
        state.get(str(ep_id), {})
        .get("models", {})
        .get(str(model), {})
    )
    if not isinstance(settings, dict):
        return None
    out = runtime_defaults()
    out.update({k: v for k, v in settings.items() if k in out})
    return out


def _normalize_base(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    for suffix in ("/models", "/chat/completions", "/completions", "/v1/messages"):
        if url.endswith(suffix):
            url = url[: -len(suffix)].rstrip("/")
    for suffix in ("/chat", "/tags", "/generate", "/show", "/ps"):
        if url.endswith("/api" + suffix):
            url = url[: -len(suffix)].rstrip("/")
    return url


def _origin(url: str) -> str:
    parsed = urlparse(url or "")
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def is_ollama_runtime_url(url: str) -> bool:
    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    return (
        host == "ollama"
        or host == "ollama.com"
        or host.endswith(".ollama.com")
        or parsed.port == 11434
        or path.startswith("/api/")
    )


def _endpoint_id_for_url(url: str) -> Optional[str]:
    from core.database import ModelEndpoint, SessionLocal

    norm = _normalize_base(url)
    origin = _origin(url)
    db = SessionLocal()
    try:
        rows = db.query(ModelEndpoint).filter(ModelEndpoint.is_enabled == True).all()
        for ep in rows:
            ep_base = _normalize_base(ep.base_url or "")
            if ep_base.rstrip("/") == norm.rstrip("/"):
                return ep.id
        if is_ollama_runtime_url(url):
            for ep in rows:
                if _origin(ep.base_url or "") == origin and is_ollama_runtime_url(ep.base_url or ""):
                    return ep.id
    except Exception:
        logger.debug("Could not resolve runtime endpoint for %s", url, exc_info=True)
    finally:
        db.close()
    return None


def runtime_settings_for_url(url: str, model: str) -> Optional[Dict[str, Any]]:
    if not is_ollama_runtime_url(url):
        return None
    ep_id = _endpoint_id_for_url(url)
    if not ep_id:
        return None
    return runtime_settings_if_saved(ep_id, model)


def apply_ollama_runtime_payload_options(payload: Dict[str, Any], url: str, model: str) -> bool:
    """Merge saved Ollama runtime options into a request payload.

    This is intentionally idempotent and cheap. It does not unload or reload a
    model; it only ensures that if Ollama has to load the model for this
    request, it receives the saved placement settings.
    """
    settings = runtime_settings_for_url(url, model)
    if not settings:
        return False

    keep_alive = settings.get("keep_alive")
    if keep_alive not in (None, ""):
        payload["keep_alive"] = keep_alive

    gpu_layers = settings.get("gpu_layers")
    if gpu_layers not in (None, "", "auto"):
        try:
            num_gpu = max(0, int(gpu_layers))
        except Exception:
            num_gpu = None
        if num_gpu is not None:
            options = payload.setdefault("options", {})
            if isinstance(options, dict):
                options["num_gpu"] = num_gpu
    return True
