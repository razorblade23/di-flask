from typing import Annotated

from flask_di import Depends, DIFlask


def dep1():
    return 42


IntDep = Annotated[int, Depends(dep1)]


def test_basic_injection():
    app = DIFlask(__name__)

    @app.route("/test")
    def test_route(v: IntDep):
        return str(v)

    client = app.test_client()
    resp = client.get("/test")
    assert resp.data == b"42"
