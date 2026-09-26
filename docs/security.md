# CodeAtlas — Security

- Keys and tokens only in env vars.
- Safe ZIP extraction (reject ".." and absolute paths).
- Size and file caps enforced.
- CORS allowlist from `ALLOWED_ORIGINS`.
- Sanitize labels (strip quotes, brackets, backticks).
- Mermaid in strict security mode.
- GitHub token: fine-grained, public repositories read-only, 7-day expiry.