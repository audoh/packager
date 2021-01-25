from typing import Callable, Dict, Generic, List, Optional, Set, Type, TypeVar, Union

from pydantic import ValidationError

T = TypeVar("T")


class BaseDiscriminatedUnion(Generic[T]):
    _base: Type[T]
    _members: Dict[str, Type[T]]
    _attr: str

    def __new__(self, *args, **kwargs) -> None:
        discriminator = kwargs[self._attr]
        return self._members[discriminator](*args, **kwargs)

    @classmethod
    def register(self, cls: Type[T], type: str) -> None:
        self._members[type] = cls

    @classmethod
    def member(self, type: str) -> Callable[[Type[T]], Type[T]]:
        def _decorator(cls: Type[T]) -> Type[T]:
            self.register(cls, type=type)
            return cls

        return _decorator

    @classmethod
    def decorator(cls) -> Callable[[str], Callable[[Type[T]], Type[T]]]:
        return cls.member


def create_discriminated_union(
    base: Type[T], *, discriminator: str
) -> Type[Union[BaseDiscriminatedUnion[T], T]]:
    class DiscriminatedUnion(base, BaseDiscriminatedUnion):
        _base = base
        _members = {}
        _attr = discriminator

    return DiscriminatedUnion


class BaseInstantiableUnion(Generic[T]):
    _base: Type[T]
    _members: Set[Type[T]]

    def __new__(self, *args, **kwargs) -> None:
        validation_errs: List[ValidationError] = []
        last_exc: Optional[Exception] = None
        for member in self._members:
            try:
                return member(*args, **kwargs)
            except ValidationError as exc:
                validation_errs.append(exc)
                continue
            except Exception as exc:
                last_exc = exc
                continue

        if validation_errs:
            raise ValidationError(
                [err for exc in validation_errs for err in exc.raw_errors],
                self,
            )

        raise last_exc or TypeError(
            "can't instantiate union base class with no concrete implementations"
        )

    @classmethod
    def register(cls, type: Type[T]) -> None:
        """
        Registers a new member of this union.
        """
        if not issubclass(type, cls._base):
            raise TypeError(
                f"{type.__name__} is not a subclass of {cls._base.__name__}"
            )
        cls._members.add(type)

    @classmethod
    def member(cls) -> Callable[[Type[T]], Type[T]]:
        def _decorator(member_cls: Type[T]) -> Type[T]:
            cls.register(member_cls)
            return member_cls

        return _decorator

    @classmethod
    def decorator(cls) -> Callable[..., Callable[[Type[T]], Type[T]]]:
        return cls.member


def create_union(base: Type[T]) -> Type[Union[BaseInstantiableUnion[T], T]]:
    class InstantiableUnion(base, BaseInstantiableUnion):
        _base: Type[T] = base
        _members: Set[Type[T]] = set()

    return InstantiableUnion
