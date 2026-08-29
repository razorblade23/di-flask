"""
These tests pin down behavior that looks unintended, so that:

  * if it's a real bug and someone fixes it, this test XPASSes loudly
    (strict=True turns an unexpected pass into a failure) instead of
    the fix going unnoticed, and
  * nobody is surprised by it in production before then.

Delete/rewrite the corresponding test as you fix each issue.
"""

from typing import Annotated

import pytest

from flask_di import Depends


def test_readme_default_value_style_is_not_currently_injected(app, client):
    """The README's very first example uses FastAPI's classic default-
    value style:

        def get_user(db=Depends(get_db)):
            ...

    But DIFlask._extract_dependencies() only looks at
    `Annotated[T, Depends(...)]` type hints — it never inspects
    `param.default`. So today, a bare `x=Depends(fn)` parameter is
    *not* resolved: the view receives the raw Depends instance itself
    instead of the dependency's return value.

    Either the README needs updating to show only the Annotated form,
    or add_url_rule's wrapper needs to also support default-value
    Depends(). Until one of those happens, this test documents what
    actually happens today.
    """

    def get_db():
        return {"session": "db-session"}

    @app.route("/legacy-style")
    def view(user=Depends(get_db)):
        return type(user).__name__

    resp = client.get("/legacy-style")
    # If this ever becomes "dict", the README-style injection has
    # started working and this test (and its docstring) should be
    # rewritten as a positive test in test_injection.py instead.
    assert resp.data == b"Depends"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Cache key in _resolve_dependency() is `f'_dep_{dep_func.__name__}'` "
        "— based on the function's __name__ only, not its identity. Two "
        "different dependency callables that happen to share a __name__ "
        "(e.g. locally defined closures, or same-named factories from "
        "different modules) collide in flask.g's per-request cache, so the "
        "second one silently returns the first one's cached result."
    ),
)
def test_dependencies_with_the_same_name_do_not_collide_in_cache(app, client):
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Depends[T] (subscript without calling it) is accepted as valid "
        "metadata inside Annotated[...] since it's a real Depends instance, "
        "but its .dependency is None. _resolve_dependency() doesn't guard "
        "against that, so it blows up with an unhelpful "
        "'NoneType has no attribute __name__' AttributeError instead of a "
        "clear error explaining that Depends[T] needs to be called with a "
        "factory, e.g. Depends[T](my_factory)."
    ),
)
def test_bare_depends_subscript_gives_clear_error(app, client):
    IntDep = Annotated[int, Depends[int]]

    @app.route("/bare")
    def view(v: IntDep):
        return str(v)

    resp = client.get("/bare")
    # Whatever the eventual behavior is, it shouldn't be a bare 500
    # with an AttributeError about NoneType.
    assert resp.status_code in (400, 422, 500)
    assert b"NoneType" not in resp.data
