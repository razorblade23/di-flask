# v0.1.6
- Added `resolve()` method for cleaner call site, and it's a reusable escape hatch for any other Flask callback (error handlers, CLI commands, before_request, etc.) that also sits outside the view-wrapping path.
- Re-export DIFlask own `current_app` that's runtime-identical to Flask's but statically typed as `DIFlask`.
- Implemented tests (AI generated)

# v0.1.0
Core features implemented:
- Annotated[T, Depends(...)]
- Nested dependencies
- Override system
- Per-request caching
- Type-alias dependencies like:
    - DepName = Annotated[T, Depends(Callable)]