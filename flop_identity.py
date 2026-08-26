#!/usr/bin/env python3
"""Local-only Ed25519 DID helper for technocore.chat on Windows.

The private 32-byte seed is encrypted with Windows DPAPI for the current user.
This tool never prints the seed, exports it, opens a browser, or sends a network
request. Commands that can write to Technocore only PREPARE a URL for manual
review; they never open or submit that URL.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import getpass
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
import unicodedata
from contextlib import contextmanager
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


VERSION = "1.0.0"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
MULTICODEC_ED25519 = b"\xed\x01"
INVISIBLE_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Zl", "Zp"}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
NONCE_RE = re.compile(r"^[0-9]{1,19}$")
DEFAULT_STORE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "FlopAgent" / "Identity"
SECRET_FILE = "seed.dpapi"
PUBLIC_FILE = "identity.json"
LOCK_FILE = "init.lock"
TECHNOCORE_ORIGIN = "https://technocore.chat"


class DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes) -> tuple[DataBlob, object]:
    buffer = ctypes.create_string_buffer(data, len(data))
    value = DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    return value, buffer


def _crypt32() -> ctypes.WinDLL:
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is required; this helper intentionally fails closed elsewhere")
    library = ctypes.WinDLL("crypt32", use_last_error=True)
    library.CryptProtectData.argtypes = [
        ctypes.POINTER(DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DataBlob),
    ]
    library.CryptProtectData.restype = wintypes.BOOL
    library.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DataBlob),
    ]
    library.CryptUnprotectData.restype = wintypes.BOOL
    return library


def _local_free(pointer: object) -> None:
    if pointer:
        ctypes.windll.kernel32.LocalFree(pointer)


def dpapi_protect(data: bytes) -> bytes:
    source, source_buffer = _blob(data)
    _ = source_buffer
    output = DataBlob()
    if not _crypt32().CryptProtectData(
        ctypes.byref(source), "Technocore agent Ed25519 seed", None, None, None, 0, ctypes.byref(output)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        _local_free(output.pbData)


def dpapi_unprotect(data: bytes) -> bytes:
    source, source_buffer = _blob(data)
    _ = source_buffer
    output = DataBlob()
    description = wintypes.LPWSTR()
    if not _crypt32().CryptUnprotectData(
        ctypes.byref(source), ctypes.byref(description), None, None, None, 0, ctypes.byref(output)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        _local_free(output.pbData)
        _local_free(description)


def base58btc(data: bytes) -> str:
    leading_zeroes = len(data) - len(data.lstrip(b"\x00"))
    number = int.from_bytes(data, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58[remainder] + encoded
    return "1" * leading_zeroes + (encoded or "1")


def did_from_seed(seed: bytes) -> str:
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be exactly 32 bytes")
    key = Ed25519PrivateKey.from_private_bytes(seed)
    public = key.public_key().public_bytes_raw()
    did = "did:key:z" + base58btc(MULTICODEC_ED25519 + public)
    if not did.startswith("did:key:z6Mk") or len(did) != 56:
        raise RuntimeError("derived DID failed the did:key invariant")
    return did


def fingerprint(did: str) -> str:
    return hashlib.sha256(did.encode("utf-8")).hexdigest()[:16]


def sweep(text: str, limit: int) -> str:
    cleaned = "".join(
        " " if unicodedata.category(char) in INVISIBLE_CATEGORIES else char for char in text
    ).strip()
    if not cleaned:
        raise ValueError("text is empty after the Technocore single-line sweep")
    if len(cleaned) > limit:
        raise ValueError(f"text has {len(cleaned)} characters after sweep; limit is {limit}")
    return cleaned


def validate_name(value: str, label: str) -> str:
    if not NAME_RE.fullmatch(value):
        raise ValueError(f"{label} must match {NAME_RE.pattern}")
    return value


def validate_nonce(value: str) -> str:
    if not NONCE_RE.fullmatch(value):
        raise ValueError("nonce must be 1-19 ASCII digits")
    return value


def sign(seed: bytes, canonical: str) -> str:
    raw = Ed25519PrivateKey.from_private_bytes(seed).sign(canonical.encode("utf-8"))
    signature = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    if len(signature) != 86:
        raise RuntimeError("signature length invariant failed")
    return signature


def _exclusive_write(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


@contextmanager
def _init_lock(store: Path) -> Iterator[None]:
    lock_path = store / LOCK_FILE
    try:
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(
            f"{LOCK_FILE} already exists; another init may be running. Refusing to create or rotate a key"
        ) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            handle.write(str(os.getpid()))
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _restrict_acl(store: Path) -> str:
    principal = subprocess.run(
        ["whoami"], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout.strip()
    if not principal:
        principal = getpass.getuser()
    result = subprocess.run(
        [
            "icacls",
            str(store),
            "/inheritance:r",
            "/grant:r",
            f"{principal}:(OI)(CI)F",
            "*S-1-5-18:(OI)(CI)F",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError("could not restrict the identity directory ACL; refusing to create a key")
    return principal


def _read_public_identity(store: Path) -> dict[str, str]:
    public_path = store / PUBLIC_FILE
    if not public_path.is_file():
        raise FileNotFoundError("public identity is missing; run init once")
    public = json.loads(public_path.read_text(encoding="utf-8"))
    did = public.get("did", "")
    if public.get("schema") != "technocore-safe-did-public-v1":
        raise RuntimeError("unrecognized public identity schema")
    if not isinstance(did, str) or not did.startswith("did:key:z6Mk") or len(did) != 56:
        raise RuntimeError("public identity contains an invalid did:key")
    if public.get("fingerprint_sha256_16") != fingerprint(did):
        raise RuntimeError("public identity fingerprint mismatch")
    return public


def create_identity(store: Path) -> dict[str, str]:
    if store.exists() and store.is_symlink():
        raise RuntimeError("identity store must not be a symbolic link")
    store.mkdir(parents=True, exist_ok=True)
    principal = _restrict_acl(store)
    with _init_lock(store):
        secret_path = store / SECRET_FILE
        public_path = store / PUBLIC_FILE
        if secret_path.exists() or public_path.exists():
            raise FileExistsError("identity already exists; refusing to overwrite or rotate it")
        seed = secrets.token_bytes(32)
        did = did_from_seed(seed)
        protected = dpapi_protect(seed)
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        public = {
            "schema": "technocore-safe-did-public-v1",
            "did": did,
            "fingerprint_sha256_16": fingerprint(did),
            "created_at_utc": created_at,
            "private_seed_storage": "Windows DPAPI CurrentUser; not portable",
            "technocore_protocol": "Ed25519 did:key",
        }
        _exclusive_write(secret_path, protected)
        _exclusive_write(public_path, (json.dumps(public, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return {
        "status": "created",
        "did": did,
        "fingerprint": fingerprint(did),
        "store": str(store),
        "acl_principal": principal,
        "secret_exposed": "no",
        "network_requests": "0",
    }


def load_identity(store: Path) -> tuple[bytes, dict[str, str]]:
    secret_path = store / SECRET_FILE
    if not secret_path.is_file():
        raise FileNotFoundError("protected seed is missing; run init once")
    public = _read_public_identity(store)
    seed = dpapi_unprotect(secret_path.read_bytes())
    if len(seed) != 32 or did_from_seed(seed) != public.get("did"):
        raise RuntimeError("decrypted seed does not match the public identity; refusing to sign")
    return seed, public


def prepare_message(store: Path, room: str, nonce: str, text: str) -> dict[str, str]:
    room = validate_name(room, "room")
    nonce = validate_nonce(nonce)
    cleaned = sweep(text, 4096)
    seed, public = load_identity(store)
    did = public["did"]
    signature = sign(seed, f"{room}|{nonce}|{cleaned}")
    path = f"/r/{room}/say-signed/{quote(did, safe='')}/{signature}/{nonce}/{quote(cleaned, safe='')}"
    return {
        "action": "prepare_signed_room_message",
        "sent": "no",
        "did": did,
        "room": room,
        "nonce": nonce,
        "text": cleaned,
        "signature": signature,
        "write_url": TECHNOCORE_ORIGIN + path,
        "warning": "Review first. Opening write_url publishes this message. The tool never opens it.",
    }


def prepare_did_note(store: Path) -> dict[str, str]:
    public = _read_public_identity(store)
    did = public["did"]
    fp = fingerprint(did)
    namespace = f"did-{fp[:2]}"
    key = fp[2:]
    path = f"/kv/{namespace}/{key}/set/{quote(did, safe='')}"
    return {
        "action": "prepare_public_did_note",
        "sent": "no",
        "did": did,
        "fingerprint": fp,
        "namespace": namespace,
        "key": key,
        "write_url": TECHNOCORE_ORIGIN + path,
        "read_url": f"{TECHNOCORE_ORIGIN}/kv/{namespace}/{key}",
        "warning": "Review first. DID notes are public and world-writable; signed messages prove key control.",
    }


def selftest() -> dict[str, str]:
    seed = secrets.token_bytes(32)
    did = did_from_seed(seed)
    canonical = "lobby|1|local self-test"
    signature = sign(seed, canonical)
    padded = signature + "=" * (-len(signature) % 4)
    Ed25519PrivateKey.from_private_bytes(seed).public_key().verify(
        base64.urlsafe_b64decode(padded), canonical.encode("utf-8")
    )
    protected = dpapi_protect(seed)
    if dpapi_unprotect(protected) != seed:
        raise RuntimeError("DPAPI round-trip failed")
    return {
        "status": "ok",
        "version": VERSION,
        "did_prefix": did[:12],
        "signature_length": str(len(signature)),
        "dpapi_roundtrip": "ok",
        "network_requests": "0",
    }


def emit(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest", help="verify local DID, signature, and DPAPI primitives")
    sub.add_parser("init", help="create one non-overwriting DPAPI-protected identity")
    sub.add_parser("inspect", help="show public identity and validate its protected seed")
    sub.add_parser("prepare-did-note", help="prepare, but do not send, a public DID-note write")
    message = sub.add_parser("prepare-message", help="prepare, but do not send, a signed room message")
    message.add_argument("--room", default="lobby")
    message.add_argument("--nonce", default=None)
    message.add_argument("--text", required=True)
    args = parser.parse_args()
    store = args.store.expanduser().resolve()

    try:
        if args.command == "selftest":
            emit(selftest())
        elif args.command == "init":
            emit(create_identity(store))
        elif args.command == "inspect":
            _, public = load_identity(store)
            emit({"status": "valid", "store": str(store), **public, "secret_exposed": "no"})
        elif args.command == "prepare-did-note":
            emit(prepare_did_note(store))
        else:
            nonce = args.nonce or str(int(time.time_ns() // 1_000_000))
            emit(prepare_message(store, args.room, nonce, args.text))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
