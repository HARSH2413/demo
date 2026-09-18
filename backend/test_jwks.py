import jwt
from jwt import PyJWKClient
import sys

# The exact JWT from the user's logs
token = "eyJhbGciOiJFUzI1NiIsImtpZCI6ImJjMWVkNmY3LWJiNDctNGE3ZC1hZDA1LWI0ZTc2NDA4NGM2OCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3ZoYWp6cWVyZG55bmd2d3d1a2ZmLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3MDRhNjc0My0wODkzLTQwNGUtYWU2Yi0xNDhiNmYwNWFkNGUiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzg3MjQ4ODk2LCJpYXQiOjE3ODcyNDUyOTYsImVtYWlsIjoiaGFyc2htYWxva2FyOEBnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiaGFyc2htYWxva2FyOEBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSGFyc2ggTWFsb2thciIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiNzA0YTY3NDMtMDg5My00MDRlLWFlNmItMTQ4YjZmMDVhZDRlIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3ODcyNDA0Nzl9XSwic2Vzc2lvbl9pZCI6Ijk1YjJjMDUyLTc1Y2ItNDFhZi05NWJkLWFmNDdkY2NkMjY4MyIsImlzX2Fub255bW91cyI6ZmFsc2V9.wxYRnWKtRbGV_HG8quwBHFatZEB3WCbvVGp7u1gWLn6nVK6Jbs_GvyoINsYW4-7Mtd7q2w4OsCiyzv2vkQY8Eg"

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
