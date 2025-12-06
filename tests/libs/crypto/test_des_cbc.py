from __future__ import annotations

import random

import pytest
from Crypto.Cipher import DES as RefDES

from novelkit.libs.crypto.cipher import DES

_rng = random.Random(20251123)


def randbytes(n: int) -> bytes:
    return bytes(_rng.randrange(0, 256) for _ in range(n))


# ===========================================================
# Encryption matches reference
# ===========================================================


@pytest.mark.parametrize("nblocks", [0, 1, 2, 4, 8, 16])
def test_des_cbc_encrypt_matches_pycryptodome(nblocks):
    key = randbytes(8)
    iv = randbytes(8)
    pt = randbytes(8 * nblocks)

    my_cipher = DES.new(key, DES.MODE_CBC, iv=iv)
    ref_cipher = RefDES.new(key, RefDES.MODE_CBC, iv=iv)

    assert my_cipher.encrypt(pt) == ref_cipher.encrypt(pt)


# ===========================================================
# Decryption matches reference
# ===========================================================


@pytest.mark.parametrize("nblocks", [0, 1, 3, 5, 10])
def test_des_cbc_decrypt_matches_pycryptodome(nblocks):
    key = randbytes(8)
    iv = randbytes(8)
    pt = randbytes(8 * nblocks)

    ref_enc = RefDES.new(key, RefDES.MODE_CBC, iv=iv)
    ct = ref_enc.encrypt(pt)

    my_dec = DES.new(key, DES.MODE_CBC, iv=iv)
    assert my_dec.decrypt(ct) == pt


# ===========================================================
# Streaming CBC state behavior
# ===========================================================


def test_des_cbc_streaming_state_matches_pycryptodome():
    key = randbytes(8)
    iv = randbytes(8)
    pt = randbytes(8 * 6)

    # one-shot encryption (my)
    my1 = DES.new(key, DES.MODE_CBC, iv=iv)
    ct_oneshot = my1.encrypt(pt)

    # streaming encryption (my)
    my2 = DES.new(key, DES.MODE_CBC, iv=iv)
    ct_stream = my2.encrypt(pt[:16]) + my2.encrypt(pt[16:])
    assert ct_stream == ct_oneshot

    # cross-check streaming with reference
    ref = RefDES.new(key, RefDES.MODE_CBC, iv=iv)
    ct_ref = ref.encrypt(pt[:16]) + ref.encrypt(pt[16:])
    assert ct_stream == ct_ref


# ===========================================================
# Key / IV validation
# ===========================================================


def test_des_cbc_rejects_bad_key_size():
    iv = b"\x00" * 8
    with pytest.raises(ValueError):
        DES.new(b"", DES.MODE_CBC, iv=iv)
    with pytest.raises(ValueError):
        DES.new(b"\x00" * 7, DES.MODE_CBC, iv=iv)
    with pytest.raises(ValueError):
        DES.new(b"\x00" * 9, DES.MODE_CBC, iv=iv)


def test_des_cbc_rejects_bad_iv_size():
    key = b"\x00" * 8
    with pytest.raises(ValueError):
        DES.new(key, DES.MODE_CBC, iv=b"")
    with pytest.raises(ValueError):
        DES.new(key, DES.MODE_CBC, iv=b"\x00" * 7)
    with pytest.raises(ValueError):
        DES.new(key, DES.MODE_CBC, iv=b"\x00" * 9)


# ===========================================================
# Block alignment
# ===========================================================


def test_des_cbc_rejects_non_block_aligned_data():
    key = randbytes(8)
    iv = randbytes(8)
    my = DES.new(key, DES.MODE_CBC, iv=iv)

    with pytest.raises(ValueError):
        my.encrypt(b"\x00" * 7)
    with pytest.raises(ValueError):
        my.decrypt(b"\x00" * 15)


# ===========================================================
# Default IV behavior
# ===========================================================


def test_des_cbc_none_iv_defaults_to_zero_iv():
    key = randbytes(8)
    zero_iv = b"\x00" * 8
    pt = randbytes(8 * 4)

    my = DES.new(key, DES.MODE_CBC, iv=None)
    ref = RefDES.new(key, RefDES.MODE_CBC, iv=zero_iv)

    assert my.encrypt(pt) == ref.encrypt(pt)
