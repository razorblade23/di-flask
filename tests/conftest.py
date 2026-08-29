import pytest

from flask_di import DIFlask


@pytest.fixture
def app():
    """A fresh DIFlask app for each test.

    Routes/dependencies should be registered inside the test itself,
    since every test typically needs a different wiring.
    """
    app = DIFlask(__name__)
    app.testing = True
    return app


@pytest.fixture
def client(app):
    """Test client bound to the `app` fixture.

    Safe to grab before routes are added — Flask only locks the app
    down after the *first request* is dispatched, not on client
    creation.
    """
    return app.test_client()
