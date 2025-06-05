"""
openai_service.py
-----------------
Exports `generate_response()` for the WhatsApp bot.
Uses a configurable chat API provider (e.g., public OpenAI, Azure OpenAI),
selected via the CHAT_API_PROVIDER environment variable.

Environment variables
---------------------
CHAT_API_PROVIDER: "OPENAI" or "AZURE" (required, defaults to "OPENAI")
                     Determines which chat API service to use.

If CHAT_API_PROVIDER="OPENAI":
  OPENAI_API_KEY        – required
  OPENAI_MODEL_NAME     – required (e.g. gpt-3.5-turbo, gpt-4o-mini, ...)
  OPENAI_API_BASE       – optional, override if using a proxy / mirror
  OPENAI_EMBEDDING_MODEL_NAME – optional, defaults to "text-embedding-3-small"

If CHAT_API_PROVIDER="AZURE":
  AZURE_OPENAI_ENDPOINT         – required (https://<resource>.openai.azure.com)
  AZURE_OPENAI_API_KEY          – required (key from the portal)
  AZURE_OPENAI_DEPLOYMENT_NAME  – required (chat model deployment, e.g. gpt4-turbo)
  AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME – optional, if you use embeddings (defaults to chat deployment name)
  AZURE_OPENAI_API_VERSION      – optional, default "2024-02-15-preview"

Future providers (e.g., local vLLM) might require CHAT_API_PROVIDER="VLLM"
and specific variables like VLLM_API_BASE and VLLM_MODEL_NAME.
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List, Union

from dotenv import load_dotenv
from openai import OpenAI, AzureOpenAI # Import both
from ..decorators.service_decorators import require_env_vars

load_dotenv()

# ----------------------------------------------------------------------
#   Client Initialization (conditional based on provider)
# ----------------------------------------------------------------------
_client: Union[OpenAI, AzureOpenAI] # Type hint for the client object
_chat_model_or_deployment_id: str
_embedding_model_or_deployment_id: str


@require_env_vars(provider_name="AZURE", required_vars=[
    "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_NAME"
])
def _get_azure_config():
    """Retrieve Azure OpenAI specific configurations."""
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
    """Retrieve OpenAI specific configurations."""
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
    """Initializes and returns the API client and model/deployment IDs based on CHAT_API_PROVIDER."""
    provider = os.getenv("CHAT_API_PROVIDER", "OPENAI").upper()
    config = None

    if provider == "AZURE":
        config = _get_azure_config()
    elif provider == "OPENAI":
        config = _get_openai_config()
    # elif provider == "VLLM":
    #     config = _get_vllm_config()
    else:
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
    """Add a message to history and discard the oldest if buffer too big."""
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
    """
    Generate an assistant reply for the WhatsApp user identified by *wa_id*.
    Uses the configured chat API service (public OpenAI, Azure OpenAI, etc.).
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
    """
    Return an embedding vector for *text*. Not used by WhatsApp bot but
    provided for completeness. Uses the configured chat API service.
    """
    resp = _client.embeddings.create(
        model=_embedding_model_or_deployment_id, # Use the unified variable
        input=[text]
    )
    return resp.data[0].embedding
