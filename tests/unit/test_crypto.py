import pytest
from cryptography.fernet import Fernet

from infrastructure.crypto import TokenCrypto


def test_token_crypto_round_trip_and_ciphertext() -> None:
    crypto = TokenCrypto(Fernet.generate_key().decode())
    plaintext = "access-secret"
    ciphertext = crypto.encrypt(plaintext)
    assert ciphertext != plaintext
    assert plaintext not in ciphertext
    assert crypto.decrypt(ciphertext) == plaintext


def test_token_crypto_rejects_wrong_key() -> None:
    first = TokenCrypto(Fernet.generate_key().decode())
    second = TokenCrypto(Fernet.generate_key().decode())
    with pytest.raises(ValueError, match="decrypt"):
        second.decrypt(first.encrypt("secret"))


def test_token_crypto_rejects_invalid_key() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        TokenCrypto("invalid")
