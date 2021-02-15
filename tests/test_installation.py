import os

from packman import Packman


def test_core_works(packman: Packman) -> None:
    packman.install(name="mockpackage", version="v1.3.3.7")
