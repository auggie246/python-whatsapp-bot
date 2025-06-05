import os
import functools
from typing import List

def require_env_vars(provider_name: str, required_vars: List[str]):
    """Decorator to check for required environment variables for a given provider."""
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
