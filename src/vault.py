#!/usr/bin/env python3
"""
LEON Secrets Vault — Encrypted .env storage using Fernet (AES-128).

Usage:
    from vault import load_env, encrypt_env, decrypt_env

Master key location: /opt/leon/.master_key (permissions 0400)
Encrypted vault:    /opt/leon/app/.env.encrypted
"""

import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MASTER_KEY_PATH = Path("/opt/leon/.master_key")
ENCRYPTED_ENV_PATH = PROJECT_ROOT / ".env.encrypted"
ENV_PATH = PROJECT_ROOT / ".env"


# ── Key Management ─────────────────────────────────────────────


def generate_key() -> bytes:
    """Generate a new Fernet key."""
    return Fernet.generate_key()


def save_key(key: bytes, path: Path = DEFAULT_MASTER_KEY_PATH) -> None:
    """Save master key to a file with restricted permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    path.chmod(0o400)  # owner read-only
    print(f"[VAULT] Master key saved to {path} (permissions: 0400)")


def load_key(path: Path = DEFAULT_MASTER_KEY_PATH) -> bytes:
    """Load master key from file."""
    if not path.exists():
        raise FileNotFoundError(
            f"Master key not found at {path}. "
            f"Run 'python3 -m src.vault init' to create one."
        )
    return path.read_bytes()


# ── Encrypt / Decrypt ──────────────────────────────────────────


def encrypt_file(
    source: Path = ENV_PATH,
    dest: Path = ENCRYPTED_ENV_PATH,
    key: bytes | None = None,
) -> None:
    """Encrypt the .env file into .env.encrypted."""
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    if key is None:
        key = load_key()

    fernet = Fernet(key)
    data = source.read_bytes()
    encrypted = fernet.encrypt(data)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(encrypted)
    dest.chmod(0o600)  # owner read-write only

    print(f"[VAULT] Encrypted: {source} → {dest} ({len(encrypted)} bytes)")


def decrypt_file(
    source: Path = ENCRYPTED_ENV_PATH,
    dest: Path = ENV_PATH,
    key: bytes | None = None,
) -> None:
    """Decrypt .env.encrypted into .env."""
    if not source.exists():
        raise FileNotFoundError(
            f"Encrypted vault not found at {source}. "
            f"Run 'python3 -m src.vault encrypt' first."
        )

    if key is None:
        key = load_key()

    fernet = Fernet(key)
    data = source.read_bytes()

    try:
        decrypted = fernet.decrypt(data)
    except InvalidToken:
        raise ValueError(
            "Invalid master key or corrupted vault file."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(decrypted)
    dest.chmod(0o600)

    print(f"[VAULT] Decrypted: {source} → {dest} ({len(decrypted)} bytes)")


def load_env(key: bytes | None = None) -> dict[str, str]:
    """Load environment variables from the encrypted vault.

    Tries .env first, then falls back to .env.encrypted.
    Useful for production startup when .env has been cleaned.
    """
    if ENV_PATH.exists() and ENV_PATH.stat().st_size > 0:
        # .env exists and is non-empty, use it directly
        return _parse_env_file(ENV_PATH)

    if ENCRYPTED_ENV_PATH.exists():
        # Decrypt the vault into memory
        if key is None:
            key = load_key()
        decrypt_file(source=ENCRYPTED_ENV_PATH, dest=ENV_PATH, key=key)
        return _parse_env_file(ENV_PATH)

    return {}


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict."""
    result = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


# ── CLI ────────────────────────────────────────────────────────


def cmd_init():
    """Initialize vault: generate master key + encrypt .env."""
    if DEFAULT_MASTER_KEY_PATH.exists():
        overwrite = input(
            f"Master key already exists at {DEFAULT_MASTER_KEY_PATH}. "
            f"Overwrite? (y/N): "
        )
        if overwrite.lower() != "y":
            print("[VAULT] Aborted.")
            return

    key = generate_key()
    save_key(key)
    print(f"[VAULT] Master key generated: {key.decode()[:20]}...")

    if ENV_PATH.exists():
        encrypt_file(key=key)
        print(f"[VAULT] .env encrypted to {ENCRYPTED_ENV_PATH}")

    # Optionally clear the plaintext .env
    clear = input(
        "Remove plaintext .env file? "
        "It is recommended for production. (y/N): "
    )
    if clear.lower() == "y":
        if ENV_PATH.exists():
            ENV_PATH.unlink()
            print(f"[VAULT] Removed {ENV_PATH}")
        print(
            "[VAULT] In production, the systemd unit will decrypt "
            "the vault on startup."
        )
    else:
        print(
            "[VAULT] Keeping .env. The vault serves as backup. "
            "In production, remove .env and use .env.encrypted only."
        )

    print("[VAULT] Initialization complete.")


def cmd_encrypt():
    """Encrypt .env into .env.encrypted."""
    if not DEFAULT_MASTER_KEY_PATH.exists():
        print(
            f"[VAULT] Master key not found. Run 'python3 -m src.vault init' first."
        )
        return
    key = load_key()
    encrypt_file(key=key)


def cmd_decrypt():
    """Decrypt .env.encrypted into .env."""
    if not DEFAULT_MASTER_KEY_PATH.exists():
        print(
            f"[VAULT] Master key not found. Run 'python3 -m src.vault init' first."
        )
        return
    key = load_key()
    decrypt_file(key=key)


def cmd_status():
    """Show vault status."""
    key_exists = DEFAULT_MASTER_KEY_PATH.exists()
    vault_exists = ENCRYPTED_ENV_PATH.exists()
    env_exists = ENV_PATH.exists()

    print("[VAULT] Status:")
    print(f"  Master key ({DEFAULT_MASTER_KEY_PATH}):      "
          f"{'✅ EXISTS' if key_exists else '❌ NOT FOUND'}")
    print(f"  Encrypted vault ({ENCRYPTED_ENV_PATH}): "
          f"{'✅ EXISTS' if vault_exists else '❌ NOT FOUND'}")
    print(f"  Plaintext .env ({ENV_PATH}):        "
          f"{'⚠️  EXISTS' if env_exists else '✅ REMOVED (secure)'}")

    if key_exists:
        key = load_key()
        print(f"  Key fingerprint: {key.decode()[:16]}...")

    if vault_exists:
        size = ENCRYPTED_ENV_PATH.stat().st_size
        print(f"  Vault size: {size} bytes")


if __name__ == "__main__":
    commands = {
        "init": cmd_init,
        "encrypt": cmd_encrypt,
        "decrypt": cmd_decrypt,
        "status": cmd_status,
    }

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Usage: python3 -m src.vault [{'|'.join(commands)}]")
        sys.exit(1)
