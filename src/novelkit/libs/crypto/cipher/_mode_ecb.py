from __future__ import annotations

from ._mode_base import BaseMode, BlockCipherFunc


class ECBMode(BaseMode):
    """Electronic Code Book (ECB) mode.

    ECB is stateless: each block is processed independently without an IV or
    chaining. This mode provides no semantic security and is included mainly
    for completeness or educational purposes.
    """

    def __init__(
        self,
        encrypt_block: BlockCipherFunc,
        decrypt_block: BlockCipherFunc,
        block_size: int,
    ) -> None:
        """Initialize an ECB mode instance.

        Args:
            encrypt_block: Block encryption function. See :class:`BaseMode`.
            decrypt_block: Block decryption function. See :class:`BaseMode`.
            block_size: Block size in bytes. See :class:`BaseMode`.
        """
        super().__init__(encrypt_block, decrypt_block, block_size)

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data in ECB mode.

        The input must be block-aligned; padding is not applied automatically.

        Args:
            data: Plaintext bytes. Length must be a multiple of ``block_size``.

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
        for i in range(0, len(data), bs):
            out += self.encrypt_block(data[i : i + bs])
        return bytes(out)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data in ECB mode.

        The input must be block-aligned; unpadding is not performed
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
        for i in range(0, len(data), bs):
            out += self.decrypt_block(data[i : i + bs])
        return bytes(out)
