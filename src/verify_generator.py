"""Section 9.2 - confirm the supplied generator is unchanged (SHA-256 against generator.sha256)."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
expected = (ROOT / "generator.sha256").read_text().split()[0]
actual = hashlib.sha256((ROOT / "mobile_money_generator.py").read_bytes()).hexdigest()
print(f"expected {expected}\nactual   {actual}\n{'UNCHANGED' if actual == expected else 'MODIFIED!'}")
