from types import SimpleNamespace

from core.models import Session
from core.session_manager import SessionManager


class _Column:
    def __eq__(self, _other):
        return True

    def desc(self):
        return self


class _DbSessionModel:
    owner = _Column()
    archived = _Column()
    last_accessed = _Column()


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return self._rows


class _Db:
    def __init__(self, rows):
        self._rows = rows
        self.closed = False

    def query(self, _model):
        return _Query(self._rows)

    def close(self):
        self.closed = True


def _row(session_id, owner, name="Chat"):
    return SimpleNamespace(
        id=session_id,
        name=name,
        endpoint_url="http://model/v1/chat/completions",
        model="test-model",
        rag=False,
        archived=False,
        headers={},
        owner=owner,
        is_important=False,
        message_count=0,
        last_accessed=None,
    )


def test_get_sessions_for_user_uses_db_not_stale_cache(monkeypatch):
    stale = Session(
        id="stale",
        name="Stale cache entry",
        endpoint_url="http://model/v1/chat/completions",
        model="test-model",
        owner="jam",
    )
    manager = SessionManager.__new__(SessionManager)
    manager.sessions = {"stale": stale}

    db = _Db([_row("fresh", "jam", "Fresh DB entry")])
    monkeypatch.setattr("core.session_manager.SessionLocal", lambda: db)
    monkeypatch.setattr("core.session_manager.DbSession", _DbSessionModel)

    sessions = manager.get_sessions_for_user("jam")

    assert list(sessions) == ["fresh"]
    assert sessions["fresh"].owner == "jam"
    assert "fresh" in manager.sessions
    assert db.closed is True


def test_get_sessions_for_user_fallback_filters_cached_sessions(monkeypatch):
    matching = Session(
        id="cached",
        name="Cached",
        endpoint_url="http://model/v1/chat/completions",
        model="test-model",
        owner="alice",
    )
    other = Session(
        id="other",
        name="Other",
        endpoint_url="http://model/v1/chat/completions",
        model="test-model",
        owner="bob",
    )
    manager = SessionManager.__new__(SessionManager)
    manager.sessions = {"cached": matching, "other": other}

    monkeypatch.setattr("core.session_manager.SessionLocal", lambda: (_ for _ in ()).throw(RuntimeError("db down")))

    sessions = manager.get_sessions_for_user("alice")

    assert list(sessions) == ["cached"]
    assert sessions["cached"].owner == "alice"
