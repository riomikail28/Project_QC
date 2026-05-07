"""
Redis Cache Implementation for QC Central Kitchen
Multi-level caching with Redis and in-memory fallback
"""

import json
import logging
import pickle
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
import os
from functools import wraps

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available, using in-memory cache only")

logger = logging.getLogger("qc.cache")

class CacheManager:
    """Multi-level cache manager with Redis and in-memory fallback"""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}  # Fallback in-memory cache
        self.memory_expiry = {}
        self.default_ttl = 300  # 5 minutes
        
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            return
        
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache")
            self.redis_client = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        # Try Redis first
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    # Try to deserialize as JSON first, then pickle
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        try:
                            return pickle.loads(value.encode('latin1'))
                        except:
                            return value
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to memory cache
        if key in self.memory_cache:
            if self._is_memory_expired(key):
                self.delete(key)
                return default
            return self.memory_cache[key]
        
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        success = False
        
        # Try Redis first
        if self.redis_client:
            try:
                # Serialize value
                if isinstance(value, (dict, list)):
                    serialized = json.dumps(value, default=str)
                elif isinstance(value, (int, float, str, bool)):
                    serialized = str(value)
                else:
                    serialized = pickle.dumps(value).decode('latin1')
                
                result = self.redis_client.setex(key, ttl, serialized)
                success = bool(result)
                
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Always store in memory cache as backup
        self.memory_cache[key] = value
        self.memory_expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)
        
        return success
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        success = False
        
        # Try Redis
        if self.redis_client:
            try:
                result = self.redis_client.delete(key)
                success = bool(result)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
        
        # Remove from memory cache
        self.memory_cache.pop(key, None)
        self.memory_expiry.pop(key, None)
        
        return success
    
    def clear(self, pattern: Optional[str] = None) -> bool:
        """Clear cache keys"""
        success = False
        
        # Try Redis
        if self.redis_client:
            try:
                if pattern:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        result = self.redis_client.delete(*keys)
                        success = bool(result)
                else:
                    result = self.redis_client.flushdb()
                    success = bool(result)
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
        
        # Clear memory cache
        if pattern:
            keys_to_remove = [k for k in self.memory_cache.keys() if pattern in k]
            for key in keys_to_remove:
                self.memory_cache.pop(key, None)
                self.memory_expiry.pop(key, None)
        else:
            self.memory_cache.clear()
            self.memory_expiry.clear()
        
        return success
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        # Try Redis
        if self.redis_client:
            try:
                return bool(self.redis_client.exists(key))
            except Exception as e:
                logger.warning(f"Redis exists error: {e}")
        
        # Check memory cache
        return key in self.memory_cache and not self._is_memory_expired(key)
    
    def _is_memory_expired(self, key: str) -> bool:
        """Check if memory cache key is expired"""
        if key not in self.memory_expiry:
            return True
        return datetime.utcnow() > self.memory_expiry[key]
    
    def cleanup_memory(self):
        """Clean up expired memory cache entries"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, expiry in self.memory_expiry.items()
            if now > expiry
        ]
        
        for key in expired_keys:
            self.memory_cache.pop(key, None)
            self.memory_expiry.pop(key, None)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "memory_cache_size": len(self.memory_cache),
            "redis_available": self.redis_client is not None
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats.update({
                    "redis_connected_clients": info.get("connected_clients", 0),
                    "redis_used_memory": info.get("used_memory_human", "N/A"),
                    "redis_keyspace_hits": info.get("keyspace_hits", 0),
                    "redis_keyspace_misses": info.get("keyspace_misses", 0)
                })
            except Exception as e:
                logger.warning(f"Redis stats error: {e}")
        
        return stats

# Singleton instance
cache_manager = CacheManager()

# Decorators for caching
def cache_result(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{f.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return decorated_function
    return decorator

def cache_query(ttl: int = 300, table: str = ""):
    """Decorator to cache database queries"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key for database query
            query_params = {
                'table': table,
                'args': args,
                'kwargs': sorted(kwargs.items())
            }
            cache_key = f"query:{hash(str(query_params))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute query and cache result
            result = f(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return decorated_function
    return decorator

class CacheInvalidation:
    """Cache invalidation utilities"""
    
    @staticmethod
    def invalidate_dashboard():
        """Invalidate dashboard cache"""
        cache_manager.clear("dashboard")
    
    @staticmethod
    def invalidate_device(device_id: str):
        """Invalidate device-specific cache"""
        patterns = [f"device:{device_id}", f"temperature:{device_id}"]
        for pattern in patterns:
            cache_manager.clear(pattern)
    
    @staticmethod
    def invalidate_alerts():
        """Invalidate alerts cache"""
        cache_manager.clear("alerts")
    
    @staticmethod
    def invalidate_all():
        """Invalidate all cache"""
        cache_manager.clear()