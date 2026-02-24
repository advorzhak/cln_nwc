"""Unit tests for NWC plugin Python modules"""

from __future__ import annotations

import time

import pytest
from coincurve import PrivateKey, PublicKey
from pyln.client import Millisatoshi

from lib.nip04 import decrypt, encrypt, get_ecdh_key, process_aes
from lib.nip47 import (
    NIP47URI,
    ErrorCodes,
    NotImplementedError,
    NWCError,
    ParameterValidationError,
    QuotaExceededError,
    UnauthorizedError,
    URIOptions,
)
from lib.utils import get_hex_pubkey


class TestUtils:
    """Test utility functions"""

    def test_get_hex_pubkey(self):
        """Test x-only pubkey derivation from private key"""
        # Create a known private key
        privkey = PrivateKey()
        privkey_hex = privkey.secret.hex()

        # Get the x-only pubkey
        x_only_pubkey = get_hex_pubkey(privkey_hex)

        # Verify it's valid hex and correct length (64 chars = 32 bytes)
        assert isinstance(x_only_pubkey, str)
        assert len(x_only_pubkey) == 64
        assert all(c in "0123456789abcdef" for c in x_only_pubkey)

        # Verify it matches the expected value
        expected_pubkey = (
            PublicKey.from_secret(bytes.fromhex(privkey_hex)).format().hex()[2:]
        )
        assert x_only_pubkey == expected_pubkey

    def test_get_hex_pubkey_consistency(self):
        """Test that same privkey always produces same pubkey"""
        # Use a valid private key (not all zeros)
        privkey = PrivateKey()
        privkey_hex = privkey.secret.hex()
        pubkey1 = get_hex_pubkey(privkey_hex)
        pubkey2 = get_hex_pubkey(privkey_hex)

        assert pubkey1 == pubkey2

    def test_get_hex_pubkey_invalid_input(self):
        """Test get_hex_pubkey with invalid input"""
        invalid_privkey = "not_a_valid_hex"
        with pytest.raises(ValueError):
            get_hex_pubkey(invalid_privkey)


class TestNIP04Encryption:
    """Test NIP04 encryption/decryption"""

    def test_ecdh_key_derivation(self):
        """Test ECDH key exchange"""
        # Create two keypairs
        privkey1 = PrivateKey()
        privkey2 = PrivateKey()

        pubkey2_hex = get_hex_pubkey(privkey2.secret.hex())

        # Derive shared key
        shared_key = get_ecdh_key(privkey1.secret.hex(), pubkey2_hex)

        # Verify it's 32 bytes
        assert isinstance(shared_key, bytes)
        assert len(shared_key) == 32

    def test_ecdh_key_mutual(self):
        """Test that both parties derive same shared key"""
        # Create two keypairs
        privkey1 = PrivateKey()
        privkey2 = PrivateKey()

        pubkey1_hex = get_hex_pubkey(privkey1.secret.hex())
        pubkey2_hex = get_hex_pubkey(privkey2.secret.hex())

        # Person 1 derives shared key with person 2's pubkey
        shared_key1 = get_ecdh_key(privkey1.secret.hex(), pubkey2_hex)

        # Person 2 derives shared key with person 1's pubkey
        shared_key2 = get_ecdh_key(privkey2.secret.hex(), pubkey1_hex)

        # Both should have same shared key
        assert shared_key1 == shared_key2

    def test_aes_encrypt_decrypt_roundtrip(self):
        """Test AES encryption/decryption"""
        # Create two keypairs for ECDH
        privkey1 = PrivateKey()
        privkey1_hex = privkey1.secret.hex()
        privkey2 = PrivateKey()
        pubkey2_hex = get_hex_pubkey(privkey2.secret.hex())

        # Use plaintext that's exactly 16 bytes
        plaintext = "Exactly16BytesPL"

        # Encrypt using high-level function
        encrypted = encrypt(privkey1_hex, pubkey2_hex, plaintext)
        assert encrypted != plaintext

        # Decrypt using high-level function
        decrypted = decrypt(privkey1_hex, pubkey2_hex, encrypted)
        assert decrypted == plaintext

    def test_aes_different_keys_different_ciphertext(self):
        """Test that different keys produce different ciphertexts"""
        import os

        # Use plaintext that's exactly 16 bytes (multiple of AES block size)
        plaintext = b"Exactly16BytesPL"
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        iv = os.urandom(16)

        ciphertext1 = process_aes(plaintext, key1, iv, "encrypt")
        ciphertext2 = process_aes(plaintext, key2, iv, "encrypt")

        assert ciphertext1 != ciphertext2

    def test_nip04_encrypt_decrypt(self):
        """Test full NIP04 encryption/decryption"""
        privkey1 = PrivateKey()
        privkey2 = PrivateKey()

        privkey1_hex = privkey1.secret.hex()
        pubkey2_hex = get_hex_pubkey(privkey2.secret.hex())

        message = "Secret NWC message"

        # Encrypt from privkey1 to pubkey2
        encrypted = encrypt(privkey1_hex, pubkey2_hex, message)

        # Should be base64 encoded with format: base64_iv?base64_ciphertext
        assert "?" in encrypted
        parts = encrypted.split("?")
        assert len(parts) == 2

        # Decrypt with privkey2
        privkey2_hex = privkey2.secret.hex()
        pubkey1_hex = get_hex_pubkey(privkey1.secret.hex())

        decrypted = decrypt(privkey2_hex, pubkey1_hex, encrypted)
        assert decrypted == message


class TestNIP47URI:
    """Test NIP47URI class"""

    def test_construct_wallet_connect_url(self):
        """Test NWC URL construction"""
        options = URIOptions(
            relay_url="wss://relay.example.com",
            secret="abc123def456",
            wallet_pubkey="node_pubkey_hex",
        )

        url = NIP47URI.construct_wallet_connect_url(options)

        assert url.startswith("nostr+walletconnect://")
        assert "node_pubkey_hex" in url
        assert "relay=wss://relay.example.com" in url
        assert "secret=abc123def456" in url

    def test_construct_url_missing_relay(self):
        """Test URL construction fails with missing relay"""
        options = URIOptions(secret="abc123", wallet_pubkey="node_pubkey")

        with pytest.raises(ValueError, match="relay url is required"):
            NIP47URI.construct_wallet_connect_url(options)

    def test_construct_url_missing_secret(self):
        """Test URL construction fails with missing secret"""
        options = URIOptions(relay_url="wss://relay.com", wallet_pubkey="node_pubkey")

        with pytest.raises(ValueError, match="secret is require"):
            NIP47URI.construct_wallet_connect_url(options)

    def test_construct_url_missing_wallet_pubkey(self):
        """Test URL construction fails with missing wallet pubkey"""
        options = URIOptions(relay_url="wss://relay.com", secret="abc123")

        with pytest.raises(ValueError, match="wallet pubkey is required"):
            NIP47URI.construct_wallet_connect_url(options)

    def test_parse_wallet_connect_url(self):
        """Test parsing NWC URL"""
        url = (
            "nostr+walletconnect://node_pubkey123?relay=wss://relay.com&secret=mysecret"
        )

        options = NIP47URI.parse_wallet_connect_url(url)

        assert options.wallet_pubkey == "node_pubkey123"
        assert options.relay_url == "wss://relay.com"
        assert options.secret == "mysecret"

    def test_nip47uri_initialization_from_secret(self):
        """Test NIP47URI initialization and pubkey derivation"""
        privkey = PrivateKey()
        secret = privkey.secret.hex()

        options = URIOptions(
            relay_url="wss://relay.com",
            secret=secret,
            wallet_pubkey="node_pubkey",
        )

        nip47_uri = NIP47URI(options=options)

        # Pubkey should be derived from secret
        expected_pubkey = (
            PublicKey.from_secret(bytes.fromhex(secret)).format().hex()[2:]
        )
        assert nip47_uri.pubkey == expected_pubkey
        assert nip47_uri.secret == secret
        assert nip47_uri.relay_url == "wss://relay.com"
        assert nip47_uri.wallet_pubkey == "node_pubkey"

    def test_nip47uri_datastore_key(self):
        """Test datastore key generation"""
        privkey = PrivateKey()
        secret = privkey.secret.hex()

        options = URIOptions(
            relay_url="wss://relay.com",
            secret=secret,
            wallet_pubkey="node_pubkey",
        )

        nip47_uri = NIP47URI(options=options)
        key = nip47_uri.datastore_key

        assert isinstance(key, list)
        assert key[0] == "nwc"
        assert key[1] == "uri"
        assert key[2] == nip47_uri.pubkey

    def test_nip47uri_expired_no_expiry(self):
        """Test expired() when no expiry is set"""
        privkey = PrivateKey()
        options = URIOptions(
            relay_url="wss://relay.com",
            secret=privkey.secret.hex(),
            wallet_pubkey="node_pubkey",
            expiry_unix=None,
        )

        nip47_uri = NIP47URI(options=options)
        assert nip47_uri.expired() is False

    def test_nip47uri_not_expired(self):
        """Test expired() when expiry is in future"""
        privkey = PrivateKey()
        future_expiry = int(time.time()) + 3600  # 1 hour from now

        options = URIOptions(
            relay_url="wss://relay.com",
            secret=privkey.secret.hex(),
            wallet_pubkey="node_pubkey",
            expiry_unix=future_expiry,
        )

        nip47_uri = NIP47URI(options=options)
        assert nip47_uri.expired() is False

    def test_nip47uri_is_expired(self):
        """Test expired() when expiry is in past"""
        privkey = PrivateKey()
        past_expiry = int(time.time()) - 3600  # 1 hour ago

        options = URIOptions(
            relay_url="wss://relay.com",
            secret=privkey.secret.hex(),
            wallet_pubkey="node_pubkey",
            expiry_unix=past_expiry,
        )

        nip47_uri = NIP47URI(options=options)
        assert nip47_uri.expired() is True

    def test_nip47uri_remaining_budget(self):
        """Test remaining_budget calculation"""
        privkey = PrivateKey()
        budget = Millisatoshi(100000)
        spent = Millisatoshi(30000)

        options = URIOptions(
            relay_url="wss://relay.com",
            secret=privkey.secret.hex(),
            wallet_pubkey="node_pubkey",
            budget_msat=budget,
            spent_msat=spent,
        )

        nip47_uri = NIP47URI(options=options)
        remaining = nip47_uri.remaining_budget

        assert remaining == Millisatoshi(70000)

    def test_nip47uri_remaining_budget_under_limit(self):
        """Test remaining budget when under limit"""
        privkey = PrivateKey()
        budget = Millisatoshi(1000000)
        spent = Millisatoshi(500000)

        options = URIOptions(
            relay_url="wss://relay.example.com",
            secret=privkey.secret.hex(),
            wallet_pubkey="node_pubkey",
            budget_msat=budget,
            spent_msat=spent,
        )

        nip47_uri = NIP47URI(options=options)

        # Remaining should be budget - spent
        remaining = nip47_uri.remaining_budget
        expected = budget - spent
        assert remaining == expected


class TestNWCErrors:
    """Test error classes"""

    def test_nwc_error(self):
        """Test NWCError base class"""
        error = NWCError(ErrorCodes.OTHER, "Test error")
        assert error.code == ErrorCodes.OTHER
        assert error.message == "Test error"

    def test_parameter_validation_error(self):
        """Test ParameterValidationError"""
        error = ParameterValidationError("amount")
        assert error.code == ErrorCodes.OTHER
        assert "amount" in error.message
        assert "missing parameter" in error.message

    def test_quota_exceeded_error(self):
        """Test QuotaExceededError"""
        error = QuotaExceededError()
        assert error.code == ErrorCodes.QUOTA_EXCEEDED

    def test_unauthorized_error(self):
        """Test UnauthorizedError"""
        error = UnauthorizedError("Invalid token")
        assert error.code == ErrorCodes.UNAUTHORIZED
        assert error.message == "Invalid token"

    def test_not_implemented_error(self):
        """Test NotImplementedError"""
        error = NotImplementedError("Method not supported")
        assert error.code == ErrorCodes.NOT_IMPLEMENTED
        assert error.message == "Method not supported"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
