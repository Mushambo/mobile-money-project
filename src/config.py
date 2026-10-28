"""Shared settings. Values come from environment variables (see .env.example).
Never commit real passwords: copy .env.example to .env and edit locally."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

DATA_DIR = Path(os.environ.get("MM_DATA_DIR", ROOT / "data"))        # CSVs stay local
IMPORT_DIR = Path(os.environ.get("MM_IMPORT_DIR", DATA_DIR / "neo4j_import"))
RESULTS_DIR = ROOT / "results"

PG_DSN = os.environ.get(
    "PG_DSN",
    "host=localhost port=5432 dbname=mobile_money user=postgres password=CHANGE_ME",
)
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "CHANGE_ME")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

STREAMS = ("customers", "accounts", "devices", "account_devices", "transfers")
