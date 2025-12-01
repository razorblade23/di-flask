# v0.1.0
Core features implemented:
- Annotated[T, Depends(...)]
- Nested dependencies
- Override system
- Per-request caching
- Type-alias dependencies like:
    - DepName = Annotated[T, Depends(Callable)]