import os
from dataclasses import dataclass


DEFAULT_SYSTEM_A_API_KEY = "sistema-mobile"
DEFAULT_SYSTEM_B_API_KEY = "rehabeasy-sistema"


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_role_key: str
    supabase_payloads_table: str
    system_a_api_key: str
    system_b_api_key: str
    payload_ttl_seconds: int = 1800
    max_payload_bytes: int = 1_048_576
    environment: str = "production"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            supabase_payloads_table=os.getenv("SUPABASE_PAYLOADS_TABLE", "payloads"),
            system_a_api_key=os.getenv("SYSTEM_A_API_KEY", DEFAULT_SYSTEM_A_API_KEY),
            system_b_api_key=os.getenv("SYSTEM_B_API_KEY", DEFAULT_SYSTEM_B_API_KEY),
            payload_ttl_seconds=_get_int_env("PAYLOAD_TTL_SECONDS", 1800),
            max_payload_bytes=_get_int_env("MAX_PAYLOAD_BYTES", 1_048_576),
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
