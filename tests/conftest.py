import os

from cryptography.fernet import Fernet

os.environ["SENTRY_ENABLED"] = "false"
os.environ["HH_TOKEN_ENCRYPT_KEY"] = Fernet.generate_key().decode()
os.environ["HH_REDIRECT_URL"] = "http://localhost:3101/auth/hh/"
os.environ["HH_CLIENT_ID"] = "test-client"
os.environ["HH_CLIENT_SECRET"] = "test-secret"
