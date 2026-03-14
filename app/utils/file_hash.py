import hashlib


def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
