"""Security-related decorators for the Flask application.

This module provides decorators to help secure webhook endpoints,
primarily by validating request signatures.
"""
from functools import wraps
from flask import current_app, jsonify, request
import logging
import hashlib
import hmac

def validate_signature(payload: str, signature: str) -> bool:
    """Validates an incoming payload's signature.

    Compares the provided signature with an expected signature generated
    using the APP_SECRET and the payload.

    Args:
        payload (str): The raw request payload string to validate.
        signature (str): The signature string from the request
            (e.g., from 'X-Hub-Signature-256' header).

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    # Use the App Secret to hash the payload
    expected_signature = hmac.new(
        bytes(current_app.config["APP_SECRET"], "latin-1"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Check if the signature matches
    return hmac.compare_digest(expected_signature, signature)

def signature_required(f):
    """Decorator to validate the signature of incoming webhook requests.

    Ensures that requests are genuinely from Meta by checking the
    'X-Hub-Signature-256' header against a signature computed using
    the APP_SECRET.

    Args:
        f: The Flask view function to decorate.

    Returns:
        The decorated function, which will first perform signature validation
        before executing the original view function. Returns a 403 error
        if signature validation fails.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        signature = request.headers.get("X-Hub-Signature-256", "")[
            7:
        ]  # Removing 'sha256='
        if not validate_signature(request.data.decode("utf-8"), signature):
            logging.info("Signature verification failed!")
            return jsonify({"status": "error", "message": "Invalid signature"}), 403
        return f(*args, **kwargs)

    return decorated_function
