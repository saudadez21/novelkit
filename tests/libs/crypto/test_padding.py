from __future__ import annotations

import random

import pytest
from Crypto.Util.Padding import pad as ref_pad
from Crypto.Util.Padding import unpad as ref_unpad

from novelkit.libs.crypto.padding import pad as my_pad
from novelkit.libs.crypto.padding import unpad as my_unpad

# ===========================================================
# FIXED PARAMETERS
# ===========================================================

STYLES = ["pkcs7", "x923", "iso7816"]

BLOCK_SIZES_MAIN = [8, 16, 32]
BLOCK_SIZES_EDGE = [1, 2, 3]

DATA_KNOWN = [
    b"",
    b"\x00",
    b"\x01\x02\x03",
    b"hello",
    b"\xff" * 7,
    b"\x10" * 16,
    b"The quick brown fox jumps over the lazy dog",
]

DATA_RANDOM_LENGTHS = [0, 1, 2, 7, 8, 15, 16, 17, 31, 32, 33, 63, 64, 65]

_rng = random.Random(20251123)


def randbytes(n: int) -> bytes:
    """Reproducible random bytes using Python's random.Random."""
    return bytes(_rng.randrange(0, 256) for _ in range(n))


# ===========================================================
# PAD TESTS
# ===========================================================


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("block_size", BLOCK_SIZES_MAIN + BLOCK_SIZES_EDGE)
@pytest.mark.parametrize("data", DATA_KNOWN)
def test_pad_matches_pycryptodome_known(style, block_size, data):
    assert my_pad(data, block_size, style=style) == ref_pad(
        data, block_size, style=style
    )


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("block_size", BLOCK_SIZES_MAIN)
@pytest.mark.parametrize("n", DATA_RANDOM_LENGTHS)
def test_pad_matches_pycryptodome_random(style, block_size, n):
    data = randbytes(n)
    assert my_pad(data, block_size, style=style) == ref_pad(
        data, block_size, style=style
    )


# ===========================================================
# UNPAD TESTS
# ===========================================================


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("block_size", BLOCK_SIZES_MAIN + BLOCK_SIZES_EDGE)
@pytest.mark.parametrize("n", DATA_RANDOM_LENGTHS)
def test_unpad_roundtrip_and_match(style, block_size, n):
    data = randbytes(n)

    padded_my = my_pad(data, block_size, style=style)
    padded_ref = ref_pad(data, block_size, style=style)
    assert padded_my == padded_ref

    assert my_unpad(padded_my, block_size, style=style) == data
    assert ref_unpad(padded_ref, block_size, style=style) == data


# ===========================================================
# ERROR CASES
# ===========================================================


def test_pad_invalid_block_size():
    with pytest.raises(ValueError):
        my_pad(b"abc", 0, style="pkcs7")
    with pytest.raises(ValueError):
        my_pad(b"abc", 256, style="pkcs7")


def test_unpad_invalid_block_size():
    with pytest.raises(ValueError):
        my_unpad(b"abcd", 0, style="pkcs7")
    with pytest.raises(ValueError):
        my_unpad(b"abcd", 256, style="pkcs7")


def test_pad_unknown_style():
    with pytest.raises(ValueError):
        my_pad(b"abc", 16, style="nope")


def test_unpad_unknown_style():
    with pytest.raises(ValueError):
        my_unpad(b"abc" * 16, 16, style="nope")


@pytest.mark.parametrize("style", STYLES)
def test_unpad_rejects_non_multiple(style):
    with pytest.raises(ValueError):
        my_unpad(b"\x00" * 15, 16, style=style)


# ===========================================================
# ADDITIONAL REQUIRED ERROR TESTS
# ===========================================================


def test_unpad_rejects_empty_input():
    """Covers: pdata_len == 0"""
    with pytest.raises(ValueError):
        my_unpad(b"", 16, style="pkcs7")


@pytest.mark.parametrize("style", ["pkcs7", "x923"])
def test_unpad_rejects_bad_padding_length(style):
    block_size = 16
    bad_block = b"A" * 15 + bytes([block_size + 1])
    with pytest.raises(ValueError):
        my_unpad(bad_block, block_size, style=style)


def test_unpad_iso7816_wrong_zero_fill():
    block_size = 16
    bad_block = b"\x80" + b"\x01" + b"\x00" * (block_size - 2)

    with pytest.raises(ValueError):
        my_unpad(bad_block, block_size, style="iso7816")


# ===========================================================
# TAMPER TESTS
# ===========================================================


@pytest.mark.parametrize("block_size", BLOCK_SIZES_MAIN)
def test_unpad_pkcs7_tamper(block_size):
    data = b"attack at dawn"
    padded = my_pad(data, block_size, style="pkcs7")

    bad = padded[:-1] + bytes([padded[-1] ^ 1])
    with pytest.raises(ValueError):
        my_unpad(bad, block_size, style="pkcs7")
    with pytest.raises(ValueError):
        ref_unpad(bad, block_size, style="pkcs7")


@pytest.mark.parametrize("block_size", BLOCK_SIZES_MAIN)
def test_unpad_x923_tamper(block_size):
    data = b"attack at dusk"
    padded = my_pad(data, block_size, style="x923")
    pad_len = padded[-1]

    if pad_len > 1:
        idx = len(padded) - pad_len
        bad = bytearray(padded)
        bad[idx] ^= 0xFF
        bad = bytes(bad)
    else:
        bad = padded[:-1] + bytes([padded[-1] ^ 1])

    with pytest.raises(ValueError):
        my_unpad(bad, block_size, style="x923")
    with pytest.raises(ValueError):
        ref_unpad(bad, block_size, style="x923")


@pytest.mark.parametrize("block_size", BLOCK_SIZES_MAIN)
def test_unpad_iso7816_tamper(block_size):
    data = b"hello world"
    padded = my_pad(data, block_size, style="iso7816")

    bad = bytearray(padded)
    start = len(bad) - block_size
    for i in range(block_size):
        if bad[start + i] == 0x80:
            bad[start + i] = 0x81
            break
    bad = bytes(bad)

    with pytest.raises(ValueError):
        my_unpad(bad, block_size, style="iso7816")
    with pytest.raises(ValueError):
        ref_unpad(bad, block_size, style="iso7816")
