"""ID generation helpers."""
from datetime import datetime, timezone
import secrets


def generate_claim_number() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"CLM-{ts}-{secrets.token_hex(3).upper()}"
