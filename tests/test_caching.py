from typing import Annotated

from flask_di import Depends


def test_dependency_is_called_once_per_request_even_when_reused(app, client):
    """The same dependency used directly *and* inside a nested
    dependency should only execute once per request (result cached
    on flask.g)."""
    calls = {"db": 0}

    def get_db():
        calls["db"] += 1
        return "db-session"

    DbDep = Annotated[str, Depends(get_db)]

    def get_user(db: DbDep):
        return f"user-{db}"

    UserDep = Annotated[str, Depends(get_user)]

    @app.route("/both")
    def view(db: DbDep, user: UserDep):
        return f"{db}|{user}|{calls['db']}"

    resp = client.get("/both")
    assert resp.data == b"db-session|user-db-session|1"


def test_cache_does_not_persist_across_requests(app, client):
    calls = {"db": 0}

    def get_db():
        calls["db"] += 1
        return calls["db"]

    DbDep = Annotated[int, Depends(get_db)]

    @app.route("/count")
    def view(db: DbDep):
        return str(db)

    first = client.get("/count")
    second = client.get("/count")

    assert first.data == b"1"
    assert second.data == b"2"


def test_two_different_dependencies_are_cached_independently(app, client):
    calls = {"a": 0, "b": 0}

    def get_a():
        calls["a"] += 1
        return "a"

    def get_b():
        calls["b"] += 1
        return "b"

    ADep = Annotated[str, Depends(get_a)]
    BDep = Annotated[str, Depends(get_b)]

    @app.route("/ab")
    def view(a: ADep, b: BDep, a2: ADep):
        # a2 reuses the same dependency function as `a` — should hit cache
        return f"{a}{b}{a2}|{calls['a']}|{calls['b']}"

    resp = client.get("/ab")
    assert resp.data == b"aba|1|1"


def test_dependencies_with_the_same_name_do_not_collide_in_cache(app, client):
    """The per-request cache is keyed by the dependency callable's
    identity, not its __name__, so two different callables that
    happen to share a __name__ (e.g. locally defined closures, or
    same-named factories from different modules) don't collide."""

    def make_dep(value):
        def dep():
            return value

        dep.__name__ = "dep"  # deliberately identical across both
        return dep

    dep_a = make_dep("A")
    dep_b = make_dep("B")

    ADep = Annotated[str, Depends(dep_a)]
    BDep = Annotated[str, Depends(dep_b)]

    @app.route("/collide")
    def view(a: ADep, b: BDep):
        return f"{a}-{b}"

    resp = client.get("/collide")
    assert resp.data == b"A-B"
