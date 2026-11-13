import os

# app.core.db creates its engine at import time from settings.database_url.
# Tests never use that real engine (each test module builds its own
# in-memory SQLite session), but importing app.main - which now pulls in
# the players router, and therefore app.core.db - fails collection if the
# env var is unset. Set a harmless default before any test module imports
# app code.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
