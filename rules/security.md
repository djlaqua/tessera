# Security Rules

1. Treat all external input as hostile. Validate type, range, length, and encoding at the adapter boundary.
2. Bound everything: message size, queue length, attribute count, string length.
3. XML: parse only with `defusedxml`. Generate with `xml.etree` and escape automatically.
4. No `pickle`, `eval`, `exec`, `yaml.load` (use `safe_load`), or shell with interpolated input.
5. SQL: parameterized queries only.
6. Secrets: environment or secret manager. Never in code, logs, tests, or the repo. Add secret scanning in CI.
7. Network: TLS 1.3 for anything off the host. Edges authenticate with Ed25519 batch signatures, the hub with its TLS certificate. Plain HTTP only on loopback or an isolated container network (`--allow-insecure-http`). Bind services to localhost by default.
8. Integrity: every sync batch is signed (Ed25519) and verified before storage. Private keys are mode 0600 and never committed.
9. Logging: no raw coordinates of customers or credentials at INFO. Structured logs, redaction helper.
10. Supply chain: pinned versions with hashes, `pip-audit` and SBOM in CI, minimal base image, non-root container.
11. Least privilege: dedicated service user, read-only filesystem where possible.
12. Data handling: customer telemetry is sensitive. Synthetic or consented data only in demos.
13. Export and legal: no localization code (Phase 2) in the public repository or outside the EU until the `docs/06` checklist and ADR-012 review are cleared.
