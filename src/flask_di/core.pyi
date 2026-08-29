from typing import Any, Callable, Dict, TypeVar

from flask import Flask

T = TypeVar("T")

class FlaskDI:
    app: Flask
    providers: Dict[type, Callable[..., Any]]

    def __init__(self, app: Flask | None = None) -> None: ...
    def init_app(self, app: Flask) -> None: ...
    def register(self, interface: type[T], provider: Callable[..., T]) -> None: ...
