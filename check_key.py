import base64
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives import serialization

key_path = Path("keys/rsa_key.p8")

private_key = serialization.load_pem_private_key(
    key_path.read_bytes(),
    password=None,
)

public_key_der = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

digest = hashlib.sha256(public_key_der).digest()
fingerprint = "SHA256:" + base64.b64encode(digest).decode().rstrip("=")

print("Local public key fingerprint:")
print(fingerprint)