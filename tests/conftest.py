import pytest

from backend.database import Database


@pytest.fixture
def database(tmp_path):
    return Database(str(tmp_path / "test.db"))