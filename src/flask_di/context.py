from typing import TYPE_CHECKING, cast

from flask import current_app as _current_app

if TYPE_CHECKING:
    from .core import DIFlask

    current_app: DIFlask = cast("DIFlask", _current_app)
else:
    current_app = _current_app
