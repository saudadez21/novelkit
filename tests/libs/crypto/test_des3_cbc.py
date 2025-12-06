from __future__ import annotations

import random

import pytest
from Crypto.Cipher import DES3 as RefDES3

from novelkit.libs.crypto.cipher import DES3

_rng = random.Random(20251123)


def randbytes(n: int) -> bytes:
    return bytes(_rng.randrange(0, 256) for _ in range(n))


def make_ref_compatible_key(key_len: int) -> bytes:
    """Generate DES3 key with correct parity so PyCryptodome accepts it."""
    assert key_len in (16, 24)
    for _ in range(1000):
        raw = randbytes(key_len)
        key = RefDES3.adjust_key_parity(raw)
        try:
            RefDES3.new(key, RefDES3.MODE_ECB)
            return key
        except ValueError:
            continue
    raise RuntimeError("Failed to generate a valid DES3 key")


# ===========================================================
# CBC encryption correctness
# ===========================================================


@pytest.mark.parametrize("key_len", [16, 24])
@pytest.mark.parametrize("nblocks", [0, 1, 2, 4, 8, 16])
def test_des3_cbc_encrypt_matches_pycryptodome(key_len, nblocks):
    key = make_ref_compatible_key(key_len)
    iv = randbytes(8)
    pt = randbytes(8 * nblocks)

    my = DES3.new(key, DES3.MODE_CBC, iv=iv)
    ref = RefDES3.new(key, RefDES3.MODE_CBC, iv=iv)

    assert my.encrypt(pt) == ref.encrypt(pt)


# ===========================================================
# CBC decryption correctness
# ===========================================================


@pytest.mark.parametrize("key_len", [16, 24])
@pytest.mark.parametrize("nblocks", [0, 1, 3, 5, 10])
def test_des3_cbc_decrypt_matches_pycryptodome(key_len, nblocks):
    key = make_ref_compatible_key(key_len)
    iv = randbytes(8)
    pt = randbytes(8 * nblocks)

    ref_enc = RefDES3.new(key, RefDES3.MODE_CBC, iv=iv)
    ct = ref_enc.encrypt(pt)

    my_dec = DES3.new(key, DES3.MODE_CBC, iv=iv)
    assert my_dec.decrypt(ct) == pt


# ===========================================================
# Streaming correctness
# ===========================================================


def test_des3_cbc_streaming_state_matches_pycryptodome():
    key = make_ref_compatible_key(24)
    iv = randbytes(8)
    pt = randbytes(8 * 6)

    # One-shot
    my1 = DES3.new(key, DES3.MODE_CBC, iv=iv)
    ct_oneshot = my1.encrypt(pt)

    # Streaming
    my2 = DES3.new(key, DES3.MODE_CBC, iv=iv)
    ct_stream = my2.encrypt(pt[:16]) + my2.encrypt(pt[16:])

    assert ct_stream == ct_oneshot

    # Reference streaming
    ref = RefDES3.new(key, RefDES3.MODE_CBC, iv=iv)
    ct_ref = ref.encrypt(pt[:16]) + ref.encrypt(pt[16:])
    assert ct_stream == ct_ref


# ===========================================================
# Key + IV validation
# ===========================================================


def test_des3_cbc_rejects_bad_key_size():
    iv = b"\x00" * 8
    with pytest.raises(ValueError):
        DES3.new(b"", DES3.MODE_CBC, iv=iv)
    with pytest.raises(ValueError):
        DES3.new(b"\x00" * 15, DES3.MODE_CBC, iv=iv)
    with pytest.raises(ValueError):
        DES3.new(b"\x00" * 17, DES3.MODE_CBC, iv=iv)
    with pytest.raises(ValueError):
        DES3.new(b"\x00" * 23, DES3.MODE_CBC, iv=iv)
    with pytest.raises(ValueError):
        DES3.new(b"\x00" * 25, DES3.MODE_CBC, iv=iv)


def test_des3_cbc_rejects_bad_iv_size():
    key = make_ref_compatible_key(16)
    with pytest.raises(ValueError):
        DES3.new(key, DES3.MODE_CBC, iv=b"")
    with pytest.raises(ValueError):
        DES3.new(key, DES3.MODE_CBC, iv=b"\x00" * 7)
    with pytest.raises(ValueError):
        DES3.new(key, DES3.MODE_CBC, iv=b"\x00" * 9)


# ===========================================================
# Block alignment rules
# ===========================================================


def test_des3_cbc_rejects_non_block_aligned_data():
    key = make_ref_compatible_key(24)
    iv = randbytes(8)
    my = DES3.new(key, DES3.MODE_CBC, iv=iv)

    with pytest.raises(ValueError):
        my.encrypt(b"\x00" * 7)

    with pytest.raises(ValueError):
        my.decrypt(b"\x00" * 15)


# ===========================================================
# iv=None should map to zero IV
# ===========================================================


def test_des3_cbc_none_iv_defaults_to_zero_iv():
    key = make_ref_compatible_key(24)
    zero_iv = b"\x00" * 8
    pt = randbytes(8 * 4)

    my = DES3.new(key, DES3.MODE_CBC, iv=None)
    ref = RefDES3.new(key, RefDES3.MODE_CBC, iv=zero_iv)

    assert my.encrypt(pt) == ref.encrypt(pt)
