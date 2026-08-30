"""
Generator-based dependencies (FastAPI-style `yield`), the common
pattern for resources that need setup *and* teardown, e.g.:

    def get_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

The code before `yield` runs when the dependency is first resolved,
the yielded value is what gets injected, and the code after `yield`
runs as teardown once the request (or app context, for app.resolve()
used outside a view) ends — regardless of whether the view raised.
"""

from typing import Annotated

import pytest

from flask_di import Depends


def test_generator_dependency_yields_value(app, client):
    def get_value():
        yield 42

    ValueDep = Annotated[int, Depends(get_value)]

    @app.route("/value")
    def view(v: ValueDep):
        return str(v)

    resp = client.get("/value")
    assert resp.data == b"42"


def test_generator_dependency_runs_teardown_after_response(app, client):
    events = []

    def get_session():
        events.append("setup")
        yield "session"
        events.append("teardown")

    SessionDep = Annotated[str, Depends(get_session)]

    @app.route("/session")
    def view(s: SessionDep):
        events.append("handler")
        return s

    resp = client.get("/session")
    assert resp.data == b"session"
    assert events == ["setup", "handler", "teardown"]


def test_generator_dependency_with_context_manager_closes_resource(app, client):
    """Mirrors the common SQLAlchemy pattern of
    `with Session(engine) as session: yield session`."""

    class FakeSession:
        def __init__(self):
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.closed = True

    holder = {}

    def get_session():
        with FakeSession() as session:
            holder["session"] = session
            yield session

    SessionDep = Annotated[FakeSession, Depends(get_session)]

    @app.route("/db")
    def view(session: SessionDep):
        return "closed" if session.closed else "open"

    resp = client.get("/db")
    assert resp.data == b"open"  # not yet closed while handling the request
    assert holder["session"].closed is True  # closed once teardown runs


def test_generator_dependency_is_still_cached_per_request(app, client):
    calls = {"n": 0}

    def get_session():
        calls["n"] += 1
        yield "session"

    SessionDep = Annotated[str, Depends(get_session)]

    def get_user(session: SessionDep):
        return f"user-{session}"

    UserDep = Annotated[str, Depends(get_user)]

    @app.route("/both")
    def view(session: SessionDep, user: UserDep):
        return f"{session}|{user}|{calls['n']}"

    resp = client.get("/both")
    assert resp.data == b"session|user-session|1"


def test_generator_dependency_teardown_runs_even_on_view_exception(app, client):
    events = []

    def get_session():
        events.append("setup")
        yield "session"
        events.append("teardown")

    SessionDep = Annotated[str, Depends(get_session)]

    @app.route("/boom")
    def view(s: SessionDep):
        raise ValueError("boom")

    # app.testing = True propagates unhandled exceptions to the test
    # client instead of turning them into a 500 response, but the
    # request's teardown (and therefore the dependency's teardown)
    # still runs first.
    with pytest.raises(ValueError):
        client.get("/boom")

    assert events == ["setup", "teardown"]


def test_generator_dependency_via_app_resolve(app):
    events = []

    def get_session():
        events.append("setup")
        yield "session"
        events.append("teardown")

    with app.test_request_context("/"):
        result = app.resolve(get_session)
        assert result == "session"
        assert events == ["setup"]

    # teardown_request fires once the request context is popped
    assert events == ["setup", "teardown"]


def test_generator_dependency_with_default_value_style(app, client):
    """Generator dependencies work with the default-value style too."""

    def get_session():
        yield "session"

    @app.route("/legacy-session")
    def view(s=Depends(get_session)):
        return s

    resp = client.get("/legacy-session")
    assert resp.data == b"session"


def test_generator_dependency_respects_overrides(app, client):
    def get_session():
        yield "real-session"

    def fake_session():
        yield "fake-session"

    SessionDep = Annotated[str, Depends(get_session)]

    @app.route("/session")
    def view(s: SessionDep):
        return s

    app.dependency_overrides[get_session] = fake_session

    resp = client.get("/session")
    assert resp.data == b"fake-session"
