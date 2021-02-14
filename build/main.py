import os
from shutil import copyfile
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
        schema = model.schema_json(indent=2, by_alias=True)
        fp.write(schema)


def generate_schemas(models: Iterable[Type[BaseModel]], dir: str) -> None:
    for model in models:
        path = get_schema_path(model=model, dir=dir)
        generate_schema(model=model, path=path)


def generate_docs_index(readme_path: str, index_path: str) -> None:
    copyfile(index_path, readme_path)
    os.system("git reset")
    os.system(f"git add {readme_path}")
    os.system('git commit -m "README.md updated"')


def main(schemas_dir: str, readme_path: str, index_path: str) -> None:
    os.makedirs(schemas_dir, exist_ok=True)
    sources.register_all(PackageSource)
    steps.register_all(InstallStep)
    generate_schemas(models=(Manifest, PackageDefinition), dir=schemas_dir)
    generate_docs_index(readme_path=readme_path, index_path=index_path)


if __name__ == "__main__":
    main(
        schemas_dir="./docs/schemas",
        readme_path="README.md",
        index_path="./docs/index.md",
    )
