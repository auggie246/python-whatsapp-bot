import os
from collections import defaultdict
from typing import List, Dict

from openai import AzureOpenAI, OpenAI
from dotenv import load_dotenv
from flask import current_app # Still needed for logger and context for decorator
from app.decorators.service_decorators import select_service_impl
# Removed: from app.config import get_yaml_config

# Load environment variables from .env file
load_dotenv()

# Global variables for the OpenAI client and model names
_client = None
_chat_model_name: str | None = None
_embedding_model_name: str | None = None

# Conversation history
_CONV_HISTORY: Dict[str, List[Dict[str, str]]] = defaultdict(list)
_MAX_TURNS = 12

def initialize_openai_client():
    """
    Initializes the OpenAI client based on the Flask app's configuration.
    This function must be called before any service function is used.
    """
    global _client, _chat_model_name, _embedding_model_name

    if not current_app: # current_app is essential for app.config and logger
        raise RuntimeError("Flask app context is required to initialize OpenAI client.")

    # Get provider from current_app.config (loaded from environment variables)
    provider = current_app.config.get("OPENAI_SERVICE_PROVIDER", "openai")
    # Removed try-except block for get_yaml_config

    if provider == "azure":
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

        if not all([azure_endpoint, azure_api_key, azure_deployment_name]):
            raise RuntimeError(
                "Azure OpenAI environment variables (AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME) are not fully set."
            )
        
        _client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-07-01-preview"),
        )
        _chat_model_name = azure_deployment_name
        _embedding_model_name = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", _chat_model_name)
        current_app.logger.info(f"Initialized Azure OpenAI client with deployment: {_chat_model_name}, embedding deployment: {_embedding_model_name}")

    elif provider == "openai":
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_model_name = os.getenv("OPENAI_MODEL_NAME")

        if not all([openai_api_key, openai_model_name]):
            raise RuntimeError(
                "OpenAI environment variables (OPENAI_API_KEY, OPENAI_MODEL_NAME) "
                "are not fully set."
            )
        
        _client = OpenAI(api_key=openai_api_key)
        _chat_model_name = openai_model_name
        _embedding_model_name = os.getenv("OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-small")
        current_app.logger.info(f"Initialized standard OpenAI client with model: {_chat_model_name}, embedding model: {_embedding_model_name}")

    else:
        raise ValueError(f"Unsupported OPENAI_SERVICE_PROVIDER: {provider}")


def _append_to_history(wa_id: str, role: str, content: str):
    """Appends a message to the conversation history for a given user."""
    user_history = _CONV_HISTORY[wa_id]
    if len(user_history) >= _MAX_TURNS * 2:  # Each turn has a user and assistant message
        user_history.pop(0)  # Remove the oldest message (user)
        user_history.pop(0)  # Remove the oldest message (assistant)
    user_history.append({"role": role, "content": content})


# Original select_service_impl decorator has been moved to app.decorators.service_decorators
# and is now imported.

@select_service_impl("azure")
def _generate_response_azure(message_body: str, wa_id: str, name: str, system_message: str | None = None) -> str:
    global _client, _chat_model_name
    if system_message is None:
        system_message = f"You are a friendly assistant named {name}."
    
    _append_to_history(wa_id, "user", message_body)
    
    messages_for_api = [{"role": "system", "content": system_message}] + _CONV_HISTORY[wa_id]

    current_app.logger.info(f"Generating Azure OpenAI response for {wa_id} with model {_chat_model_name}")
    completion = _client.chat.completions.create(
        model=_chat_model_name,  # Azure uses deployment name as model
        messages=messages_for_api,
        temperature=0.7,
        max_tokens=150,
    )
    response = completion.choices[0].message.content
    _append_to_history(wa_id, "assistant", response)
    return response


@select_service_impl("openai")
def _generate_response_openai(message_body: str, wa_id: str, name: str, system_message: str | None = None) -> str:
    global _client, _chat_model_name
    if system_message is None:
        system_message = f"You are a friendly assistant named {name}."

    _append_to_history(wa_id, "user", message_body)

    messages_for_api = [{"role": "system", "content": system_message}] + _CONV_HISTORY[wa_id]
    
    current_app.logger.info(f"Generating OpenAI response for {wa_id} with model {_chat_model_name}")
    completion = _client.chat.completions.create(
        model=_chat_model_name,
        messages=messages_for_api,
        temperature=0.7,
        max_tokens=150,
    )
    response = completion.choices[0].message.content
    _append_to_history(wa_id, "assistant", response)
    return response


def generate_response(message_body: str, wa_id: str, name: str, system_message: str | None = None) -> str:
    """
    Generates a chat response using the configured OpenAI service.
    """
    # current_app check is important for app.config
    if not current_app: 
        raise RuntimeError("Flask app context is required for generate_response.")

    # Get provider from current_app.config
    provider = current_app.config.get("OPENAI_SERVICE_PROVIDER", "openai")
    # Removed try-except block for get_yaml_config

    if _client is None: # Ensure client is initialized if not already
        current_app.logger.warning("OpenAI client was not initialized prior to generate_response call. Initializing now.")
        initialize_openai_client()

    if provider == "azure":
        return _generate_response_azure(message_body, wa_id, name, system_message)
    elif provider == "openai":
        return _generate_response_openai(message_body, wa_id, name, system_message)
    else:
        current_app.logger.error(f"Unsupported OPENAI_SERVICE_PROVIDER: {provider}")
        raise ValueError(f"Unsupported OPENAI_SERVICE_PROVIDER: {provider}")


@select_service_impl("azure")
def _embed_azure(text: str) -> List[float]:
    global _client, _embedding_model_name
    current_app.logger.info(f"Generating Azure OpenAI embedding with deployment {_embedding_model_name}")
    response = _client.embeddings.create(
        model=_embedding_model_name, # Azure uses deployment name
        input=text
    )
    return response.data[0].embedding


@select_service_impl("openai")
def _embed_openai(text: str) -> List[float]:
    global _client, _embedding_model_name
    current_app.logger.info(f"Generating OpenAI embedding with model {_embedding_model_name}")
    response = _client.embeddings.create(
        model=_embedding_model_name,
        input=text
    )
    return response.data[0].embedding


def embed(text: str) -> List[float]:
    """
    Generates an embedding for the given text using the configured OpenAI service.
    """
    if not current_app: # current_app check for app.config
        raise RuntimeError("Flask app context is required for embed.")

    # Get provider from current_app.config
    provider = current_app.config.get("OPENAI_SERVICE_PROVIDER", "openai")
    # Removed try-except block for get_yaml_config

    if _client is None: # Ensure client is initialized if not already
        current_app.logger.warning("OpenAI client was not initialized prior to embed call. Initializing now.")
        initialize_openai_client()

    if provider == "azure":
        return _embed_azure(text)
    elif provider == "openai":
        return _embed_openai(text)
    else:
        current_app.logger.error(f"Unsupported OPENAI_SERVICE_PROVIDER: {provider}")
        raise ValueError(f"Unsupported OPENAI_SERVICE_PROVIDER: {provider}")

# Example of how to clear history for a user (optional, can be called from elsewhere)
def clear_conversation_history(wa_id: str):
    """Clears the conversation history for a specific user."""
    if wa_id in _CONV_HISTORY:
        del _CONV_HISTORY[wa_id]
        current_app.logger.info(f"Conversation history cleared for {wa_id}")

# Example of how to get history (optional)
def get_conversation_history(wa_id: str) -> List[Dict[str, str]]:
    """Retrieves the conversation history for a specific user."""
    return _CONV_HISTORY[wa_id]

# It's good practice to log the chosen provider at startup,
# which is handled in initialize_openai_client.
# Ensure initialize_openai_client() is called from your Flask app factory (e.g., create_app).
# Example:
# from .services import combined_openai_service
# def create_app():
#     app = Flask(__name__)
#     # ... other configurations ...
#     with app.app_context():
#          combined_openai_service.initialize_openai_client()
#     return app
