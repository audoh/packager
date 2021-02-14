from packman.models.install_step import BaseInstallStep as _BaseInstallStep
from packman.utils.union import BaseInstantiableUnion as _BaseInstantiableUnion

from .copy_folder import CopyFolderInstallStep  # noqa


def register_all(cls: _BaseInstantiableUnion[_BaseInstallStep]) -> None:
    cls.register(CopyFolderInstallStep)
