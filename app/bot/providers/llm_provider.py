"""LLM Provider for interacting with OpenAI-compatible APIs.

This module defines the LLMProvider class, which encapsulates all direct
interactions with the configured LLM service (e.g., OpenAI, Azure OpenAI).
It handles client initialization, API calls for chat completions (text and
multimodal), and embeddings. It also includes helper methods for interacting
with the WhatsApp Media API to retrieve image information and content.
"""
import os
import base64
import logging
import requests
from typing import List, Dict, Any, Union, Optional

from flask import current_app
from openai import OpenAI, AzureOpenAI
from app.bot.decorators.service_decorators import require_env_vars

logger = logging.getLogger(__name__)

class LLMProvider:
    """Provides an interface to a configured LLM service and media utilities."""

    def __init__(self):
        """Initializes the LLM client, model IDs, and media handling utilities."""
        self.client: Union[OpenAI, AzureOpenAI]
        self.chat_model_id: str
        self.embedding_model_id: str
        self._initialize_llm_client()
        logger.info(f"LLMProvider initialized for provider: {os.getenv('CHAT_API_PROVIDER', 'OPENAI').upper()}, Model: {self.chat_model_id}")

    @require_env_vars(provider_name="AZURE", required_vars=[
        "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_NAME"
    ])
    def _get_azure_config_internal(self) -> Dict[str, Any]:
        """Retrieves Azure OpenAI specific configurations. Internal use for initialization."""
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
    def _get_openai_config_internal(self) -> Dict[str, Any]:
        """Retrieves OpenAI specific configurations. Internal use for initialization."""
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

    @require_env_vars(provider_name="VLLM", required_vars=["VLLM_API_BASE", "VLLM_MODEL_NAME"])
    def _get_vllm_config_internal(self) -> Dict[str, Any]:
        """Retrieves vLLM specific configurations. Internal use for initialization."""
        api_base = os.getenv("VLLM_API_BASE")
        model_name = os.getenv("VLLM_MODEL_NAME")
        api_key = os.getenv("VLLM_API_KEY", "EMPTY")  # Default to "EMPTY" as per vLLM docs
        embedding_model_name = os.getenv("VLLM_EMBEDDING_MODEL_NAME", model_name)
        return {
            "client_config": {
                "base_url": api_base,
                "api_key": api_key,
            },
            "client_class": OpenAI,  # vLLM is OpenAI-compatible
            "chat_model_id": model_name,
            "embedding_model_id": embedding_model_name,
        }

    def _initialize_llm_client(self):
        """Initializes the API client and model IDs based on CHAT_API_PROVIDER."""
        provider = os.getenv("CHAT_API_PROVIDER", "OPENAI").upper()
        config_data: Optional[Dict[str, Any]] = None

        if provider == "AZURE":
            config_data = self._get_azure_config_internal()
        elif provider == "OPENAI":
            config_data = self._get_openai_config_internal()
        elif provider == "VLLM":
            config_data = self._get_vllm_config_internal()
        else:
            raise ValueError(
                f"Invalid CHAT_API_PROVIDER: '{provider}'. "
                "Supported values are 'OPENAI', 'AZURE', or 'VLLM'."
            )
        
        if not config_data: # Should be caught by decorator or above, but as safeguard
            raise RuntimeError(f"Configuration could not be loaded for provider: {provider}")

        client_class = config_data["client_class"]
        self.client = client_class(**config_data["client_config"])
        self.chat_model_id = config_data["chat_model_id"]
        self.embedding_model_id = config_data["embedding_model_id"]

    def get_media_info(self, media_id: str) -> Optional[Dict[str, str]]:
        """Retrieves media item's URL and MIME type using its ID from Meta API.

        Args:
            media_id (str): The ID of the media item.

        Returns:
            Optional[Dict[str, str]]: A dictionary with "url" and "mime_type"
                                       if successful, None otherwise.
        """
        version_str = current_app.config.get('VERSION', 'v19.0')
        # Ensure 'v' is not duplicated if already present in version_str
        if version_str.startswith('v'):
            base_api_url = f"https://graph.facebook.com/{version_str}"
        else:
            base_api_url = f"https://graph.facebook.com/v{version_str}"
        
        url = f"{base_api_url}/{media_id}"
        headers = {"Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "url" in data and "mime_type" in data:
                return {"url": data["url"], "mime_type": data["mime_type"], "id": data.get("id", media_id)}
            else:
                logger.error(f"Missing 'url' or 'mime_type' in media info response for ID {media_id}: {data}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve media info for ID {media_id}: {e}")
            return None
        except ValueError as e: # Includes JSONDecodeError
            logger.error(f"Failed to decode JSON response for media info ID {media_id}: {e}")
            return None

    def download_media_content(self, media_download_url: str) -> Optional[bytes]:
        """Downloads the media content from the given URL (obtained from Meta API).

        Args:
            media_download_url (str): The URL to download the media from.

        Returns:
            Optional[bytes]: The media content as bytes if successful, None otherwise.
        """
        headers = {"Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"}
        try:
            response = requests.get(media_download_url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download media from URL {media_download_url}: {e}")
            return None

    def get_chat_completion(
        self, 
        messages: List[Dict[str, Any]], 
        temperature: float = 0.7, 
        max_tokens: int = 512
    ) -> str:
        """Gets a chat completion from the configured LLM.

        Args:
            messages (List[Dict[str, Any]]): A list of message objects, prepared
                by PromptBuilder, suitable for the OpenAI API (can be multimodal).
            temperature (float): Sampling temperature for the completion.
            max_tokens (int): Maximum number of tokens to generate.

        Returns:
            str: The assistant's response text, or a generic error message.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model_id,
                messages=messages, # type: ignore # complesso per type checker statico
                temperature=temperature,
                max_tokens=max_tokens,
            )
            assistant_text = response.choices[0].message.content if response.choices[0].message.content else ""
            return assistant_text.strip() if assistant_text else "I received that, but I'm not sure how to respond just yet."
        except Exception as e:
            logger.error(f"Error calling LLM for chat completion: {e}")
            return "I encountered an issue trying to process your request. Please try again."

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generates an embedding vector for the given text.

        Args:
            text (str): The text to embed.

        Returns:
            Optional[List[float]]: The embedding vector, or None on error.
        """
        try:
            resp = self.client.embeddings.create(
                model=self.embedding_model_id, 
                input=[text]
            )
            return resp.data[0].embedding
        except Exception as e:
            logger.error(f"Error calling LLM for embedding: {e}")
            return None
