import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_role_key: str
    supabase_payloads_table: str
    supabase_organizations_table: str
    supabase_credentials_table: str
    supabase_audit_table: str
    supabase_pdf_bucket: str
    payload_ttl_seconds: int = 1800
    consumed_payload_grace_seconds: int = 1800
    max_payload_bytes: int = 1_048_576
    max_pdf_bytes: int = 10_485_760
    pdf_signed_url_seconds: int = 1800
    credential_hash_pepper: str = ""
    patient_pseudonymization_key: str = ""
    maintenance_key: str = ""
    cron_secret: str = ""
    local_clinical_retention_days: int = 0
    environment: str = "production"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_service_role_key=(
                os.getenv("SUPABASE_SECRET_KEY", "")
                or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            ),
            supabase_payloads_table=os.getenv("SUPABASE_PAYLOADS_TABLE", "payloads"),
            supabase_organizations_table=os.getenv(
                "SUPABASE_ORGANIZATIONS_TABLE", "organizations"
            ),
            supabase_credentials_table=os.getenv(
                "SUPABASE_CREDENTIALS_TABLE", "api_credentials"
            ),
            supabase_audit_table=os.getenv("SUPABASE_AUDIT_TABLE", "audit_events"),
            supabase_pdf_bucket=os.getenv("SUPABASE_PDF_BUCKET", "payload-pdfs"),
            payload_ttl_seconds=_get_int_env("PAYLOAD_TTL_SECONDS", 1800),
            consumed_payload_grace_seconds=_get_int_env(
                "CONSUMED_PAYLOAD_GRACE_SECONDS", 1800
            ),
            max_payload_bytes=_get_int_env("MAX_PAYLOAD_BYTES", 1_048_576),
            max_pdf_bytes=_get_int_env("MAX_PDF_BYTES", 10_485_760),
            pdf_signed_url_seconds=_get_int_env("PDF_SIGNED_URL_SECONDS", 1800),
            credential_hash_pepper=os.getenv("CREDENTIAL_HASH_PEPPER", ""),
            patient_pseudonymization_key=os.getenv("PATIENT_PSEUDONYMIZATION_KEY", ""),
            maintenance_key=os.getenv("MAINTENANCE_KEY", ""),
            cron_secret=os.getenv("CRON_SECRET", ""),
            local_clinical_retention_days=_get_int_env(
                "LOCAL_CLINICAL_RETENTION_DAYS", 0
            )
            if os.getenv("LOCAL_CLINICAL_RETENTION_DAYS")
            else 0,
            environment=os.getenv("ENVIRONMENT", "production"),
        )

    def validate_for_runtime(self) -> None:
        if self.environment.lower() not in {"production", "staging"}:
            return

        required = {
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SECRET_KEY/SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            "CREDENTIAL_HASH_PEPPER": self.credential_hash_pepper,
            "PATIENT_PSEUDONYMIZATION_KEY": self.patient_pseudonymization_key,
            "MAINTENANCE_KEY": self.maintenance_key,
            "CRON_SECRET": self.cron_secret,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Configuracao de producao incompleta: " + ", ".join(missing)
            )

        if len(self.credential_hash_pepper) < 32:
            raise RuntimeError("CREDENTIAL_HASH_PEPPER precisa ter pelo menos 32 caracteres")
        if len(self.patient_pseudonymization_key) < 32:
            raise RuntimeError("PATIENT_PSEUDONYMIZATION_KEY precisa ter pelo menos 32 caracteres")
        if len(self.maintenance_key) < 32:
            raise RuntimeError("MAINTENANCE_KEY precisa ter pelo menos 32 caracteres")
        if len(self.cron_secret) < 16:
            raise RuntimeError("CRON_SECRET precisa ter pelo menos 16 caracteres")

    def supabase_request_headers(self) -> dict[str, str]:
        """Return headers compatible with both new and legacy Supabase keys."""
        headers = {
            "apikey": self.supabase_service_role_key,
            "Content-Type": "application/json",
        }
        # New sb_secret keys must not be sent as Authorization: Bearer because
        # they are opaque keys, not JWTs. Legacy service_role keys still need
        # the Bearer header for compatibility with existing deployments.
        if not self.supabase_service_role_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self.supabase_service_role_key}"
        return headers


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
