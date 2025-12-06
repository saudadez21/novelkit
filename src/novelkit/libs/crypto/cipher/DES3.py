from __future__ import annotations

from ._mode_base import BaseMode
from .DES import _DESContext

block_size = 8
key_size = (16, 24)

MODE_ECB = 1  #: Electronic Code Book
MODE_CBC = 2  #: Cipher-Block Chaining


class _DES3Context:
    """Internal Triple-DES (3DES/TDES) primitive using EDE construction.

    This context applies 3DES in the Encrypt-Decrypt-Encrypt sequence. It
    supports both two-key and three-key variants, depending on the key length.
    """

    __slots__ = ("_k1", "_k2", "_k3")

    def __init__(self, key: bytes) -> None:
        """Initialize the 3DES key schedule.

        Args:
            key: Triple-DES key of length 16 bytes (two-key 3DES) or
                24 bytes (three-key 3DES).

        Raises:
            ValueError: If the key length is invalid.
        """
        if len(key) not in key_size:
            raise ValueError("Invalid key size")

        if len(key) == 16:
            k1 = key[:8]
            k2 = key[8:16]
            k3 = k1
        else:  # 24
            k1 = key[:8]
            k2 = key[8:16]
            k3 = key[16:24]

        self._k1 = _DESContext(k1)
        self._k2 = _DESContext(k2)
        self._k3 = _DESContext(k3)

    def encrypt_block(self, plaintext: bytes) -> bytes:
        """Encrypt a single 8-byte block using 3DES (EDE).

        Args:
            plaintext: A plaintext block of length 8 bytes.

        Returns:
            The encrypted block.

        Raises:
            ValueError: If the block size is not 8 bytes.
        """
        if len(plaintext) != 8:
            raise ValueError("Plaintext block must be 8 bytes")

        x = self._k1.encrypt_block(plaintext)
        x = self._k2.decrypt_block(x)
        x = self._k3.encrypt_block(x)
        return x

    def decrypt_block(self, ciphertext: bytes) -> bytes:
        """Decrypt a single 8-byte block using 3DES (DED).

        Args:
            ciphertext: A ciphertext block of length 8 bytes.

        Returns:
            The decrypted block.

        Raises:
            ValueError: If the block size is not 8 bytes.
        """
        if len(ciphertext) != 8:
            raise ValueError("Ciphertext block must be 8 bytes")

        x = self._k3.decrypt_block(ciphertext)
        x = self._k2.encrypt_block(x)
        x = self._k1.decrypt_block(x)
        return x


def new(
    key: bytes | bytearray,
    mode: int,
    iv: bytes | bytearray | None = None,
) -> BaseMode:
    """Create a DES3 cipher object in the requested mode.

    Args:
        key: A 3DES key of length 16 bytes (two-key) or 24 bytes (three-key).
        mode: Either ``MODE_ECB`` or ``MODE_CBC``.
        iv: Initialization vector for CBC mode. Must be 8 bytes. If ``None``,
            a zero IV is used for learning and testing.

    Returns:
        A mode object implementing Triple-DES encryption and decryption.

    Raises:
        ValueError: If the key length, IV length, or mode is invalid.
    """
    ctx = _DES3Context(bytes(key))
    encrypt_block = ctx.encrypt_block
    decrypt_block = ctx.decrypt_block

    if mode == MODE_ECB:
        from ._mode_ecb import ECBMode

        return ECBMode(encrypt_block, decrypt_block, block_size)

    if mode == MODE_CBC:
        from ._mode_cbc import CBCMode

        return CBCMode(
            encrypt_block,
            decrypt_block,
            block_size,
            None if iv is None else bytes(iv),
        )

    raise ValueError("Unknown mode")
