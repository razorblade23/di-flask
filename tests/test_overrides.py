from typing import Annotated

from flask_di import Depends, DIFlask


def test_override_replaces_dependency_result(app, client):
    def get_db():
        return "real-db"

    DbDep = Annotated[str, Depends(get_db)]

    @app.route("/db")
    def view(db: DbDep):
        return db

    app.dependency_overrides[get_db] = lambda: "test-db"

    resp = client.get("/db")
    assert resp.data == b"test-db"


def test_override_applies_inside_nested_dependency(app, client):
    def get_db():
        return "real-db"

    DbDep = Annotated[str, Depends(get_db)]

    def get_user(db: DbDep):
        return f"user-using-{db}"

    UserDep = Annotated[str, Depends(get_user)]

    @app.route("/user")
    def view(user: UserDep):
        return user

    app.dependency_overrides[get_db] = lambda: "fake-db"

    resp = client.get("/user")
    assert resp.data == b"user-using-fake-db"


def test_without_override_real_dependency_is_used(app, client):
    def get_db():
        return "real-db"

    DbDep = Annotated[str, Depends(get_db)]

    @app.route("/db")
    def view(db: DbDep):
        return db

    resp = client.get("/db")
    assert resp.data == b"real-db"


def test_removing_override_reverts_to_original(app, client):
    def get_db():
        return "real-db"

    DbDep = Annotated[str, Depends(get_db)]

    @app.route("/db")
    def view(db: DbDep):
        return db

    app.dependency_overrides[get_db] = lambda: "test-db"
    assert client.get("/db").data == b"test-db"

    del app.dependency_overrides[get_db]
    assert client.get("/db").data == b"real-db"


def test_override_only_affects_the_targeted_dependency(app, client):
    def get_db():
        return "db"

    def get_config():
        return "config"

    DbDep = Annotated[str, Depends(get_db)]
    ConfigDep = Annotated[str, Depends(get_config)]

    @app.route("/multi")
    def view(db: DbDep, config: ConfigDep):
        return f"{db}-{config}"

    app.dependency_overrides[get_db] = lambda: "overridden-db"

    resp = client.get("/multi")
    assert resp.data == b"overridden-db-config"


def test_overrides_are_isolated_per_app_instance():
    def get_value():
        return "original"

    ValueDep = Annotated[str, Depends(get_value)]

    app_a = DIFlask("app_a")
    app_b = DIFlask("app_b")

    @app_a.route("/v")
    def view_a(v: ValueDep):
        return v

    @app_b.route("/v")
    def view_b(v: ValueDep):
        return v

    app_a.dependency_overrides[get_value] = lambda: "overridden-in-a"

    assert app_a.test_client().get("/v").data == b"overridden-in-a"
    # app_b shares the same dependency function but has its own
    # dependency_overrides dict, so it must be unaffected.
    assert app_b.test_client().get("/v").data == b"original"
