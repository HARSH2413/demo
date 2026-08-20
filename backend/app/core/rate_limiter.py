"""
Rate limiter — reads limits from config so you can tune via .env.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Uses the caller's IP address for tracking.
# Behind a reverse proxy, configure X-Forwarded-For header parsing.
limiter = Limiter(key_func=get_remote_address)