import inspect
from contextlib import ExitStack, contextmanager
from typing import Annotated, Callable, get_args, get_origin, get_type_hints, overload

from flask import Flask, g
from werkzeug.exceptions import InternalServerError

from flask_di.dependency import Depends


class DIFlask(Flask):
    """
    Flask subclass that provides FastAPI-style dependency injection using Annotated.

    Supports:
        - Annotated[T, Depends(...)]
        - FastAPI's classic default-value style: def view(x=Depends(fn))
        - Nested dependencies
        - Override system
        - Per-request caching (keyed by dependency identity, not name)
        - Generator dependencies (`yield`-based setup/teardown, e.g.
              def get_session():
                  with Session(engine) as session:
                      yield session
          )
        - Type-alias dependencies like:
              BackendAPIDep = Annotated[BackendAPI, Depends(get_backend_api)]
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependency_overrides = {}
        # Run teardown for generator-based dependencies whenever the
        # request (or, for resolve() used outside a view, the app
        # context) that owns them ends.
        self.teardown_request(self._close_dependency_exit_stack)
        self.teardown_appcontext(self._close_dependency_exit_stack)

    @overload
    def resolve[T](self, dependency: Depends[T]) -> T: ...
    @overload
    def resolve[T](self, dependency: Callable[..., T]) -> T: ...
    def resolve(self, dependency):
        dep_obj = dependency if isinstance(dependency, Depends) else Depends(dependency)
        return self._resolve_dependency(dep_obj)

    # -------------------------------------------------------------------------
    # Wrap view functions so DI happens automatically
    # -------------------------------------------------------------------------
    def add_url_rule(self, rule, *args, **kwargs):
        # Keyword "view_func"
        if "view_func" in kwargs and kwargs["view_func"]:
            kwargs["view_func"] = self._wrap_view(kwargs["view_func"])

        # Positional view_func (args[1])
        if len(args) >= 2 and args[1]:
            args = list(args)
            args[1] = self._wrap_view(args[1])
            return super().add_url_rule(rule, *args, **kwargs)

        return super().add_url_rule(rule, *args, **kwargs)

    # -------------------------------------------------------------------------
    # Build wrapper that injects Annotated dependencies
    # -------------------------------------------------------------------------
    def _wrap_view(self, view_func):
        sig = inspect.signature(view_func)
        type_hints = get_type_hints(view_func, include_extras=True)

        dependency_map = self._extract_dependencies(sig, type_hints)

        def wrapper(*args, **kwargs):
            injected = {}

            for param_name, depends_obj in dependency_map.items():
                injected[param_name] = self._resolve_dependency(depends_obj)

            return view_func(*args, **injected, **kwargs)

        wrapper.__name__ = view_func.__name__
        wrapper.__doc__ = view_func.__doc__
        return wrapper

    # -------------------------------------------------------------------------
    # Parse Annotated parameters and extract Depends objects
    # -------------------------------------------------------------------------
    def _extract_dependencies(self, sig, type_hints):
        dependency_map = {}

        for name, param in sig.parameters.items():
            annotation = type_hints.get(name)
            depends_obj = None

            # Annotated[T, Depends(...)] style
            if get_origin(annotation) is Annotated:
                ann_type, *metadata = get_args(annotation)
                depends_obj = next(
                    (m for m in metadata if isinstance(m, Depends)), None
                )

            # FastAPI's classic default-value style:
            #     def get_user(db=Depends(get_db)): ...
            if depends_obj is None and isinstance(param.default, Depends):
                depends_obj = param.default

            if depends_obj:
                dependency_map[name] = depends_obj

        return dependency_map

    # -------------------------------------------------------------------------
    # Per-request state: resolved-value cache and generator teardown stack
    # -------------------------------------------------------------------------
    def _dependency_cache(self) -> dict:
        """Cache of already-resolved dependency values for the current
        request/app context, keyed by the dependency callable itself
        (identity), not by its __name__ — so two different callables
        that happen to share a name never collide."""
        if not hasattr(g, "_di_cache"):
            g._di_cache = {}
        return g._di_cache

    def _dependency_exit_stack(self) -> ExitStack:
        """ExitStack that owns the teardown half (the code after
        `yield`) of any generator-based dependencies resolved during
        the current request/app context."""
        if not hasattr(g, "_di_exit_stack"):
            g._di_exit_stack = ExitStack()
        return g._di_exit_stack

    def _close_dependency_exit_stack(self, exc=None):
        stack = getattr(g, "_di_exit_stack", None)
        if stack is not None:
            stack.close()

    # -------------------------------------------------------------------------
    # Resolve a dependency function
    # -------------------------------------------------------------------------
    def _resolve_dependency(self, depends_obj: Depends):
        dep_func = depends_obj.dependency

        if dep_func is None:
            # Depends[T] was used as bare metadata (never called with a
            # factory), e.g. Annotated[int, Depends[int]] instead of
            # Annotated[int, Depends[int](my_factory)] / Depends(my_factory).
            raise InternalServerError(
                "Depends[T] has no factory function attached, so it can't "
                "be resolved. Use Depends(my_factory) or Depends[T](my_factory) "
                "instead of leaving Depends[T] bare inside Annotated[...]."
            )

        # Apply override if present
        if dep_func in self.dependency_overrides:
            dep_func = self.dependency_overrides[dep_func]

        # Request-scoped caching, keyed by callable identity
        cache = self._dependency_cache()
        if dep_func in cache:
            return cache[dep_func]

        # Collect nested dependencies
        sig = inspect.signature(dep_func)  # type: ignore
        type_hints = get_type_hints(dep_func, include_extras=True)

        kwargs = {}
        dependency_map = self._extract_dependencies(sig, type_hints)

        for name, nested_dep in dependency_map.items():
            kwargs[name] = self._resolve_dependency(nested_dep)

        # Execute dependency factory. Generator functions get FastAPI-style
        # setup/teardown: the code up to `yield` runs now, the yielded
        # value is what gets injected, and the code after `yield` runs
        # later as teardown (see _close_dependency_exit_stack).
        if inspect.isgeneratorfunction(dep_func):
            cm = contextmanager(dep_func)(**kwargs)
            value = self._dependency_exit_stack().enter_context(cm)
        else:
            value = dep_func(**kwargs)  # type: ignore

        # Cache result
        cache[dep_func] = value

        return value
