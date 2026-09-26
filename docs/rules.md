\# CodeAtlas — Rules



\- Spec before code. Never change the schema without updating schema.md and telling everyone.

\- Typed Python, Pydantic v2, POSIX paths everywhere (Windows dev, Linux server).

\- Never execute repo code. Parse only.

\- Every external call has a timeout and a fallback.

\- No secrets in code. Small commits. Parsers must have tests.

\- API endpoints are plain `def` (blocking work), not `async def`.

