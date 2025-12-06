class RC4:
    """Minimal RC4 cipher implementation."""

    def __init__(self, key: bytes) -> None:
        """
        Args:
            key: RC4 key bytes (must not be empty).
        """
        if not key:
            raise ValueError("Key must not be empty")

        self._key = key
        self._S0 = self._rc4_init(key)

    def crypt(self, data: bytes) -> bytes:
        """Encrypts/Decrypts data

        This is the RC4 Pseudo-Random Generation Algorithm (PRGA).

        Args:
            data: Input bytes, either plaintext or ciphertext.

        Returns:
            Output bytes after XOR with the RC4 keystream.
        """
        if not data:
            return b""

        S = self._S0.copy()
        i = 0
        j = 0
        out = bytearray(len(data))
        for idx, ch in enumerate(data):
            i = (i + 1) & 0xFF
            j = (j + S[i]) & 0xFF
            S[i], S[j] = S[j], S[i]
            t = (S[i] + S[j]) & 0xFF
            out[idx] = ch ^ S[t]
        return bytes(out)

    @staticmethod
    def _rc4_init(key: bytes) -> list[int]:
        """Perform the RC4 Key-Scheduling Algorithm (KSA)."""
        S = list(range(256))
        j = 0
        klen = len(key)
        for i in range(256):
            j = (j + S[i] + key[i % klen]) & 0xFF
            S[i], S[j] = S[j], S[i]
        return S
