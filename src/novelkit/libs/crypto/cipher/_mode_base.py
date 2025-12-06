import abc
from collections.abc import Callable

BlockCipherFunc = Callable[[bytes], bytes]


class BaseMode(abc.ABC):
    """Base class for block-cipher modes of operation.

    A mode instance wraps a *block cipher primitive* that encrypts or decrypts
    a single block, and provides streaming :meth:`encrypt` and :meth:`decrypt`
    operations for arbitrary-length data.
    """

    def __init__(
        self,
        encrypt_block: BlockCipherFunc,
        decrypt_block: BlockCipherFunc,
        block_size: int,
    ) -> None:
        """Initialize a block-cipher mode instance.

        Args:
            encrypt_block: Callable that encrypts a single block of length
                ``block_size``.
            decrypt_block: Callable that decrypts a single block of length
                ``block_size``.
            block_size: Block size in bytes (for example, 16 for AES or
                8 for DES).
        """
        self.encrypt_block = encrypt_block
        self.decrypt_block = decrypt_block
        self.block_size = block_size

    @abc.abstractmethod
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt plaintext.

        Args:
            data: Plaintext bytes. The length must be a multiple of
                ``block_size``. Padding is not applied here.

        Returns:
            Ciphertext bytes of the same length.

        Raises:
            ValueError: If the input length is not a multiple of
                ``block_size``.
        """
        ...

    @abc.abstractmethod
    def decrypt(self, data: bytes) -> bytes:
        """Decrypt ciphertext.

        Args:
            data: Ciphertext bytes. The length must be a multiple of
                ``block_size``. Unpadding is not performed here.

        Returns:
            Plaintext bytes of the same length.

        Raises:
            ValueError: If the input length is not a multiple of
                ``block_size``.
        """
        ...
