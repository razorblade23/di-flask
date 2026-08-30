# Flask-DI

![PyPI - Downloads](https://img.shields.io/pypi/dm/di-flask?style=for-the-badge&label=PyPi%20downloads&cacheSeconds=86400)

A minimal and clean FastAPI-style dependency injection system for Flask.

## Features

- FastAPI-style `Depends()`
- Automatic injection (no decorators required)
- Nested dependencies
- Override system for testing
- Per-request caching
- Pure Python and lightweight

## Installation

```bash
pip install di-flask
```

## Usage
> [!NOTE]
> For automatic injection of dependecies we need to wrap Flask class

```python
from flask_di import DIFlask, Depends

app = DIFlask(__name__)

def get_db():
    return {"session": "db-session"}

def get_user(db=Depends(get_db)):
    return {"username": "alice", "db": db}

@app.route("/info")
def info(user=Depends(get_user)):
    return user
```
> [!TIP]
> Flask-DI also supports `Annotated` type alias for declaring dependecies just like FastAPI does.
> 
> ```python
> from flask_di import DIFlask, Depends
> from typing import Annotated
> 
> app = DIFlask(__name__)
> 
> def get_db():
>     return {"session": "db-session"}
> 
> SessionDep = Annotated(dict, Depends(get_db))
> 
> def get_user(session: SessionDep):
>     return {"username": "alice", "session": session}
> 
> UserDep = Annotated(dict, Depends(get_user))
> 
> @app.route("/info")
> def info(user: UserDep):
>     return user
> ```

## Overrides
Flask-DI supports overrides for easy mocking and testing of dependacies.

```python
def override_db():
    return {"session": "test-db"}

app.dependency_overrides[get_db] = override_db
```

## Generator dependencies (setup / teardown)
Just like FastAPI, a dependency can be a generator function that `yield`s
its value once instead of `return`ing it. Whatever runs before the `yield`
is setup, the yielded value is what gets injected, and whatever runs after
the `yield` is teardown — run automatically once the request finishes
(even if the view raised). This is the common pattern for handing out a
database session that needs to be closed afterwards:

```python
from typing import Generator
from sqlalchemy.orm import Session

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

@app.route("/users")
def list_users(session: SessionDep):
    return [u.name for u in session.query(User).all()]
```

The default-value style (`def view(session=Depends(get_session))`) works
the same way. Teardown also runs for dependencies resolved manually via
`app.resolve(...)`, once the surrounding request or app context ends.

## Disclaimer
This is my snippet of code that I use for my Flask project. 

Just wanted to share as its dead simple, lightweight and pure python.

## Contribution
You are free to contribute to the project in any way you want.

The goal of the project is to be on-par with FastAPI DI style. Please keep it simple, concise and with clear code comments.