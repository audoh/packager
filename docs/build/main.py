import os
from typing import Iterable, Type

from packman import InstallStep, PackageSource, sources, steps
from packman.models.manifest import Manifest
from packman.models.package_definition import PackageDefinition
from pydantic import BaseModel


def get_schema_path(model: Type[BaseModel], dir: str) -> str:
    camel_case = model.__name__
    result = "".join(c if c.islower() else f"_{c.lower()}" for c in camel_case)

    return os.path.join(dir, f"{result[1:]}.json")


def generate_schema(model: Type[BaseModel], path: str) -> None:
    with open(path, "w") as fp:
        schema = model.schema_json(indent=2)
        fp.write(schema)


def generate_schemas(models: Iterable[Type[BaseModel]], dir: str) -> None:
    for model in models:
        path = get_schema_path(model=model, dir=dir)
        generate_schema(model=model, path=path)


def main(docs_dir: str) -> None:
    sources.register_all(PackageSource)
    steps.register_all(InstallStep)
    generate_schemas([Manifest, PackageDefinition], docs_dir)


if __name__ == "__main__":
    main("./docs")
