import inspect
from typing import Annotated, get_args, get_origin, get_type_hints

from flask import Flask, g

from flask_di.dependency import Depends


class DIFlask(Flask):
    """
    Flask subclass that provides FastAPI-style dependency injection using Annotated.

    Supports:
        - Annotated[T, Depends(...)]
        - Nested dependencies
        - Override system
        - Per-request caching
        - Type-alias dependencies like:
              BackendAPIDep = Annotated[BackendAPI, Depends(get_backend_api)]
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependency_overrides = {}

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

            # Must be Annotated[T, metadata...]
            if get_origin(annotation) is Annotated:
                ann_type, *metadata = get_args(annotation)
                depends_obj = next(
                    (m for m in metadata if isinstance(m, Depends)), None
                )
                if depends_obj:
                    dependency_map[name] = depends_obj

        return dependency_map

    # -------------------------------------------------------------------------
    # Resolve a dependency function
    # -------------------------------------------------------------------------
    def _resolve_dependency(self, depends_obj: Depends):
        dep_func = depends_obj.dependency

        # Apply override if present
        if dep_func in self.dependency_overrides:
            dep_func = self.dependency_overrides[dep_func]

        # Request-scoped caching
        cache_key = f"_dep_{dep_func.__name__}"  # type: ignore
        if hasattr(g, cache_key):
            return getattr(g, cache_key)

        # Collect nested dependencies
        sig = inspect.signature(dep_func)  # type: ignore
        type_hints = get_type_hints(dep_func, include_extras=True)

        kwargs = {}
        dependency_map = self._extract_dependencies(sig, type_hints)

        for name, nested_dep in dependency_map.items():
            kwargs[name] = self._resolve_dependency(nested_dep)

        # Execute dependency factory
        value = dep_func(**kwargs)  # type: ignore

        # Cache result
        setattr(g, cache_key, value)

        return value
