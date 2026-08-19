from app.auth.hashing import hash_phrase
from app.auth.store import SecretStore


def test_missing_file_is_not_configured(tmp_path):
    store = SecretStore(tmp_path / "secrets.yaml")
    assert store.is_configured() is False
    assert store.get_phrase_hash() is None


def test_round_trip_hash_storage(tmp_path):
    store = SecretStore(tmp_path / "secrets.yaml")
    hashed = hash_phrase("my phrase")

    store.set_phrase_hash(hashed)

    assert store.is_configured() is True
    assert store.get_phrase_hash() == hashed


def test_stored_file_never_contains_plaintext(tmp_path):
    store = SecretStore(tmp_path / "secrets.yaml")
    phrase = "definitely-do-not-leak-this"
    store.set_phrase_hash(hash_phrase(phrase))

    raw = store.path.read_text(encoding="utf-8")
    assert phrase not in raw


def test_overwriting_replaces_previous_hash(tmp_path):
    store = SecretStore(tmp_path / "secrets.yaml")
    store.set_phrase_hash(hash_phrase("first phrase"))
    first_hash = store.get_phrase_hash()

    store.set_phrase_hash(hash_phrase("second phrase"))
    second_hash = store.get_phrase_hash()

    assert first_hash != second_hash


def test_creates_parent_directories(tmp_path):
    nested = tmp_path / "nested" / "dir" / "secrets.yaml"
    store = SecretStore(nested)
    store.set_phrase_hash(hash_phrase("phrase"))
    assert nested.exists()