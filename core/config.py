import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    system_a_api_key: str
    system_b_api_key: str
    transfer_signing_secret: str
    payload_ttl_seconds: int = 1800
    max_payload_bytes: int = 8_192
    environment: str = "production"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            system_a_api_key=os.getenv("SYSTEM_A_API_KEY", ""),
            system_b_api_key=os.getenv("SYSTEM_B_API_KEY", ""),
            transfer_signing_secret=os.getenv("TRANSFER_SIGNING_SECRET", ""),
            payload_ttl_seconds=_get_int_env("PAYLOAD_TTL_SECONDS", 1800),
            max_payload_bytes=_get_int_env("MAX_PAYLOAD_BYTES", 8_192),
            environment=os.getenv("ENVIRONMENT", "production"),
        )


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default


settings = Settings.from_env()
