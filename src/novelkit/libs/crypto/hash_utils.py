import hashlib
from pathlib import Path


def hash_file(file_path: Path, chunk_size: int = 8192) -> str:
    """Compute the SHA256 hash of a file.

    Args:
        file_path: The path of the file to hash.
        chunk_size: Size of chunks to read while hashing. Defaults to 8192.

    Returns:
        SHA256 hash of the file content as a lowercase hexadecimal string.
    """
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def hash_bytes(data: bytes) -> str:
    """Compute the SHA256 hash of a bytes object.

    Args:
        data: The bytes to hash.

    Returns:
        SHA256 hash of the data as a lowercase hexadecimal string.
    """
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()
