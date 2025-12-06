from __future__ import annotations

import random

import pytest
from Crypto.Cipher import AES as RefAES

from novelkit.libs.crypto.cipher import AES

_rng = random.Random(20251123)


def randbytes(n: int) -> bytes:
    return bytes(_rng.randrange(0, 256) for _ in range(n))


# ===========================================================
# Encryption matches reference
# ===========================================================


@pytest.mark.parametrize("key_len", [16, 24, 32])
@pytest.mark.parametrize("nblocks", [0, 1, 2, 4, 8])
def test_aes_cbc_encrypt_matches_pycryptodome(key_len, nblocks):
    key = randbytes(key_len)
    iv = randbytes(16)
    pt = randbytes(16 * nblocks)

    my_cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    ref_cipher = RefAES.new(key, RefAES.MODE_CBC, iv=iv)

    assert my_cipher.encrypt(pt) == ref_cipher.encrypt(pt)


# ===========================================================
# Decryption matches reference
# ===========================================================


@pytest.mark.parametrize("key_len", [16, 24, 32])
@pytest.mark.parametrize("nblocks", [0, 1, 3, 5, 10])
def test_aes_cbc_decrypt_matches_pycryptodome(key_len, nblocks):
    key = randbytes(key_len)
    iv = randbytes(16)
    pt = randbytes(16 * nblocks)

    ref_enc = RefAES.new(key, RefAES.MODE_CBC, iv=iv)
    ct = ref_enc.encrypt(pt)

    my_dec = AES.new(key, AES.MODE_CBC, iv=iv)
    assert my_dec.decrypt(ct) == pt


# ===========================================================
# Streaming CBC encrypt behaves like reference CBC encrypt
# ===========================================================


def test_aes_cbc_streaming_state_matches_pycryptodome():
    key = randbytes(32)
    iv = randbytes(16)
    pt = randbytes(16 * 6)

    # one-shot (my)
    my1 = AES.new(key, AES.MODE_CBC, iv=iv)
    ct_one_shot = my1.encrypt(pt)

    # streaming (my)
    my2 = AES.new(key, AES.MODE_CBC, iv=iv)
    ct_stream = my2.encrypt(pt[:32]) + my2.encrypt(pt[32:])

    assert ct_stream == ct_one_shot

    # streaming reference (for safety)
    ref = RefAES.new(key, RefAES.MODE_CBC, iv=iv)
    ct_ref = ref.encrypt(pt[:32]) + ref.encrypt(pt[32:])
    assert ct_stream == ct_ref


# ===========================================================
# Bad key and IV validation
# ===========================================================


def test_aes_cbc_rejects_bad_key_size():
    with pytest.raises(ValueError):
        AES.new(b"", AES.MODE_CBC, iv=b"\x00" * 16)
    with pytest.raises(ValueError):
        AES.new(b"\x00" * 15, AES.MODE_CBC, iv=b"\x00" * 16)
    with pytest.raises(ValueError):
        AES.new(b"\x00" * 17, AES.MODE_CBC, iv=b"\x00" * 16)


def test_aes_cbc_rejects_bad_iv_size():
    key = b"\x00" * 16
    with pytest.raises(ValueError):
        AES.new(key, AES.MODE_CBC, iv=b"")
    with pytest.raises(ValueError):
        AES.new(key, AES.MODE_CBC, iv=b"\x00" * 15)
    with pytest.raises(ValueError):
        AES.new(key, AES.MODE_CBC, iv=b"\x00" * 17)


# ===========================================================
# Block-alignment validation
# ===========================================================


def test_aes_cbc_rejects_non_block_aligned_data():
    key = randbytes(16)
    iv = randbytes(16)
    my = AES.new(key, AES.MODE_CBC, iv=iv)

    with pytest.raises(ValueError):
        my.encrypt(b"\x00" * 15)
    with pytest.raises(ValueError):
        my.decrypt(b"\x00" * 31)


# ===========================================================
# Default IV behavior
# ===========================================================


def test_aes_cbc_none_iv_defaults_to_zero_iv():
    key = randbytes(16)
    zero_iv = b"\x00" * 16
    pt = randbytes(16 * 2)

    my = AES.new(key, AES.MODE_CBC, iv=None)
    ref = RefAES.new(key, RefAES.MODE_CBC, iv=zero_iv)

    assert my.encrypt(pt) == ref.encrypt(pt)
