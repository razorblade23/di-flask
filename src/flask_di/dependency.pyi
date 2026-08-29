from typing import Generic, Type, TypeVar

T = TypeVar("T")

class Provide(Generic[T]):
    dependency_type: Type[T]

    def __init__(self, dependency_type: Type[T]) -> None: ...
    def resolve(self) -> T: ...
