# Security Policy

## Security boundary

`flop_identity.py` is intentionally local-only. It has no HTTP client, socket, browser-opening, wallet, transaction, token approval, or claim code.

The only child processes allowed by design are Windows built-ins:

- `whoami` — determine the current Windows principal
- `icacls` — remove inherited ACLs and grant access to that principal and SYSTEM

Commands named `prepare-*` produce data for manual review. They do not submit it.

## Sensitive material

Never publish or attach any of the following:

- a private key, seed, or recovery phrase
- `seed.dpapi`
- a Windows user-profile backup containing the identity store
- an unused `write_url` produced by `prepare-message`

`seed.dpapi` is encrypted, but it is still sensitive. Treat it as a private key backup.

## Reporting a vulnerability

Open a GitHub issue containing only a minimal description and non-secret reproduction steps. Do not include live key material, a private room URL, an unused signed-write URL, wallet information, or personal data.

If secret material was exposed, do not paste it into an issue to prove the exposure. A Technocore `did:key` cannot be centrally revoked; stop using that DID and create a new identity in a separately reviewed store.

## Dependency policy

The direct third-party dependency is `cryptography`; its Windows dependencies `cffi` and `pycparser` are also pinned in `requirements.txt`. Review all three before changing a pin.

