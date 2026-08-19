import pytest

from app.auth.hashing import hash_phrase, verify_phrase


def test_correct_phrase_verifies():
    phrase = "correct horse battery staple"
    hashed = hash_phrase(phrase)
    assert verify_phrase(phrase, hashed) is True


def test_incorrect_phrase_does_not_verify():
    hashed = hash_phrase("correct horse battery staple")
    assert verify_phrase("wrong phrase", hashed) is False


def test_hash_does_not_contain_plaintext_phrase():
    phrase = "super-secret-phrase-xyz"
    hashed = hash_phrase(phrase)
    assert phrase not in hashed


def test_same_phrase_produces_different_hashes_due_to_salt():
    phrase = "same phrase twice"
    assert hash_phrase(phrase) != hash_phrase(phrase)


def test_empty_phrase_raises_on_hash():
    with pytest.raises(ValueError):
        hash_phrase("")


def test_verify_against_empty_or_garbage_hash_is_false_not_raising():
    assert verify_phrase("anything", "") is False
    assert verify_phrase("anything", "not-a-real-argon2-hash") is False


def test_verify_empty_candidate_is_false():
    hashed = hash_phrase("real phrase")
    assert verify_phrase("", hashed) is False