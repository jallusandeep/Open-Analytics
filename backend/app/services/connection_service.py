"""Compatibility wrapper for connection services.

Existing imports should continue to use:
    from app.services.connection_service import ...
"""

from app.services.connections import *  # noqa: F401,F403
