import redis
from fastapi import Request, HTTPException, status
from app.core.config import settings

_redis_client = None

def get_redis_client():
    """Lazily initializes and returns the Redis client with connection timeouts."""
    global _redis_client
    if _redis_client is None:
        try:
            redis_url = settings.REDIS_URL or ""
            # Strip parameters like ssl_cert_reqs from redis URL to initialize pure redis connection
            if "?" in redis_url:
                redis_url = redis_url.split("?")[0]
            _redis_client = redis.Redis.from_url(
                redis_url, 
                socket_timeout=3.0, 
                socket_connect_timeout=3.0,
                retry_on_timeout=True
            )
            # Test ping
            _redis_client.ping()
        except Exception as e:
            print(f"[RATE LIMITER] Failed to connect to Redis: {e}")
            _redis_client = None
    return _redis_client

class RateLimiter:
    """
    Fixed-window rate limiter dependency using Redis.
    Limits requests based on client host IP and target endpoint path.
    """
    def __init__(self, times: int = 10, seconds: int = 60):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request):
        client = get_redis_client()
        if client is None:
            # Fallback gracefully if Redis is down (soft-failure)
            return

        ip = request.client.host if request.client else "127.0.0.1"
        endpoint = request.url.path
        redis_key = f"rate_limit:{ip}:{endpoint}"
        
        try:
            current = client.get(redis_key)
            
            if current is not None and int(current) >= self.times:
                ttl = client.ttl(redis_key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Too Many Requests",
                        "retry_after": ttl if ttl > 0 else self.seconds,
                        "message": f"Rate limit exceeded. Please try again in {ttl if ttl > 0 else self.seconds} seconds."
                    }
                )
            
            pipe = client.pipeline()
            pipe.incr(redis_key)
            if current is None:
                pipe.expire(redis_key, self.seconds)
            pipe.execute()
            
        except HTTPException as he:
            raise he
        except Exception as e:
            # Fallback gracefully in case of Redis connection drops during execution
            print(f"[RATE LIMITER] Error executing rate limit logic: {e}")
            return
