import os
import tempfile
from pathlib import Path

# Set before importing app modules; never load the developer's database or secrets.
_test_directory = tempfile.TemporaryDirectory(prefix="open-analytics-tests-")
os.environ["DUCKDB_PATH"] = str(Path(_test_directory.name) / "test.duckdb")
os.environ["JWT_SECRET_KEY"] = "isolated-test-secret-never-use-in-production"
os.environ["APP_ENV"] = "test"
os.environ["QUANT_REFRESH_ON_STARTUP"] = "false"
