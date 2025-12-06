from __future__ import annotations

from ._mode_base import BaseMode, BlockCipherFunc


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    """XOR two byte sequences of equal length.

    Args:
        a: First byte sequence.
        b: Second byte sequence.

    Returns:
        The XOR result as a new byte sequence.
    """
    return bytes(x ^ y for x, y in zip(a, b, strict=False))


class CBCMode(BaseMode):
    """Cipher Block Chaining (CBC) mode.

    CBC is a stateful block-cipher mode: each encrypted block depends on the
    previous ciphertext block. The internal chaining value (IV) is updated after
    each encryption or decryption call.
    """

    def __init__(
        self,
        encrypt_block: BlockCipherFunc,
        decrypt_block: BlockCipherFunc,
        block_size: int,
        iv: bytes | None,
    ) -> None:
        """Initialize a CBC mode instance.

        Args:
            encrypt_block: Block encryption function. See :class:`BaseMode`.
            decrypt_block: Block decryption function. See :class:`BaseMode`.
            block_size: Block size in bytes. See :class:`BaseMode`.
            iv: Initialization vector. Must be exactly ``block_size`` bytes.
                If ``None``, a zero IV is used (suitable for tests or learning,
                but not recommended for real cryptographic use).

        Raises:
            ValueError: If ``iv`` does not match ``block_size``.
        """
        super().__init__(encrypt_block, decrypt_block, block_size)
        if iv is None:
            iv = bytes(block_size)
        if len(iv) != block_size:
            raise ValueError("Invalid IV size")
        self.iv = bytes(iv)

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data in CBC mode.

        The chaining value (IV) is updated to the last ciphertext block after
        encryption. Padding is not applied automatically, so the input must
        already be block-aligned.

        Args:
            data: Plaintext bytes. Length must be a multiple of
                ``block_size``.

        Returns:
            Ciphertext bytes.

        Raises:
            ValueError: If the input length is not a multiple of
                ``block_size``.
        """
        bs = self.block_size
        if len(data) % bs != 0:
            raise ValueError("Data length not a multiple of block size")

        out = bytearray()
        prev = self.iv

        for i in range(0, len(data), bs):
            block = data[i : i + bs]
            xored = _xor_bytes(block, prev)
            ct = self.encrypt_block(xored)
            out += ct
            prev = ct

        self.iv = prev
        return bytes(out)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data in CBC mode.

        The chaining value (IV) is updated to the last ciphertext block after
        decryption. Input must be block-aligned; unpadding is not performed
        automatically.

        Args:
            data: Ciphertext bytes. Length must be a multiple of
                ``block_size``.

        Returns:
            Plaintext bytes.

        Raises:
            ValueError: If the input length is not a multiple of
                ``block_size``.
        """
        bs = self.block_size
        if len(data) % bs != 0:
            raise ValueError("Data length not a multiple of block size")

        out = bytearray()
        prev = self.iv

        for i in range(0, len(data), bs):
            block = data[i : i + bs]
            dec = self.decrypt_block(block)
            pt = _xor_bytes(dec, prev)
            out += pt
            prev = block

        self.iv = prev
        return bytes(out)
