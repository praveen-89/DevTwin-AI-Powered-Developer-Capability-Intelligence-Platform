import os
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

os.environ["DATABASE_URL"] = "postgresql+asyncpg://u:p@localhost/db"
os.environ["SUPABASE_URL"] = "https://placeholder.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "anon"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "service"
os.environ["SECRET_KEY"] = "secret"
os.environ["GITHUB_APP_ID"] = "123"
os.environ["GITHUB_APP_SLUG"] = "app"
os.environ["GITHUB_CLIENT_ID"] = "client"
os.environ["GITHUB_CLIENT_SECRET"] = "secret"
os.environ["GITHUB_PRIVATE_KEY"] = pem
os.environ["GITHUB_REDIRECT_URL"] = "http://localhost/cb"
os.environ["GITHUB_STATE_ENCRYPTION_KEY"] = "N2F0d1VNb2h3Nnl4S3hZYmF0bzh1amV6dVpZcDJ2bXg="
os.environ["GITHUB_STATE_TTL_SECONDS"] = "600"

if __name__ == "__main__":
    pytest.main(["-v", "tests/"])
