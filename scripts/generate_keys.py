#!/usr/bin/env python3
"""Generate cryptographic keys for Atalaya configuration."""
import secrets
import base64


def generate_secret_key(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def generate_jwt_secret() -> str:
    return base64.b64encode(secrets.token_bytes(64)).decode()


if __name__ == "__main__":
    print("Atalaya Key Generator")
    print("─" * 40)
    print(f"\nSECRET_KEY={generate_secret_key()}")
    print(f"\n# Alternative (base64-encoded 512-bit key):")
    print(f"SECRET_KEY={generate_jwt_secret()}")
    print("\nAdd the SECRET_KEY value to your .env file.")
