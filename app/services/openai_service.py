"""
openai_service.py
-----------------
Exports `generate_response()` for the WhatsApp bot but uses the *public*
OpenAI API (gpt\u20113.5\u2011turbo, gpt\u20114\u2011turbo, etc.) through the official `openai`
package (\u22651.0).

Environment variables
---------------------
OPENAI_API_KEY        \u2013 required
OPENAI_MODEL_NAME     \u2013 required (e.g. gpt-3.5-turbo, gpt-4o-mini, ...)
OPENAI_API_BASE       \u2013 optional, override if using a proxy / mirror
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
#   Client initialisation
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
_api_key = os.getenv("OPENAI_API_KEY")
_model_name = os.getenv("OPENAI_MODEL_NAME")  # e.g. gpt-3.5-turbo
_api_base = os.getenv("OPENAI_API_BASE")  # optional

if not (_api_key and _model_name):
    raise RuntimeError(
        "OPENAI_API_KEY and OPENAI_MODEL_NAME environment variables must be set."
    )

# Construct the client (base_url only if provided)
_client = OpenAI(
    api_key=_api_key,
    base_url=_api_base or None,  # keeps default if unset
)

# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
#   Per\u2011contact conversation buffers
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
_CONV_HISTORY: Dict[str, List[Dict[str, str]]] = defaultdict(list)
_MAX_TURNS = 12  # keep roughly the last 12 user/assistant pairs


def _append_to_history(wa_id: str, role: str, content: str) -> None:
    """Add a message to history and discard the oldest if buffer too big."""
    _CONV_HISTORY[wa_id].append({"role": role, "content": content})
    excess = len(_CONV_HISTORY[wa_id]) - _MAX_TURNS * 2
    if excess > 0:
        _CONV_HISTORY[wa_id] = _CONV_HISTORY[wa_id][excess:]


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
#   Public API
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
def generate_response(
    message_body: str,
    wa_id: str,
    name: str,
    system_message: str | None = None,
) -> str:
    """
    Generate an assistant reply for the WhatsApp user identified by *wa_id*.
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

    # 3) call OpenAI
    response = _client.chat.completions.create(
        model=_model_name,
        messages=_CONV_HISTORY[wa_id],
        temperature=0.7,
        max_tokens=512,
    )

    assistant_text = response.choices[0].message.content.strip()

    # 4) save assistant reply
    _append_to_history(wa_id, "assistant", assistant_text)

    return assistant_text


# -----------------------------------------------------------------
# Optional embeddings helper (parity with earlier version)
# -----------------------------------------------------------------
_embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-small")


def embed(text: str) -> List[float]:
    """
    Return an embedding vector for *text*. Not used by WhatsApp bot but
    provided for completeness.
    """
    resp = _client.embeddings.create(model=_embedding_model, input=[text])
    return resp.data[0].embedding
