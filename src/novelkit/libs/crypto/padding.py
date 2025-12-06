from __future__ import annotations


def pad(data_to_pad: bytes, block_size: int, style: str = "pkcs7") -> bytes:
    """Apply standard padding to align data to ``block_size``.

    Supported padding styles:

    - ``pkcs7``: PKCS#7 padding, N bytes each equal to N.
    - ``x923``: ANSI X.923 padding, N-1 zero bytes + last byte N.
    - ``iso7816``: ISO/IEC 7816-4 padding, 0x80 followed by zero bytes.

    Args:
        data_to_pad: Raw input bytes.
        block_size: Block size in bytes. Must be in the range [1, 255].
        style: Padding style to use (``pkcs7``, ``x923``, or ``iso7816``).

    Returns:
        Data padded so its length becomes a multiple of ``block_size``.

    Raises:
        ValueError: If ``block_size`` is out of range or the padding style
            is unknown.
    """
    if not (1 <= block_size <= 255):
        raise ValueError("block_size must be between 1 and 255")

    padding_len = block_size - (len(data_to_pad) % block_size)

    if style == "pkcs7":
        padding = bytes([padding_len]) * padding_len

    elif style == "x923":
        padding = b"\x00" * (padding_len - 1) + bytes([padding_len])

    elif style == "iso7816":
        padding = b"\x80" + b"\x00" * (padding_len - 1)

    else:
        raise ValueError("Unknown padding style")

    return data_to_pad + padding


def unpad(padded_data: bytes, block_size: int, style: str = "pkcs7") -> bytes:
    """Remove padding previously applied by :func:`pad`.

    Args:
        padded_data: Input data with padding applied. Length must be a
            multiple of ``block_size``.
        block_size: Block size in bytes. Must be in the range [1, 255].
        style: Padding style used during padding.

    Returns:
        The original unpadded data.

    Raises:
        ValueError: If the input is incorrectly padded or the style
            is unknown.
    """
    if not (1 <= block_size <= 255):
        raise ValueError("block_size must be between 1 and 255")

    pdata_len = len(padded_data)

    if pdata_len == 0:
        raise ValueError("Zero-length input cannot be unpadded")

    if pdata_len % block_size:
        raise ValueError("Input data is not padded")

    if style in ("pkcs7", "x923"):
        padding_len = padded_data[-1]

        if padding_len < 1 or padding_len > block_size:
            raise ValueError("Padding is incorrect")

        padding_block = padded_data[-padding_len:]

        if style == "pkcs7":
            if padding_block != bytes([padding_len]) * padding_len:
                raise ValueError("Padding is incorrect")

        else:  # x923
            if padding_len > 1 and padding_block[:-1] != b"\x00" * (padding_len - 1):
                raise ValueError("Padding is incorrect")

    elif style == "iso7816":
        last_block = padded_data[-block_size:]
        try:
            idx = last_block.rindex(b"\x80")
        except ValueError:
            raise ValueError("Padding is incorrect") from None

        if last_block[idx + 1 :] != b"\x00" * (block_size - idx - 1):
            raise ValueError("Padding is incorrect")

        padding_len = block_size - idx

    else:
        raise ValueError("Unknown padding style")

    return padded_data[:-padding_len]
