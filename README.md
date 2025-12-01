# Flask-DI

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
pip install flask-di
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

## Disclaimer
This is my snippet of code that I use for my Flask project. 

Just wanted to share as its dead simple, lightweight and pure python.

## Contribution
You are free to contribute to the project in any way you want.

The goal of the project is to be on-par with FastAPI DI style. Please keep it simple, concise and with clear code comments.