"""HTTP layer: routers, endpoint modules and shared request dependencies.

Routers stay thin - they validate input with schemas, delegate to
``app.services`` and serialise the result. No business rules here.
"""
