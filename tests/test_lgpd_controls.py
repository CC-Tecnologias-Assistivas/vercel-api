import copy
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
from argon2 import PasswordHasher

from core.config import Settings
from core.security import KEY_PATTERN
from repositories.supabase_payload_repository import SupabasePayloadRepository
from repositories.supabase_credential_repository import SupabaseCredentialRepository
from schemas.payload_examples import CVTUG_PAYLOAD_EXAMPLE
from services.payload_sanitizer import sanitize_payload


class LgpdControlsTest(unittest.TestCase):
    def test_production_configuration_requires_secrets(self):
        settings = Settings(
            "", "", "payloads", "organizations", "api_credentials", "audit_events", "payload-pdfs"
        )
        with self.assertRaises(RuntimeError):
            settings.validate_for_runtime()

    def test_legacy_fixed_key_is_not_a_valid_credential(self):
        self.assertIsNone(KEY_PATTERN.fullmatch("rehabeasy-system-a"))
        self.assertIsNotNone(KEY_PATTERN.fullmatch("key_id_123456.secret_" + "x" * 32))

    def test_schema_sanitizer_discards_unknown_fields_and_pseudonymizes_patient(self):
        payload = copy.deepcopy(CVTUG_PAYLOAD_EXAMPLE)
        payload["unexpected"] = "do not persist"
        payload["records"][0]["source_document"] = "do not persist"
        original_external_id = payload["records"][0]["patient"]["external_id"]
        settings = Settings(
            "", "", "payloads", "organizations", "api_credentials", "audit_events", "payload-pdfs",
            patient_pseudonymization_key="p" * 32,
            environment="test",
        )

        sanitized = sanitize_payload(payload, settings)

        self.assertNotIn("unexpected", sanitized)
        self.assertNotIn("source_document", sanitized["records"][0])
        self.assertNotEqual(
            original_external_id,
            sanitized["records"][0]["patient"]["external_id"],
        )
        self.assertEqual(32, len(sanitized["records"][0]["patient"]["external_id"]))

    def test_consumption_query_is_scoped_to_organization(self):
        settings = Settings(
            "https://example.supabase.co", "service-secret", "payloads", "organizations",
            "api_credentials", "audit_events", "payload-pdfs", environment="test",
        )
        repository = SupabasePayloadRepository(settings)
        response = httpx.Response(200, json=[])

        with patch("httpx.request", return_value=response) as request:
            result = repository.consume_payload(
                "payload-1", datetime.now(timezone.utc), "org-a"
            )

        self.assertIsNone(result)
        request_url = request.call_args.args[1]
        self.assertIn("organization_id=eq.org-a", request_url)
        self.assertIn("consumed_at=is.null", request_url)

    def test_credential_requires_argon2_secret_and_active_organization(self):
        secret = "s" * 43
        settings = Settings(
            "https://example.supabase.co", "service-secret", "payloads", "organizations",
            "api_credentials", "audit_events", "payload-pdfs", credential_hash_pepper="p" * 32,
            environment="test",
        )
        credential_response = httpx.Response(
            200,
            json=[{
                "id": "credential-a",
                "organization_id": "org-a",
                "role": "consumer",
                "secret_hash": PasswordHasher().hash(secret + settings.credential_hash_pepper),
                "expires_at": None,
            }],
        )
        organization_response = httpx.Response(200, json=[{"id": "org-a"}])

        with patch("httpx.request", side_effect=[credential_response, organization_response]):
            result = SupabaseCredentialRepository(settings).authenticate(
                "key_id_123456", secret, "consumer"
            )

        self.assertEqual("org-a", result["organization_id"])
        self.assertEqual("consumer", result["role"])

    def test_new_secret_key_is_sent_only_as_apikey(self):
        settings = Settings(
            "https://example.supabase.co", "sb_secret_test", "payloads", "organizations",
            "api_credentials", "audit_events", "payload-pdfs", environment="test",
        )

        headers = settings.supabase_request_headers()

        self.assertEqual("sb_secret_test", headers["apikey"])
        self.assertNotIn("Authorization", headers)

    def test_legacy_service_role_key_keeps_bearer_compatibility(self):
        settings = Settings(
            "https://example.supabase.co", "legacy-service-role", "payloads", "organizations",
            "api_credentials", "audit_events", "payload-pdfs", environment="test",
        )

        headers = settings.supabase_request_headers()

        self.assertEqual("Bearer legacy-service-role", headers["Authorization"])


if __name__ == "__main__":
    unittest.main()
