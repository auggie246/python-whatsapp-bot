"""Manages interactions with configurable chat API providers.

This module provides functionality to generate text responses and embeddings
using different chat APIs like OpenAI or Azure OpenAI. The specific provider
is determined by the CHAT_API_PROVIDER environment variable.

Key Environment Variables:
    CHAT_API_PROVIDER: Specifies the provider ("OPENAI" or "AZURE").
                       Defaults to "OPENAI".

    For CHAT_API_PROVIDER="OPENAI":
      OPENAI_API_KEY: Required.
      OPENAI_MODEL_NAME: Required (e.g., "gpt-3.5-turbo").
      OPENAI_API_BASE: Optional, for proxy/mirror.
      OPENAI_EMBEDDING_MODEL_NAME: Optional (defaults to "text-embedding-3-small").

    For CHAT_API_PROVIDER="AZURE":
      AZURE_OPENAI_ENDPOINT: Required (e.g., "https://<resource>.openai.azure.com").
      AZURE_OPENAI_API_KEY: Required.
      AZURE_OPENAI_DEPLOYMENT_NAME: Required (chat model deployment name).
      AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME: Optional (embedding deployment,
                                              defaults to chat deployment name).
      AZURE_OPENAI_API_VERSION: Optional (defaults to "2024-02-15-preview").
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List, Union

from dotenv import load_dotenv
from openai import OpenAI, AzureOpenAI # Import both
from app.decorators.service_decorators import require_env_vars

load_dotenv()

# ----------------------------------------------------------------------
#   Client Initialization (conditional based on provider)
# ----------------------------------------------------------------------
_client: Union[OpenAI, AzureOpenAI]
_chat_model_or_deployment_id: str
_embedding_model_or_deployment_id: str

@require_env_vars(provider_name="AZURE", required_vars=[
    "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_NAME"
])
def _get_azure_config():
    """Retrieve Azure OpenAI specific configurations.

    Reads environment variables specific to Azure OpenAI and returns a
    dictionary containing the client configuration, client class,
    and model/deployment IDs.

    Raises:
        RuntimeError: If essential Azure environment variables are not set
                      (handled by the @require_env_vars decorator).

    Returns:
        dict: Configuration details for AzureOpenAI client.
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    chat_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    embedding_deployment_name = os.getenv(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", chat_deployment_name
    )
    return {
        "client_config": {
            "api_key": api_key,
            "api_version": api_version,
            "azure_endpoint": endpoint,
        },
        "client_class": AzureOpenAI,
        "chat_model_id": chat_deployment_name,
        "embedding_model_id": embedding_deployment_name,
    }

@require_env_vars(provider_name="OPENAI", required_vars=["OPENAI_API_KEY", "OPENAI_MODEL_NAME"])
def _get_openai_config():
    """Retrieve OpenAI specific configurations.

    Reads environment variables specific to OpenAI and returns a
    dictionary containing the client configuration, client class,
    and model/deployment IDs.

    Raises:
        RuntimeError: If essential OpenAI environment variables are not set
                      (handled by the @require_env_vars decorator).

    Returns:
        dict: Configuration details for OpenAI client.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL_NAME")
    api_base = os.getenv("OPENAI_API_BASE") # optional
    embedding_model_name = os.getenv("OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-small")
    return {
        "client_config": {
            "api_key": api_key,
            "base_url": api_base or None,
        },
        "client_class": OpenAI,
        "chat_model_id": model_name,
        "embedding_model_id": embedding_model_name,
    }

# Example for a future VLLM provider (illustrative)
# @require_env_vars(provider_name="VLLM", required_vars=["VLLM_API_BASE", "VLLM_MODEL_NAME"])
# def _get_vllm_config():
#     """Retrieve VLLM specific configurations."""
#     api_base = os.getenv("VLLM_API_BASE")
#     model_name = os.getenv("VLLM_MODEL_NAME")
#     embedding_model_name = os.getenv("VLLM_EMBEDDING_MODEL_NAME", model_name)
#     return {
#         "client_config": {
#             "api_key": "DUMMY_KEY_IF_NOT_NEEDED",
#             "base_url": api_base,
#         },
#         "client_class": OpenAI, # Assuming VLLM uses OpenAI-compatible API
#         "chat_model_id": model_name,
#         "embedding_model_id": embedding_model_name,
#     }

def _initialize_client_and_models():
    """Initializes the API client and model/deployment IDs.

    Determines the chat API provider from the CHAT_API_PROVIDER
    environment variable, retrieves the corresponding configuration,
    and instantiates the API client.

    Raises:
        ValueError: If CHAT_API_PROVIDER is invalid.

    Returns:
        tuple: A tuple containing the initialized client object,
               the chat model/deployment ID, and the embedding
               model/deployment ID.
    """
    provider = os.getenv("CHAT_API_PROVIDER", "OPENAI").upper()
    match provider:
        case "AZURE":
            config = _get_azure_config()
        case "OPENAI":
            config = _get_openai_config()
        # case "VLLM": # Illustrative for future extension
        #     config = _get_vllm_config()
        case _:
            raise ValueError(
                f"Invalid CHAT_API_PROVIDER: '{provider}'. "
                "Supported values are 'OPENAI' or 'AZURE'." # Update if VLLM is added
            )

    client_class = config["client_class"]
    client = client_class(**config["client_config"])
    chat_model_id = config["chat_model_id"]
    embedding_model_id = config["embedding_model_id"]

    return client, chat_model_id, embedding_model_id

_client, _chat_model_or_deployment_id, _embedding_model_or_deployment_id = _initialize_client_and_models()

# ----------------------------------------------------------------------
#   In-memory conversation buffer (common logic)
# ----------------------------------------------------------------------
_CONV_HISTORY: Dict[str, List[Dict[str, str]]] = defaultdict(list)
_MAX_TURNS = 12  # keep roughly the last 12 user/assistant pairs

def _append_to_history(wa_id: str, role: str, content: str) -> None:
    """Appends a message to the conversation history for a user.

    Also ensures the history does not exceed a maximum number of turns,
    discarding the oldest messages if necessary.

    Args:
        wa_id (str): The WhatsApp ID of the user.
        role (str): The role of the message sender (e.g., "user", "assistant").
        content (str): The content of the message.
    """
    _CONV_HISTORY[wa_id].append({"role": role, "content": content})
    excess = len(_CONV_HISTORY[wa_id]) - _MAX_TURNS * 2
    if excess > 0:
        _CONV_HISTORY[wa_id] = _CONV_HISTORY[wa_id][excess:]

# ----------------------------------------------------------------------
#   Public API (common logic, uses initialized client and model/deployment ID)
# ----------------------------------------------------------------------
def generate_response(
    message_body: str,
    wa_id: str,
    name: str,
    system_message: str | None = None,
) -> str:
    """Generates an assistant reply using the configured chat API.

    Manages conversation history and system prompts.

    Args:
        message_body (str): The incoming message from the user.
        wa_id (str): The WhatsApp ID of the user.
        name (str): The name of the user.
        system_message (str | None, optional): An optional system message
            to guide the assistant. Defaults to a generic helpful assistant
            prompt.

    Returns:
        str: The generated assistant's response.
    """
    # 1) decide / update system prompt
    if system_message is None:
        system_message = (
            "You are a helpful, concise assistant chatting on WhatsApp with "
            f"{name}. Keep answers short and conversational."
        )

    if not _CONV_HISTORY[wa_id]:
        _CONV_HISTORY[wa_id].append({"role": "system", "content": system_message})
    elif _CONV_HISTORY[wa_id][0]["role"] == "system":
        _CONV_HISTORY[wa_id][0]["content"] = system_message

    # 2) add user message
    _append_to_history(wa_id, "user", message_body)

    # 3) call the configured Chat API
    response = _client.chat.completions.create(
        model=_chat_model_or_deployment_id, # Use the unified variable
        messages=_CONV_HISTORY[wa_id],
        temperature=0.7,
        max_tokens=512,
    )

    assistant_text = response.choices[0].message.content.strip()

    # 4) save assistant reply
    _append_to_history(wa_id, "assistant", assistant_text)

    return assistant_text

# -----------------------------------------------------------------
# Optional embeddings helper (common logic)
# -----------------------------------------------------------------
def embed(text: str) -> List[float]:
    """Generates an embedding vector for the given text.

    This function is not actively used by the main WhatsApp bot logic
    but is provided for completeness, utilizing the configured
    embedding model.

    Args:
        text (str): The text to embed.

    Returns:
        List[float]: The embedding vector for the text.
    """
    resp = _client.embeddings.create(
        model=_embedding_model_or_deployment_id, # Use the unified variable
        input=[text]
    )
    return resp.data[0].embedding
