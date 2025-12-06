from __future__ import annotations

import random

import pytest
from Crypto.Cipher import AES as RefAES

from novelkit.libs.crypto.cipher import AES

_rng = random.Random(20251123)


def randbytes(n: int) -> bytes:
    return bytes(_rng.randrange(0, 256) for _ in range(n))


# ===========================================================
# Encrypt correctness
# ===========================================================


@pytest.mark.parametrize("key_len", [16, 24, 32])
@pytest.mark.parametrize("nblocks", [0, 1, 2, 4, 8])
def test_aes_ecb_encrypt_matches_pycryptodome(key_len, nblocks):
    key = randbytes(key_len)
    pt = randbytes(16 * nblocks)

    my = AES.new(key, AES.MODE_ECB)
    ref = RefAES.new(key, RefAES.MODE_ECB)

    assert my.encrypt(pt) == ref.encrypt(pt)


# ===========================================================
# Decrypt correctness
# ===========================================================


@pytest.mark.parametrize("key_len", [16, 24, 32])
@pytest.mark.parametrize("nblocks", [0, 1, 3, 5, 10])
def test_aes_ecb_decrypt_matches_pycryptodome(key_len, nblocks):
    key = randbytes(key_len)
    pt = randbytes(16 * nblocks)

    ref_enc = RefAES.new(key, RefAES.MODE_ECB)
    ct = ref_enc.encrypt(pt)

    my_dec = AES.new(key, AES.MODE_ECB)
    assert my_dec.decrypt(ct) == pt


# ===========================================================
# Streaming vs one-shot
# ===========================================================


def test_aes_ecb_streaming_equals_one_shot_and_matches_ref():
    key = randbytes(32)
    pt = randbytes(16 * 6)

    my1 = AES.new(key, AES.MODE_ECB)
    ct_one = my1.encrypt(pt)

    my2 = AES.new(key, AES.MODE_ECB)
    ct_stream = my2.encrypt(pt[:32]) + my2.encrypt(pt[32:])

    assert ct_stream == ct_one

    ref = RefAES.new(key, RefAES.MODE_ECB)
    ct_ref = ref.encrypt(pt[:32]) + ref.encrypt(pt[32:])
    assert ct_stream == ct_ref


# ===========================================================
# Multi-call correctness
# ===========================================================


def test_aes_ecb_multiple_calls_independent():
    key = randbytes(16)
    pt1 = randbytes(16 * 2)
    pt2 = randbytes(16 * 3)

    my = AES.new(key, AES.MODE_ECB)
    ref = RefAES.new(key, RefAES.MODE_ECB)

    assert my.encrypt(pt1) == ref.encrypt(pt1)
    assert my.encrypt(pt2) == ref.encrypt(pt2)


def test_aes_ecb_multiple_encrypt_calls_match_reference():
    key = randbytes(16)
    my = AES.new(key, AES.MODE_ECB)
    ref = RefAES.new(key, RefAES.MODE_ECB)

    for _ in range(10):
        pt = randbytes(16 * _rng.randrange(1, 6))
        assert my.encrypt(pt) == ref.encrypt(pt)


def test_aes_ecb_stateless_object_independence():
    key = randbytes(16)
    pt = randbytes(16 * 4)

    my1 = AES.new(key, AES.MODE_ECB)
    my2 = AES.new(key, AES.MODE_ECB)

    assert my1.encrypt(pt) == my2.encrypt(pt)


def test_aes_ecb_random_chunk_streaming_matches_reference():
    key = randbytes(32)
    pt = randbytes(16 * 8)

    valid_splits = list(range(16, len(pt), 16))
    splits = sorted(random.sample(valid_splits, 5))
    splits.append(len(pt))

    my = AES.new(key, AES.MODE_ECB)
    ref = RefAES.new(key, RefAES.MODE_ECB)

    start = 0
    ct_my = b""
    ct_ref = b""
    for s in splits:
        ct_my += my.encrypt(pt[start:s])
        ct_ref += ref.encrypt(pt[start:s])
        start = s

    assert ct_my == ct_ref


# ===========================================================
# Validation
# ===========================================================


def test_aes_ecb_rejects_bad_key_size():
    with pytest.raises(ValueError):
        AES.new(b"", AES.MODE_ECB)
    with pytest.raises(ValueError):
        AES.new(b"\x00" * 15, AES.MODE_ECB)
    with pytest.raises(ValueError):
        AES.new(b"\x00" * 17, AES.MODE_ECB)


def test_aes_ecb_rejects_non_block_aligned_data():
    key = randbytes(16)
    my = AES.new(key, AES.MODE_ECB)

    with pytest.raises(ValueError):
        my.encrypt(b"\x00" * 15)

    with pytest.raises(ValueError):
        my.decrypt(b"\x00" * 31)
