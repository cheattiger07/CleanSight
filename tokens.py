from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_token(email, salt="email-verify"):
    return _serializer().dumps(email, salt=salt)


def confirm_token(token, salt="email-verify", max_age=86400):
    """Return the email inside the token, or None if invalid or expired (default 24h)."""
    try:
        return _serializer().loads(token, salt=salt, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None