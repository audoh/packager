from typing import List

from packman.models.condition import BaseCondition, Condition, condition
from pydantic import Field


@condition()
class Either(BaseCondition):
    """
    A condition which succeeds if any of its constituent conditions succeed.
    """

    conditions: List[Condition] = Field(..., alias="either")

    def evaluate(self, package_path: str, root_dir: str) -> bool:
        return any((cond.evaluate() for cond in self.conditions))
