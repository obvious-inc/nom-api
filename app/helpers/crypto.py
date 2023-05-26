from hashlib import sha3_256
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


async def create_ed25519_keypair() -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


async def sign_keccak_ed25519(data: bytes, private_key: Ed25519PrivateKey) -> bytes:
    hash_val = sha3_256(data).digest()
    signature = private_key.sign(hash_val)
    return signature


async def verify_keccak_ed25519_signature(data: bytes, signature: bytes, signer: bytes):
    hash_val = sha3_256(data).digest()
    public_key = Ed25519PublicKey.from_public_bytes(signer)
    public_key.verify(signature, hash_val)
