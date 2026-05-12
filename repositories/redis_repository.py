from upstash_redis import Redis

from core.config import Settings
from core.errors import RedisUnavailableError


class RedisPayloadRepository:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @classmethod
    def from_settings(cls, settings: Settings) -> "RedisPayloadRepository":
        redis = Redis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token,
            allow_telemetry=False,
        )
        return cls(redis=redis)

    def set_payload(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self._redis.set(key, value, ex=ttl_seconds)
        except Exception as exc:
            raise RedisUnavailableError from exc

    def getdel_payload(self, key: str) -> str | None:
        try:
            return self._redis.getdel(key)
        except Exception as exc:
            raise RedisUnavailableError from exc

    def payload_exists(self, key: str) -> bool:
        try:
            return bool(self._redis.exists(key))
        except Exception as exc:
            raise RedisUnavailableError from exc

    def get_ttl(self, key: str) -> int:
        try:
            return int(self._redis.ttl(key))
        except Exception as exc:
            raise RedisUnavailableError from exc
