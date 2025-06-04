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

load_dotenv()

# ----------------------------------------------------------------------
#   Client Initialization (conditional based on provider)
# ----------------------------------------------------------------------
_client: Union[OpenAI, AzureOpenAI] # Type hint for the client object
_chat_model_or_deployment_id: str
_embedding_model_or_deployment_id: str

CHAT_API_PROVIDER = os.getenv("CHAT_API_PROVIDER", "OPENAI").upper()

if CHAT_API_PROVIDER == "AZURE":
    _endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    _api_key = os.getenv("AZURE_OPENAI_API_KEY")
    _api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    _chat_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    if not (_endpoint and _api_key and _chat_deployment_name):
        raise RuntimeError(
            "For CHAT_API_PROVIDER='AZURE', AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and "
            "AZURE_OPENAI_DEPLOYMENT_NAME must be set."
        )

    _client = AzureOpenAI(
        api_key=_api_key,
        api_version=_api_version,
        azure_endpoint=_endpoint,
    )
    _chat_model_or_deployment_id = _chat_deployment_name
    _embedding_model_or_deployment_id = os.getenv(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", _chat_deployment_name # Fallback to chat deployment
    )
elif CHAT_API_PROVIDER == "OPENAI":
    _api_key = os.getenv("OPENAI_API_KEY")
    _model_name = os.getenv("OPENAI_MODEL_NAME")
    _api_base = os.getenv("OPENAI_API_BASE") # optional

    if not (_api_key and _model_name):
        raise RuntimeError(
            "For CHAT_API_PROVIDER='OPENAI', OPENAI_API_KEY and OPENAI_MODEL_NAME "
            "environment variables must be set."
        )

    _client = OpenAI(
        api_key=_api_key,
        base_url=_api_base or None, # keeps default if unset
    )
    _chat_model_or_deployment_id = _model_name
    _embedding_model_or_deployment_id = os.getenv(
        "OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-small"
    )
# Example for a future VLLM provider (illustrative)
# elif CHAT_API_PROVIDER == "VLLM":
# _api_base = os.getenv("VLLM_API_BASE") # e.g., http://localhost:8000/v1
# _model_name = os.getenv("VLLM_MODEL_NAME") # e.g., mistralai/Mistral-7B-Instruct-v0.1
# if not (_api_base and _model_name):
# raise RuntimeError(
#             "For CHAT_API_PROVIDER='VLLM', VLLM_API_BASE and VLLM_MODEL_NAME must be set."
# )
# _client = OpenAI(
# api_key="DUMMY_KEY_IF_NOT_NEEDED", # VLLM might not need a key
# base_url=_api_base,
# )
# _chat_model_or_deployment_id = _model_name
#     _embedding_model_or_deployment_id = os.getenv("VLLM_EMBEDDING_MODEL_NAME", _model_name)
else:
    raise ValueError(
        f"Invalid CHAT_API_PROVIDER: '{CHAT_API_PROVIDER}'. "
        "Supported values are 'OPENAI' or 'AZURE'." # Update if VLLM is added
    )

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
