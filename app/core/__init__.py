"""Cross-cutting concerns: configuration, logging, middleware, error types.

Phase 2 adds ``security.py`` here (password hashing with Argon2, JWT creation
and decoding). Nothing in this package may import from ``app.api`` or
``app.services``, which keeps the dependency direction one-way.
"""
