# v0.1.6
- Added `resolve()` method for cleaner call site, and it's a reusable escape hatch for any other Flask callback (error handlers, CLI commands, before_request, etc.) that also sits outside the view-wrapping path.
- Re-export DIFlask own `current_app` that's runtime-identical to Flask's but statically typed as `DIFlask`.
- Implemented tests (AI generated)
- Added support for generator-based dependencies (`yield`), matching FastAPI's setup/teardown pattern for resources like DB sessions. Teardown runs automatically after the request (or app context, for `app.resolve()`) ends, even if the view raised.
- Added support for FastAPI's classic default-value style dependency declaration (`def view(x=Depends(fn))`), as already shown in the README's first example. Previously only `Annotated[T, Depends(fn)]` was recognized.
- Fixed a cache-collision bug: the per-request dependency cache was keyed by the dependency function's `__name__`, so two different callables that happened to share a name (e.g. locally defined closures) would silently return each other's cached result. The cache is now keyed by the callable's identity instead.
- `Depends[T]` used as bare metadata (never called with a factory function) now raises a clear `InternalServerError` explaining the mistake, instead of an opaque `AttributeError: 'NoneType' object has no attribute '__name__'`.
- Removed `test_known_limitations.py` now that all three issues it pinned down are fixed; the corresponding tests were rewritten as normal positive tests in `test_injection.py`, `test_caching.py`, and `test_edge_cases.py`. Added `test_generator_dependencies.py` for the new `yield` support.

# v0.1.0
Core features implemented:
- Annotated[T, Depends(...)]
- Nested dependencies
- Override system
- Per-request caching
- Type-alias dependencies like:
    - DepName = Annotated[T, Depends(Callable)]