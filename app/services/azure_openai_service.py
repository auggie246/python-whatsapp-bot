"""
azure_openai_service.py
-----------------------
Implements the same `generate_response()` function that the WhatsApp bot
already calls, but routes the request to an Azure OpenAI deployment
via the official `openai` package (≥1.0).

Expected environment variables
------------------------------
AZURE_OPENAI_ENDPOINT                    # https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY                     # key from the portal
AZURE_OPENAI_DEPLOYMENT_NAME             # chat‑model deployment (e.g. gpt4‑turbo)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME   # optional, if you use embeddings
AZURE_OPENAI_API_VERSION                 # optional, default 2024‑02‑15-preview
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List
from dotenv import load_dotenv

from openai import AzureOpenAI

load_dotenv()

# ──────────────────────────────────────────────────────────────────────
#   Initialise a single Azure OpenAI client
# ──────────────────────────────────────────────────────────────────────
_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
_api_key = os.getenv("AZURE_OPENAI_API_KEY")
_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

if not (_endpoint and _api_key and _deployment_name):
    raise RuntimeError(
        "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and "
        "AZURE_OPENAI_DEPLOYMENT_NAME must be set."
    )

_client = AzureOpenAI(
    api_key=_api_key,
    api_version=_api_version,
    azure_endpoint=_endpoint,
)

# ──────────────────────────────────────────────────────────────────────
#   In‑memory conversation buffer per WhatsApp contact
#   (keeps the last N pairs to preserve context)
# ──────────────────────────────────────────────────────────────────────
_CONV_HISTORY: Dict[str, List[Dict[str, str]]] = defaultdict(list)
_MAX_TURNS = 12  # keeps roughly the last _MAX_TURNS user/assistant pairs


def _append_to_history(wa_id: str, role: str, content: str) -> None:
    """Helper that appends a message and trims the buffer if necessary."""
    _CONV_HISTORY[wa_id].append({"role": role, "content": content})
    # Trim to the last N*2 messages (user+assistant per turn)
    excess = len(_CONV_HISTORY[wa_id]) - _MAX_TURNS * 2
    if excess > 0:
        _CONV_HISTORY[wa_id] = _CONV_HISTORY[wa_id][excess:]


# ──────────────────────────────────────────────────────────────
#   Public API
# ──────────────────────────────────────────────────────────────
def generate_response(
    message_body: str,
    wa_id: str,
    name: str,
    system_message: str | None = None,
) -> str:
    """
    Produce the assistant’s reply for a WhatsApp user.

    Parameters
    ----------
    message_body   : latest message text from the user
    wa_id          : WhatsApp ID (contact) – used as context key
    name           : profile name – inserted into the default system prompt
    system_message : optional system prompt (overrides default for this call)

    Returns
    -------
    str : bot reply text
    """
    # 1. Decide what the system prompt should be
    if system_message is None:
        system_message = (
            "You are a helpful, concise assistant chatting on WhatsApp with "
            f"{name}. Keep answers short and conversational."
        )

    # 2. If it’s the first turn, seed the history with the system prompt
    #    or update it if the caller supplied a new system prompt
    if not _CONV_HISTORY[wa_id]:
        _CONV_HISTORY[wa_id].append({"role": "system", "content": system_message})
    elif _CONV_HISTORY[wa_id][0]["role"] == "system":
        _CONV_HISTORY[wa_id][0]["content"] = system_message

    # 3. Add the user’s message to history
    _append_to_history(wa_id, "user", message_body)

    # 4. Request completion from Azure OpenAI
    response = _client.chat.completions.create(
        model=_deployment_name,                  # deployment name, not model id
        messages=_CONV_HISTORY[wa_id],
        temperature=0.7,
        max_tokens=512,
    )

    bot_text = response.choices[0].message.content.strip()

    # 5. Store assistant reply
    _append_to_history(wa_id, "assistant", bot_text)

    return bot_text

# ---------------------------------------------------------------------
# Optional helper for embeddings (kept in case you used it elsewhere)
# ---------------------------------------------------------------------
_embedding_deployment = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", _deployment_name
)


def embed(text: str) -> List[float]:
    """
    Return an embedding vector for *text*.  Not used by WhatsApp bot, but
    provided for parity with the original service module.
    """
    response = _client.embeddings.create(model=_embedding_deployment, input=[text])
    return response.data[0].embedding