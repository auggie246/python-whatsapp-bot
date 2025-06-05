"""Module for the ChatAssistant class.

This module defines the ChatAssistant, which orchestrates the bot's responses
to user messages by interacting with an LLM provider, a prompt builder,
and a WhatsApp adapter.
"""
import logging
from typing import Dict, Any, Optional, List

from .providers.llm_provider import LLMProvider
from .adapters.whatsapp_adapter import WhatsAppAdapter
# Placeholder for future imports when other classes are created:
# from .prompt_builder.whatsapp_prompt_builder import WhatsAppPromptBuilder

logger = logging.getLogger(__name__)

class ChatAssistant:
    """Orchestrates message and image interactions for the WhatsApp bot."""

    def __init__(self):
        """Initializes the assistant with its core components.
        
        The PromptBuilder dependency will be initialized in a future step.
        """
        self.llm_provider = LLMProvider()
        self.whatsapp_adapter = WhatsAppAdapter()
        self.prompt_builder = None # Example: WhatsAppPromptBuilder()
        logger.info("ChatAssistant initialized with LLMProvider and WhatsAppAdapter. PromptBuilder is stubbed.")

    def handle_text_message(
        self, 
        wa_id: str, 
        name: str, 
        text_body: str, 
        # user_histories: Dict[str, List[Dict[str, Any]]] # Will be used later
    ) -> None:
        """Processes a text message and sends a response via WhatsAppAdapter.

        Args:
            wa_id (str): The WhatsApp ID of the user.
            name (str): The name of the user.
            text_body (str): The text content of the message.
        """
        logger.info(f"ChatAssistant handling text message from {name} ({wa_id}): '{text_body}'")
        # TODO: 
        # 1. Manage/update user_histories
        # 2. Build prompt using self.prompt_builder.build_text_prompt(text_body, history)
        # 3. Get LLM response using self.llm_provider.get_chat_completion(prompt_messages)
        # 4. llm_reply_text = ...
        
        # For now, send a placeholder reply using the adapter
        placeholder_reply = f"Received your text: '{text_body}'. (LLM logic pending)"
        if self.whatsapp_adapter:
            self.whatsapp_adapter.send_text_message(wa_id, placeholder_reply)
        else:
            logger.error("WhatsAppAdapter not initialized, cannot send reply.")

    def handle_image_message(
        self, 
        wa_id: str, 
        name: str, 
        image_id: str, 
        caption: Optional[str],
        # user_histories: Dict[str, List[Dict[str, Any]]] # Will be used later
    ) -> None:
        """Processes an image message and sends a response via WhatsAppAdapter.

        Args:
            wa_id (str): The WhatsApp ID of the user.
            name (str): The name of the user.
            image_id (str): The ID of the received image.
            caption (Optional[str]): The caption accompanying the image, if any.
        """
        logger.info(f"ChatAssistant handling image message from {name} ({wa_id}), image_id: {image_id}, caption: '{caption}'")
        # TODO:
        # 1. Manage/update user_histories
        # 2. image_data_url = self.llm_provider.get_image_data_url(image_id) (or similar)
        # 3. Build image prompt using self.prompt_builder.build_image_prompt(image_data_url, caption, history)
        # 4. Get LLM response using self.llm_provider.get_chat_completion(prompt_messages_with_image_data)
        # 5. llm_reply_text = ...

        # For now, send a placeholder reply using the adapter
        placeholder_reply = f"Received your image (ID: {image_id})"
        if caption:
            placeholder_reply += f" with caption: '{caption}'"
        placeholder_reply += ". (LLM logic for images pending)"
        
        if self.whatsapp_adapter:
            self.whatsapp_adapter.send_text_message(wa_id, placeholder_reply)
        else:
            logger.error("WhatsAppAdapter not initialized, cannot send reply for image.")
