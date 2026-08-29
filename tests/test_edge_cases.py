import pytest

from flask_di import current_app


def test_resolve_returns_dependency_value(app):
    def get_db():
        return {"session": "db-session"}

    with app.test_request_context("/"):
        result = app.resolve(get_db)

    assert result == {"session": "db-session"}


def test_resolve_requires_an_application_context(app):
    def get_db():
        return "db"

    with pytest.raises(RuntimeError):
        app.resolve(get_db)


def test_resolve_respects_dependency_overrides(app):
    def get_db():
        return "real-db"

    app.dependency_overrides[get_db] = lambda: "fake-db"

    with app.test_request_context("/"):
        result = app.resolve(get_db)

    assert result == "fake-db"


def test_resolve_shares_cache_with_view_injection(app, client):
    """Calling app.resolve() for a dependency that a view also
    injects (directly or via nesting) should reuse the same
    per-request cache instead of recomputing it."""
    from typing import Annotated

    from flask_di import Depends

    calls = {"db": 0}

    def get_db():
        calls["db"] += 1
        return "db-session"

    DbDep = Annotated[str, Depends(get_db)]

    @app.route("/manual")
    def view(db: DbDep):
        manual = app.resolve(get_db)
        return f"{db}|{manual}|{calls['db']}"

    resp = client.get("/manual")
    assert resp.data == b"db-session|db-session|1"


def test_current_app_resolves_to_the_diflask_instance(app):
    with app.app_context():
        assert current_app._get_current_object() is app


def test_current_app_is_a_diflask_instance(app):
    with app.app_context():
        # current_app is DIFlask's own re-export, statically typed as
        # DIFlask rather than plain Flask.
        assert isinstance(current_app._get_current_object(), type(app))
