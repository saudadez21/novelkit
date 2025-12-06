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
def test_des_ecb_encrypt_matches_pycryptodome(nblocks):
    key = randbytes(8)
    pt = randbytes(8 * nblocks)

    my = DES.new(key, DES.MODE_ECB)
    ref = RefDES.new(key, RefDES.MODE_ECB)

    assert my.encrypt(pt) == ref.encrypt(pt)


# ===========================================================
# Decryption matches reference
# ===========================================================


@pytest.mark.parametrize("nblocks", [0, 1, 3, 5, 10])
def test_des_ecb_decrypt_matches_pycryptodome(nblocks):
    key = randbytes(8)
    pt = randbytes(8 * nblocks)

    ref_enc = RefDES.new(key, RefDES.MODE_ECB)
    ct = ref_enc.encrypt(pt)

    my = DES.new(key, DES.MODE_ECB)
    assert my.decrypt(ct) == pt


# ===========================================================
# Streaming vs one-shot
# ===========================================================


def test_des_ecb_streaming_equals_one_shot_and_matches_ref():
    key = randbytes(8)
    pt = randbytes(8 * 6)

    my1 = DES.new(key, DES.MODE_ECB)
    ct_one = my1.encrypt(pt)

    my2 = DES.new(key, DES.MODE_ECB)
    ct_stream = my2.encrypt(pt[:16]) + my2.encrypt(pt[16:])

    assert ct_stream == ct_one

    ref = RefDES.new(key, RefDES.MODE_ECB)
    ct_ref = ref.encrypt(pt[:16]) + ref.encrypt(pt[16:])
    assert ct_stream == ct_ref


# ===========================================================
# Multi-call correctness
# ===========================================================


def test_des_ecb_multiple_calls_independent():
    key = randbytes(8)
    pt1 = randbytes(8 * 2)
    pt2 = randbytes(8 * 3)

    my = DES.new(key, DES.MODE_ECB)
    ref = RefDES.new(key, RefDES.MODE_ECB)

    assert my.encrypt(pt1) == ref.encrypt(pt1)
    assert my.encrypt(pt2) == ref.encrypt(pt2)


def test_des_ecb_multiple_encrypt_calls_match_reference():
    key = randbytes(8)
    my = DES.new(key, DES.MODE_ECB)
    ref = RefDES.new(key, RefDES.MODE_ECB)

    for _ in range(10):
        pt = randbytes(8 * _rng.randrange(1, 6))
        assert my.encrypt(pt) == ref.encrypt(pt)


def test_des_ecb_stateless_object_independence():
    key = randbytes(8)
    pt = randbytes(8 * 4)

    my1 = DES.new(key, DES.MODE_ECB)
    my2 = DES.new(key, DES.MODE_ECB)

    assert my1.encrypt(pt) == my2.encrypt(pt)


def test_des_ecb_random_chunk_streaming_matches_reference():
    key = randbytes(8)
    pt = randbytes(8 * 8)

    my = DES.new(key, DES.MODE_ECB)
    ref = RefDES.new(key, RefDES.MODE_ECB)

    valid_splits = list(range(8, len(pt), 8))
    splits = sorted(random.sample(valid_splits, min(5, len(valid_splits))))
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


def test_des_ecb_rejects_bad_key_size():
    with pytest.raises(ValueError):
        DES.new(b"", DES.MODE_ECB)
    with pytest.raises(ValueError):
        DES.new(b"\x00" * 7, DES.MODE_ECB)
    with pytest.raises(ValueError):
        DES.new(b"\x00" * 9, DES.MODE_ECB)


def test_des_ecb_rejects_non_block_aligned_data():
    key = randbytes(8)
    my = DES.new(key, DES.MODE_ECB)

    with pytest.raises(ValueError):
        my.encrypt(b"\x00" * 7)

    with pytest.raises(ValueError):
        my.decrypt(b"\x00" * 15)
