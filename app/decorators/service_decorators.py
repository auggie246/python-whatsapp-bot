from flask import current_app # Necessary for accessing app.config

# Removed: from app.config import get_yaml_config
# No import for _client is present, which is correct.

def select_service_impl(required_provider_type: str):
    """
    Decorator factory to ensure that a function is called only if the
    application is configured (via app.config from environment variables)
    for the specified provider type.
    Client initialization is NOT checked here.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not current_app:
                # This check is crucial as current_app.config is used.
                print("ERROR: Flask app context is required for service decorator to access config.")
                raise RuntimeError("Flask app context is required for service decorator.")

            # Get provider from current_app.config, which is loaded from environment variables
            configured_provider = current_app.config.get("OPENAI_SERVICE_PROVIDER", "openai")
            
            if configured_provider != required_provider_type:
                error_message = (
                    f"Service is configured for '{configured_provider}' (via environment variable LLM_PROVIDER), "
                    f"but an implementation for '{required_provider_type}' (function: {func.__name__}) was called."
                )
                # Use current_app.logger if available, otherwise print
                if hasattr(current_app, 'logger'):
                    current_app.logger.error(error_message)
                else:
                    print(f"ERROR: {error_message}")
                raise RuntimeError(error_message)
            
            # Client initialization check was previously (and correctly) removed.
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
