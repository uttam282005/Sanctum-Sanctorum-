import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if "SANCTUM_DATABASE_URL" not in os.environ:
    os.environ["SANCTUM_DATABASE_URL"] = "sqlite:////tmp/sanctum.db"

from app.main import app
