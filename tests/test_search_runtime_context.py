from datetime import datetime


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 6, 2, 22, 37, 0)
        if tz is not None:
            return value.replace(tzinfo=tz)
        return value


def _assert_runtime_search_context(module, monkeypatch):
    monkeypatch.setattr(module, "datetime", _FixedDateTime)
    monkeypatch.setattr(module, "_get_search_settings", lambda: {"search_provider": "searxng"})
    monkeypatch.setattr(module, "_get_result_count", lambda: 1)
    monkeypatch.setattr(
        module,
        "_call_provider",
        lambda provider, query, count, time_filter: [
            {
                "title": "Time and Date",
                "url": "https://example.test/time",
                "snippet": "Monday, June 1, 2026",
            }
        ],
    )
    monkeypatch.setattr(module, "rank_search_results", lambda query, results: results)
    monkeypatch.setattr(
        module,
        "fetch_webpage_content",
        lambda url, timeout=8, retry_attempt=0: {
            "success": True,
            "url": url,
            "title": "Stale page",
            "content": "The page says Monday, June 1, 2026.",
        },
    )

    context = module.comprehensive_web_search("What date did this search run?", max_pages=1)

    assert "Search generated at: 2026-06-02 22:37:00" in context
    assert "Current calendar date: 2026-06-02 (Tuesday); current year: 2026" in context
    assert "if the user asks when this search ran" in context
    assert "not dates found inside fetched pages or snippets" in context
    assert "do not infer the search-run date from source content" in context
    assert "Monday, June 1, 2026" in context


def test_chat_search_context_has_authoritative_runtime_timestamp(monkeypatch):
    from src.search import core

    _assert_runtime_search_context(core, monkeypatch)


def test_route_search_context_has_authoritative_runtime_timestamp(monkeypatch):
    from services.search import core

    _assert_runtime_search_context(core, monkeypatch)
