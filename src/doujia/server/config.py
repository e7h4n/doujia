import secrets

SECRET_KEY = secrets.token_hex(32)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
