import jwt
from jwt import PyJWKClient
import sys

import os

# Get JWT from environment or command line, don't hardcode
token = os.environ.get("TEST_JWT", "")
if not token:
    print("Please set TEST_JWT environment variable.")
    sys.exit(1)

supabase_url = "https://vhajzqerdnyngvwwukff.supabase.co"
jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"

try:
    jwks_client = PyJWKClient(jwks_url)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256", "HS256"],
        audience="authenticated"
    )
    print("Success! Payload:", payload)
except Exception as e:
    print("Error:", e)
