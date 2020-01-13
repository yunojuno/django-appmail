import pkg_resources
from appmail import __version__


def test_version() -> None:
    """Check the pyproject.toml and __version__ match."""
    my_version = pkg_resources.get_distribution("appmail").version
    assert my_version == __version__
