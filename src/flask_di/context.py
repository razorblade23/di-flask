from typing import TYPE_CHECKING

from flask import current_app as _current_app

if TYPE_CHECKING:
    from .core import DIFlask
    current_app: DIFlask = _current_app
else:
    # Runtime — same LocalProxy Flask already uses
    current_app = _current_app
