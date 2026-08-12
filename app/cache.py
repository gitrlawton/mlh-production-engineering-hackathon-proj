import os
import redis

redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", 6379))

cache = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=0,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)
