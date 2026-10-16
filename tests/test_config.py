"""The secret key is made once and reused, so a restart does not log everyone out."""

from mymotoworks import config


def test_secret_key_is_created_once_and_reused(tmp_path):
    first = config.load_secret_key(str(tmp_path))
    second = config.load_secret_key(str(tmp_path))
    assert first == second
    assert len(first) == 64
    assert (tmp_path / "secret_key").exists()
