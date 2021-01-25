import os
from glob import glob

from packman.models.condition import BaseCondition, condition
from pydantic import Field


@condition()
class Exists(BaseCondition):
    package_glob: str = Field(..., alias="has-path")

    def evaluate(self, package_path: str, root_dir: str) -> bool:
        return any(glob(os.path.join(package_path, self.package_glob), recursive=True))
