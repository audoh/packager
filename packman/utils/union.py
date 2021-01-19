from typing import Any, Callable, Dict, Protocol, Type

from pydantic import BaseModel


class DecoratorFactoryProtocol(Protocol):
    def __call__(self, type: str) -> Callable[[Type[BaseModel]], Type[BaseModel]]:
        ...


class DiscriminatedUnion:
    _members: Dict[str, Type[BaseModel]] = {}

    def __init__(self, cls: Type[BaseModel], attr: str) -> None:
        self.cls = cls
        self.attr = attr

    def __call__(self, **raw: Any) -> BaseModel:
        type = str(raw.get(self.attr, ""))
        cls = self._members.get(type, None)
        if not cls:
            raise ValueError(
                f"value is not a valid {self.cls.__name__}: {type}")
        return cls(**raw)

    def register(self, key: str, type: Type[BaseModel]) -> None:
        self._members[key] = type

    def decorator(self) -> DecoratorFactoryProtocol:
        def _decorator_factory(type: str) -> Callable[[Type[BaseModel]], Type[BaseModel]]:
            def _decorator(cls: Type[BaseModel]) -> Type[BaseModel]:
                self._members[type] = cls
                return cls
            return _decorator
        return _decorator_factory
