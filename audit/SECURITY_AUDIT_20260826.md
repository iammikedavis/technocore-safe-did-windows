# Security Audit — 2026-08-26

Scope: the public contents of this repository only. No personal DID store, encrypted seed, wallet, browser profile, or local receipt is included.

## Design review

- Key generation uses `secrets.token_bytes(32)` and Ed25519 from `cryptography`.
- The seed is protected with Windows DPAPI CurrentUser before disk storage.
- Directory ACL inheritance is removed; access is granted to the current Windows principal and SYSTEM.
- Initialization fails if either identity file already exists.
- An exclusive `init.lock` prevents concurrent initialization from silently rotating the DID.
- The protected seed is never printed or exported.
- `prepare-message` signs locally and reports `sent: no`.
- `prepare-did-note` reads only the public identity file and does not decrypt the seed.
- No network-capable Python module is imported.
- No browser is opened and no HTTP request is made by the helper.
- The only subprocess commands are literal argument arrays for `whoami` and `icacls`; user input is not used as a command.
- Room names and nonce formats are allowlisted. Message text is passed through the Technocore single-line sweep and length check.

## Fail-closed behavior

- Non-Windows systems stop before key creation because DPAPI is unavailable.
- ACL restriction failure stops key creation.
- Existing or incomplete identity files are not overwritten.
- DID schema, DID format, fingerprint, decrypted seed, and public identity must agree before signing.
- Invalid room names, nonces, empty messages, and oversized messages are rejected.

## Tests run before publication

Environment:

- Windows
- CPython 3.12.13 (isolated test virtual environment)
- `cryptography==50.0.1`
- `cffi==2.1.1`
- `pycparser==3.0`

Results:

- `python -m unittest discover -s tests -v`: 6 tests passed
- CLI `selftest`: `status=ok`, `dpapi_roundtrip=ok`, `network_requests=0`
- `python -m pip check`: no broken requirements
- `python -m compileall`: passed
- Static import test: no `socket`, `http`, `httpx`, `requests`, `urllib3`, or `webbrowser` import
- Publication-tree scan: no personal DID, personal fingerprint, X handle, GitHub token pattern, or private-key block found
- Avast `ashQuick.exe` targeted scan: all 10 publication files scanned individually; each returned exit code 0 with no detection output

Publication hashes:

- `flop_identity.py`: `9CDD6D1608DB3755FB249088F098B3A7916974470C6D4A107A14F521BAF03D06`
- `requirements.txt`: `8E5E096382A35D55EA1105F989EAC41E42C237DB1E9324B3A065267246A816C0`

## Residual risks

- DPAPI CurrentUser protects against copying the file to another account, but malware already running as the same Windows user may be able to request decryption.
- An administrator or compromised Windows session may bypass local protections.
- `seed.dpapi` is not a portable backup. Loss of the Windows profile may make the DID unrecoverable.
- A prepared signed-write URL is a bearer-like capability until it is used; anyone who sees it may submit the public message.
- Technocore is public, unauthenticated for ordinary posts, world-writable for ordinary notes, and ephemeral.
- A SHA-256 file detects version mismatch; it does not protect against compromise of the repository account and all published hashes together.
- This tool proves control of a DID key only. It does not prove a legal identity, wallet ownership, or airdrop eligibility.
