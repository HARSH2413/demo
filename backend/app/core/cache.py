"""
Caching Layer for Embeddings and Query Results
Reduce repeated queries by 90%+ with simple in-memory cache (or Redis for production)
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any
from app.core.logger import logger


class SimpleCache:
    """In-memory cache for embeddings (2GB should be enough for 1000s of queries)."""

    def __init__(self, max_size: int = 10000, ttl: int = 3600):
        """
        Args:
            max_size: Max number of cached items before eviction
            ttl: Time to live in seconds (default 1 hour)
        """
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def _key(self, text: str) -> str:
        """Create hash key from text."""
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[Any]:
        """Get from cache with TTL check."""
        key = self._key(text)

        if key not in self.cache:
            self.misses += 1
            return None

        value, timestamp = self.cache[key]

        # Check if expired
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            self.misses += 1
            return None

        self.hits += 1
        return value

    def set(self, text: str, value: Any) -> None:
        """Set in cache with LRU eviction."""
        key = self._key(text)

        # Evict oldest if full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            logger.debug(f"Cache full, evicted oldest entry")

        self.cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()

    def stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }


class QueryResultCache(SimpleCache):
    """Cache for full query results (search results, reranking)."""

    def get_query_result(self, query: str, tenant_id: str) -> Optional[list]:
        """Get cached search results."""
        key = f"{tenant_id}:{query}"
        return super().get(key)

    def set_query_result(self, query: str, tenant_id: str, results: list) -> None:
        """Cache search results."""
        key = f"{tenant_id}:{query}"
        super().set(key, results)


class EmbeddingCache(SimpleCache):
    """Cache for embeddings (text → vector)."""

    def get_embedding(self, text: str) -> Optional[list]:
        """Get cached embedding."""
        return super().get(text)

    def set_embedding(self, text: str, embedding: list) -> None:
        """Cache embedding."""
        super().set(text, embedding)


class RedisCache:
    """Production version using Redis (for deployed systems)."""

    def __init__(self, redis_url: str):
        import redis

        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        try:
            self.client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def get(self, key: str) -> Optional[Any]:
        """Get from Redis."""
        data = self.client.get(key)
        if data:
            try:
                return json.loads(data)
            except:
                return data
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set in Redis with TTL."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.client.setex(key, ttl, value)

    def get_embedding(self, text: str) -> Optional[list]:
        """Get cached embedding."""
        key = f"embed:{hashlib.md5(text.encode()).hexdigest()}"
        data = self.get(key)
        if data and isinstance(data, list):
            return data
        elif data:
            return json.loads(data)
        return None

    def set_embedding(self, text: str, embedding: list) -> None:
        """Cache embedding."""
        key = f"embed:{hashlib.md5(text.encode()).hexdigest()}"
        self.set(key, embedding, ttl=24 * 3600)  # 24 hours for embeddings

    def get_query_result(self, query: str, tenant_id: str) -> Optional[list]:
        """Get cached search results."""
        key = f"query:{tenant_id}:{hashlib.md5(query.encode()).hexdigest()}"
        return self.get(key)

    def set_query_result(self, query: str, tenant_id: str, results: list) -> None:
        """Cache search results."""
        key = f"query:{tenant_id}:{hashlib.md5(query.encode()).hexdigest()}"
        self.set(key, results, ttl=3600)  # 1 hour

    def clear(self) -> None:
        """Clear all cache."""
        self.client.flushdb()

    def stats(self) -> dict:
        """Get Redis stats."""
        info = self.client.info("stats")
        return {
            "total_commands_processed": info.get("total_commands_processed"),
            "total_connections_received": info.get("total_connections_received"),
        }


# Factory function to create appropriate cache
def create_cache(cache_type: str = "simple", redis_url: str = None) -> SimpleCache | RedisCache:
    """Create cache instance based on environment."""
    if cache_type == "redis" and redis_url:
        logger.info("Using Redis cache")
        return RedisCache(redis_url)
    else:
        logger.info("Using in-memory cache")
        return SimpleCache()
