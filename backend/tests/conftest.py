import pytest

from helpers import new_client


@pytest.fixture
def client():
    with new_client() as c:
        yield c


@pytest.fixture
def make_client():
    """Factory for clients with custom settings (e.g. a tiny rate limit)."""
    opened = []

    def factory(**overrides):
        tc = new_client(**overrides)
        opened.append(tc)
        return tc.__enter__()

    yield factory
    for tc in opened:
        tc.__exit__(None, None, None)
