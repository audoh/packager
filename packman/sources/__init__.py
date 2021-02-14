from packman.models.package_source import BasePackageSource as _BasePackageSource
from packman.utils.union import BaseInstantiableUnion as _BaseInstantiableUnion

from .github import GitHubPackageSource  # noqa
from .link import LinkPackageSource  # noqa
from .spacedock import SpaceDockPackageSource  # noqa


def register_all(cls: _BaseInstantiableUnion[_BasePackageSource]) -> None:
    cls.register(GitHubPackageSource, SpaceDockPackageSource, LinkPackageSource)
