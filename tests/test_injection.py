"""
Core injection behavior.

Flask-DI recognizes dependencies declared either via
`Annotated[T, Depends(fn)]` type hints, or via FastAPI's classic
default-value style `x=Depends(fn)` (the form used in the README's
first example).
"""

from typing import Annotated

from flask_di import Depends


def test_single_dependency_is_injected(app, client):
    def get_value():
        return 42

    ValueDep = Annotated[int, Depends(get_value)]

    @app.route("/value")
    def view(v: ValueDep):
        return str(v)

    resp = client.get("/value")
    assert resp.status_code == 200
    assert resp.data == b"42"


def test_multiple_independent_dependencies_in_one_route(app, client):
    def get_db():
        return "db"

    def get_config():
        return "cfg"

    DbDep = Annotated[str, Depends(get_db)]
    ConfigDep = Annotated[str, Depends(get_config)]

    @app.route("/multi")
    def view(db: DbDep, config: ConfigDep):
        return f"{db}-{config}"

    resp = client.get("/multi")
    assert resp.data == b"db-cfg"


def test_nested_dependency_is_resolved(app, client):
    def get_db():
        return {"session": "db-session"}

    DbDep = Annotated[dict, Depends(get_db)]

    def get_user(db: DbDep):
        return {"username": "alice", "db": db}

    UserDep = Annotated[dict, Depends(get_user)]

    @app.route("/user")
    def view(user: UserDep):
        return user

    resp = client.get("/user")
    assert resp.get_json() == {
        "username": "alice",
        "db": {"session": "db-session"},
    }


def test_deeply_nested_dependencies_three_levels(app, client):
    def level1():
        return 1

    Level1Dep = Annotated[int, Depends(level1)]

    def level2(a: Level1Dep):
        return a + 1

    Level2Dep = Annotated[int, Depends(level2)]

    def level3(b: Level2Dep):
        return b + 1

    Level3Dep = Annotated[int, Depends(level3)]

    @app.route("/chain")
    def view(c: Level3Dep):
        return str(c)

    resp = client.get("/chain")
    assert resp.data == b"3"


def test_dependency_alias_can_be_reused_across_routes(app, client):
    def get_value():
        return "shared"

    SharedDep = Annotated[str, Depends(get_value)]

    @app.route("/a")
    def view_a(v: SharedDep):
        return f"a:{v}"

    @app.route("/b")
    def view_b(v: SharedDep):
        return f"b:{v}"

    assert client.get("/a").data == b"a:shared"
    assert client.get("/b").data == b"b:shared"


def test_dependency_combined_with_url_variable(app, client):
    def get_value():
        return "injected"

    ValueDep = Annotated[str, Depends(get_value)]

    @app.route("/items/<int:item_id>")
    def view(item_id: int, v: ValueDep):
        return f"{item_id}-{v}"

    resp = client.get("/items/7")
    assert resp.data == b"7-injected"


def test_view_with_no_dependencies_is_unaffected(app, client):
    @app.route("/plain")
    def view():
        return "ok"

    resp = client.get("/plain")
    assert resp.data == b"ok"


def test_add_url_rule_with_positional_view_func_is_wrapped(app, client):
    """DIFlask.add_url_rule wraps view_func whether it arrives as a
    keyword argument or as the second positional argument."""

    def get_value():
        return 99

    ValueDep = Annotated[int, Depends(get_value)]

    def view(v: ValueDep):
        return str(v)

    app.add_url_rule("/positional", "positional_view", view)

    resp = client.get("/positional")
    assert resp.data == b"99"


def test_add_url_rule_with_keyword_view_func_is_wrapped(app, client):
    def get_value():
        return 100

    ValueDep = Annotated[int, Depends(get_value)]

    def view(v: ValueDep):
        return str(v)

    app.add_url_rule("/keyword", "keyword_view", view_func=view)

    resp = client.get("/keyword")
    assert resp.data == b"100"


def test_default_value_style_depends_is_injected(app, client):
    """FastAPI's classic default-value style also works:
    `def view(user=Depends(get_db))`, as shown in the README's first
    example.
    """

    def get_db():
        return {"session": "db-session"}

    @app.route("/legacy-style")
    def view(user=Depends(get_db)):
        return type(user).__name__

    resp = client.get("/legacy-style")
    assert resp.data == b"dict"


def test_default_value_style_supports_nested_dependencies(app, client):
    """Mirrors the README's Usage example end-to-end: a default-value
    style dependency (get_user) that itself depends on another
    default-value style dependency (get_db)."""

    def get_db():
        return {"session": "db-session"}

    def get_user(db=Depends(get_db)):
        return {"username": "alice", "db": db}

    @app.route("/info")
    def info(user=Depends(get_user)):
        return user

    resp = client.get("/info")
    assert resp.get_json() == {
        "username": "alice",
        "db": {"session": "db-session"},
    }


def test_default_value_style_can_mix_with_annotated_style(app, client):
    """A view can use Annotated[...] for one param and the bare
    default-value style for another in the same signature."""

    def get_db():
        return "db"

    def get_config():
        return "cfg"

    DbDep = Annotated[str, Depends(get_db)]

    @app.route("/mixed")
    def view(db: DbDep, config=Depends(get_config)):
        return f"{db}-{config}"

    resp = client.get("/mixed")
    assert resp.data == b"db-cfg"
