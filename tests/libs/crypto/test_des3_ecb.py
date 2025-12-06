from __future__ import annotations

import random

import pytest
from Crypto.Cipher import DES3 as RefDES3

from novelkit.libs.crypto.cipher import DES3

_rng = random.Random(20251123)


def randbytes(n: int) -> bytes:
    return bytes(_rng.randrange(0, 256) for _ in range(n))


def make_ref_compatible_key(key_len: int) -> bytes:
    """Generate a DES3 key with proper parity bits."""
    assert key_len in (16, 24)
    for _ in range(1000):
        raw = randbytes(key_len)
        key = RefDES3.adjust_key_parity(raw)
        try:
            RefDES3.new(key, RefDES3.MODE_ECB)
            return key
        except ValueError:
            continue
    raise RuntimeError("Failed to generate a valid DES3 key with correct parity")


# ===========================================================
# Encrypt correctness
# ===========================================================


@pytest.mark.parametrize("key_len", [16, 24])
@pytest.mark.parametrize("nblocks", [0, 1, 2, 4, 8, 16])
def test_des3_ecb_encrypt_matches_pycryptodome(key_len, nblocks):
    key = make_ref_compatible_key(key_len)
    pt = randbytes(8 * nblocks)

    my = DES3.new(key, DES3.MODE_ECB)
    ref = RefDES3.new(key, RefDES3.MODE_ECB)

    assert my.encrypt(pt) == ref.encrypt(pt)


# ===========================================================
# Decrypt correctness
# ===========================================================


@pytest.mark.parametrize("key_len", [16, 24])
@pytest.mark.parametrize("nblocks", [0, 1, 3, 5, 10])
def test_des3_ecb_decrypt_matches_pycryptodome(key_len, nblocks):
    key = make_ref_compatible_key(key_len)
    pt = randbytes(8 * nblocks)

    ref_enc = RefDES3.new(key, RefDES3.MODE_ECB)
    ct = ref_enc.encrypt(pt)

    my = DES3.new(key, DES3.MODE_ECB)
    assert my.decrypt(ct) == pt


# ===========================================================
# Streaming vs one-shot
# ===========================================================


def test_des3_ecb_streaming_equals_one_shot_and_matches_ref():
    key = make_ref_compatible_key(24)
    pt = randbytes(8 * 6)

    my1 = DES3.new(key, DES3.MODE_ECB)
    ct_one = my1.encrypt(pt)

    my2 = DES3.new(key, DES3.MODE_ECB)
    ct_stream = my2.encrypt(pt[:16]) + my2.encrypt(pt[16:])

    assert ct_stream == ct_one

    ref = RefDES3.new(key, RefDES3.MODE_ECB)
    ct_ref = ref.encrypt(pt[:16]) + ref.encrypt(pt[16:])
    assert ct_stream == ct_ref


# ===========================================================
# Multi-call correctness (statelessness)
# ===========================================================


def test_des3_ecb_multiple_calls_independent():
    key = make_ref_compatible_key(16)
    pt1 = randbytes(8 * 2)
    pt2 = randbytes(8 * 3)

    my = DES3.new(key, DES3.MODE_ECB)
    ref = RefDES3.new(key, RefDES3.MODE_ECB)

    assert my.encrypt(pt1) == ref.encrypt(pt1)
    assert my.encrypt(pt2) == ref.encrypt(pt2)


def test_des3_ecb_multiple_encrypt_calls_match_reference():
    key = make_ref_compatible_key(24)
    my = DES3.new(key, DES3.MODE_ECB)
    ref = RefDES3.new(key, RefDES3.MODE_ECB)

    for _ in range(10):
        pt = randbytes(8 * _rng.randrange(1, 6))
        assert my.encrypt(pt) == ref.encrypt(pt)


def test_des3_ecb_stateless_object_independence():
    key = make_ref_compatible_key(24)
    pt = randbytes(8 * 4)

    my1 = DES3.new(key, DES3.MODE_ECB)
    my2 = DES3.new(key, DES3.MODE_ECB)

    assert my1.encrypt(pt) == my2.encrypt(pt)


def test_des3_ecb_random_chunk_streaming_matches_reference():
    key = make_ref_compatible_key(24)
    pt = randbytes(8 * 10)

    my = DES3.new(key, DES3.MODE_ECB)
    ref = RefDES3.new(key, RefDES3.MODE_ECB)

    valid_splits = list(range(0, len(pt) + 1, 8))
    splits = sorted(random.sample(valid_splits[1:-1], 5))
    splits.append(len(pt))

    ct_my = b""
    ct_ref = b""

    start = 0
    for s in splits:
        ct_my += my.encrypt(pt[start:s])
        ct_ref += ref.encrypt(pt[start:s])
        start = s

    assert ct_my == ct_ref


# ===========================================================
# Validation
# ===========================================================


def test_des3_ecb_rejects_bad_key_size():
    with pytest.raises(ValueError):
        DES3.new(b"", DES3.MODE_ECB)
    with pytest.raises(ValueError):
        DES3.new(b"\x00" * 15, DES3.MODE_ECB)
    with pytest.raises(ValueError):
        DES3.new(b"\x00" * 17, DES3.MODE_ECB)
    with pytest.raises(ValueError):
        DES3.new(b"\x00" * 23, DES3.MODE_ECB)
    with pytest.raises(ValueError):
        DES3.new(b"\x00" * 25, DES3.MODE_ECB)


def test_des3_ecb_rejects_non_block_aligned_data():
    key = make_ref_compatible_key(24)
    my = DES3.new(key, DES3.MODE_ECB)

    with pytest.raises(ValueError):
        my.encrypt(b"\x00" * 7)

    with pytest.raises(ValueError):
        my.decrypt(b"\x00" * 15)
