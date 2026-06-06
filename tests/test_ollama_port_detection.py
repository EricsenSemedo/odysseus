"""Pin Ollama detection for URLs on port 11434.

Odysseus treats port 11434 as native Ollama even when users paste an
OpenAI-compatible /v1 URL from Ollama docs or proxies. That keeps local and
tailnet Ollama endpoints on the native /api/chat path where runtime options
and residency controls are available.
"""
import pytest

from src import llm_core, endpoint_resolver
from src.endpoint_resolver import build_chat_url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _stub_dns(monkeypatch):
    """Stub out resolve_url so tests are offline and deterministic."""
    monkeypatch.setattr(endpoint_resolver, "resolve_url", lambda u: u)


# ---------------------------------------------------------------------------
# _is_ollama_native_url: /v1 on port 11434 is native Ollama
# ---------------------------------------------------------------------------

class TestIsOllamaNativeUrlAcceptsPort11434V1Paths:
    """Port 11434 URLs are normalized onto Ollama's native API."""

    def test_localhost_v1(self):
        assert llm_core._is_ollama_native_url("http://localhost:11434/v1")

    def test_localhost_v1_trailing_slash(self):
        assert llm_core._is_ollama_native_url("http://localhost:11434/v1/")

    def test_localhost_v1_chat_completions(self):
        assert llm_core._is_ollama_native_url("http://localhost:11434/v1/chat/completions")

    def test_loopback_ip_v1(self):
        assert llm_core._is_ollama_native_url("http://127.0.0.1:11434/v1")

    def test_named_host_v1(self):
        assert llm_core._is_ollama_native_url("http://ollama:11434/v1")

    def test_lan_ip_v1(self):
        assert llm_core._is_ollama_native_url("http://192.168.1.100:11434/v1")

    def test_lan_ip_v1_chat_completions(self):
        assert llm_core._is_ollama_native_url("http://192.168.1.100:11434/v1/chat/completions")


# ---------------------------------------------------------------------------
# _is_ollama_native_url: /api paths and ollama.com ARE native Ollama
# ---------------------------------------------------------------------------

class TestIsOllamaNativeUrlAcceptsNativePaths:
    def test_localhost_api(self):
        assert llm_core._is_ollama_native_url("http://localhost:11434/api")

    def test_localhost_api_trailing_slash(self):
        assert llm_core._is_ollama_native_url("http://localhost:11434/api/")

    def test_localhost_api_chat(self):
        assert llm_core._is_ollama_native_url("http://localhost:11434/api/chat")

    def test_localhost_api_generate(self):
        assert llm_core._is_ollama_native_url("http://localhost:11434/api/generate")

    def test_ollama_com(self):
        assert llm_core._is_ollama_native_url("https://ollama.com")

    def test_ollama_com_api(self):
        assert llm_core._is_ollama_native_url("https://ollama.com/api")


# ---------------------------------------------------------------------------
# build_chat_url: port 11434 + /v1 → native /api/chat
# ---------------------------------------------------------------------------

class TestBuildChatUrlPort11434V1IsNativeOllama:
    def test_localhost_v1(self):
        assert build_chat_url("http://localhost:11434/v1") == "http://localhost:11434/api/chat"

    def test_loopback_ip_v1(self):
        assert build_chat_url("http://127.0.0.1:11434/v1") == "http://127.0.0.1:11434/api/chat"

    def test_lan_ip_v1(self):
        assert build_chat_url("http://192.168.1.100:11434/v1") == "http://192.168.1.100:11434/api/chat"


# ---------------------------------------------------------------------------
# build_chat_url: native Ollama /api → /api/chat
# ---------------------------------------------------------------------------

class TestBuildChatUrlNativeOllamaRoutesToApiChat:
    def test_localhost_api(self):
        assert build_chat_url("http://localhost:11434/api") == "http://localhost:11434/api/chat"

    def test_ollama_com(self):
        assert build_chat_url("https://ollama.com") == "https://ollama.com/api/chat"

    def test_ollama_com_api(self):
        assert build_chat_url("https://ollama.com/api") == "https://ollama.com/api/chat"
