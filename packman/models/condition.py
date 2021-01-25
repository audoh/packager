from abc import ABC, abstractmethod

from packman.utils.union import create_union
from pydantic import BaseModel, Extra


class BaseCondition(BaseModel, ABC):
    @abstractmethod
    def evaluate(self) -> bool:
        ...

    class Config:
        extra = Extra.forbid


Condition = create_union(BaseCondition)
