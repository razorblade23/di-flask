from typing import Callable, Optional


class Depends[T]:
    def __init__(
        self,
        dependency: Optional[Callable] = None,
        return_type: Optional[type] = None,
    ):
        self.dependency = dependency
        self.return_type = return_type

    def __class_getitem__(cls, return_type: type):
        # Enables Depends[T]
        return cls(dependency=None, return_type=return_type)

    def __call__(self, dependency: Callable):
        # Enables Depends[T](func)
        self.dependency = dependency
        return self
