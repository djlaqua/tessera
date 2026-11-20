# Security Rules

1. Treat all external input as hostile. Validate type, range, length, and encoding at the adapter boundary.
2. Bound everything: message size, queue length, attribute count, string length.
3. XML: parse only with `defusedxml`. Generate with `xml.etree` and escape automatically.
4. No `pickle`, `eval`, `exec`, `yaml.load` (use `safe_load`), or shell with interpolated input.
5. SQL: parameterized queries only.
6. Secrets: environment or secret manager. Never in code, logs, tests, or the repo. Add secret scanning in CI.
7. Network: TLS 1.3, mutual auth for sync, certificate pinning where practical. Bind services to localhost by default.
8. Integrity: sign log segments (Ed25519). Verify before replay or sync ingest.
9. Logging: no raw coordinates of customers or credentials at INFO. Structured logs, redaction helper.
10. Supply chain: pinned versions with hashes, `pip-audit` and SBOM in CI, minimal base image, non-root container.
11. Least privilege: dedicated service user, read-only filesystem where possible.
12. Data handling: customer telemetry is sensitive. Synthetic or consented data only in demos.
13. Export and legal: no sharing of localization code outside the EU until `docs/06` checklist is cleared.
