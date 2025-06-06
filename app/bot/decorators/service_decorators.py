"""Decorators for service layer functionality.

This module provides decorators that can be used by service modules
to encapsulate common checks or behaviors, such as ensuring
necessary environment variables are set.
"""
import os
import functools
from typing import List

def require_env_vars(provider_name: str, required_vars: List[str]):
    """Decorator factory to ensure required environment variables are set for a service.

    This factory takes a provider name and a list of required environment variable
    names. It returns a decorator that, when applied to a function, will check
    if all specified environment variables are set. If not, it raises a
    RuntimeError.

    Args:
        provider_name (str): The name of the provider or configuration context
            (e.g., "AZURE", "OPENAI") for which variables are being checked.
            Used in the error message.
        required_vars (List[str]): A list of strings, where each string is the
            name of an environment variable that must be set.

    Returns:
        Callable: A decorator function that can be applied to other functions.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise RuntimeError(
                    f"For CHAT_API_PROVIDER='{provider_name}', the following environment "
                    f"variables must be set: {', '.join(missing_vars)}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
