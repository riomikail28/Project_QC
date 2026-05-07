"""
Performance Middleware for QC Central Kitchen
Implements request logging, rate limiting, and performance monitoring
"""

import time
import logging
from functools import wraps
from flask import request, g, jsonify
from collections import defaultdict
import redis
import os

# Configure logging
logger = logging.getLogger("qc.performance")

# Redis for rate limiting and caching
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = None

try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
except Exception as e:
    logger.warning(f"Redis not available: {e}")

class PerformanceMiddleware:
    def __init__(self, app):
        self.app = app
        self.request_times = defaultdict(list)
        self.rate_limits = defaultdict(int)
        self.init_app(app)

    def init_app(self, app):
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
    def before_request(self):
        g.start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID', 'unknown')
        
        # Rate limiting
        client_ip = request.remote_addr
        if redis_client:
            key = f"rate_limit:{client_ip}"
            requests = redis_client.incr(key)
            redis_client.expire(key, 60)  # 1 minute window
            
            if requests > 100:  # Max 100 requests per minute
                return jsonify({
                    "error": "Rate limit exceeded",
                    "limit": 100,
                    "window": "1 minute"
                }), 429

    def after_request(self, response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            endpoint = request.endpoint or 'unknown'
            
            # Log slow requests
            if duration > 1.0:  # Log requests taking more than 1 second
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.3f}s (IP: {request.remote_addr})"
                )
            
            # Store metrics
            self.request_times[endpoint].append(duration)
            if len(self.request_times[endpoint]) > 100:
                self.request_times[endpoint] = self.request_times[endpoint][-50:]
            
            # Add performance headers
            response.headers['X-Response-Time'] = f"{duration:.3f}"
            response.headers['X-Request-ID'] = g.request_id
            
        return response

def cache_response(ttl=300):
    """Decorator to cache response data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not redis_client:
                return f(*args, **kwargs)
                
            cache_key = f"cache:{request.endpoint}:{request.url}"
            cached = redis_client.get(cache_key)
            
            if cached:
                return jsonify(cached)
            
            response = f(*args, **kwargs)
            
            # Cache only successful responses
            if hasattr(response, 'status_code') and response.status_code == 200:
                redis_client.setex(cache_key, ttl, response.get_json())
            
            return response
        return decorated_function
    return decorator

def validate_request():
    """Validate and sanitize incoming requests"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check content length
            if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB limit
                return jsonify({"error": "Request too large"}), 413
            
            # Validate JSON for POST/PUT requests
            if request.method in ['POST', 'PUT', 'PATCH'] and request.is_json:
                try:
                    request.get_json()
                except Exception as e:
                    return jsonify({"error": "Invalid JSON"}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def performance_monitor(metric_name):
    """Monitor performance of specific operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log performance metrics
                logger.info(f"Performance: {metric_name} took {duration:.3f}s")
                
                # Store in Redis for monitoring
                if redis_client:
                    key = f"perf:{metric_name}"
                    redis_client.lpush(key, duration)
                    redis_client.ltrim(key, 0, 999)  # Keep last 1000 measurements
                    redis_client.expire(key, 3600)  # 1 hour expiry
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Performance error: {metric_name} failed after {duration:.3f}s - {e}")
                raise
        return decorated_function
    return decorator