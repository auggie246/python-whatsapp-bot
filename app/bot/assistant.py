"""Module for the ChatAssistant class.

This module defines the ChatAssistant, which orchestrates the bot's responses
to user messages by interacting with an LLM provider, a prompt builder,
and a WhatsApp adapter.
"""
import logging
import base64 # For image processing
from typing import Dict, Any, Optional, List, Union
from collections import defaultdict

from .providers.llm_provider import LLMProvider
from .adapters.whatsapp_adapter import WhatsAppAdapter
from .prompt_builder.whatsapp_prompt_builder import WhatsAppPromptBuilder

logger = logging.getLogger(__name__)

class ChatAssistant:
    """Orchestrates message and image interactions for the WhatsApp bot."""

    def __init__(self):
        """Initializes the assistant with its core components and history management."""
        self.llm_provider = LLMProvider()
        self.whatsapp_adapter = WhatsAppAdapter()
        self.prompt_builder = WhatsAppPromptBuilder()
        self.user_histories: Dict[str, List[Dict[str, Union[str, List[Dict[str, Any]]]]]] = defaultdict(list)
        self.max_history_turns = 10  # Max user/assistant pairs to keep (system prompt is separate)
        logger.info(
            "ChatAssistant initialized with LLMProvider, WhatsAppAdapter, and WhatsAppPromptBuilder."
        )

    def _append_to_history(
        self, wa_id: str, role: str, content: Union[str, List[Dict[str, Any]]]
    ) -> None:
        """Appends a message to the user's conversation history and truncates if necessary."""
        self.user_histories[wa_id].append({"role": role, "content": content})
        current_history = self.user_histories[wa_id]
        # Truncate, preserving user/assistant turn structure if possible
        if len(current_history) > self.max_history_turns * 2:
            # Keep the most recent N turns
            self.user_histories[wa_id] = current_history[-(self.max_history_turns * 2):]

    def handle_text_message(self, wa_id: str, name: str, text_body: str) -> None:
        """Processes a text message, gets an LLM response, and sends it.

        Args:
            wa_id (str): The WhatsApp ID of the user.
            name (str): The name of the user.
            text_body (str): The text content of the message.
        """
        logger.info(f"ChatAssistant handling text message from {name} ({wa_id}): '{text_body}'")
        
        history_for_prompt = list(self.user_histories[wa_id]) # Use a copy for prompt building
        messages_payload = self.prompt_builder.build_text_prompt(
            name=name, text_body=text_body, history=history_for_prompt
        )
        
        # Append actual user message to stored history *after* it's used for current prompt
        self._append_to_history(wa_id, "user", text_body)

        llm_reply_text = self.llm_provider.get_chat_completion(messages_payload)

        if llm_reply_text:
            self._append_to_history(wa_id, "assistant", llm_reply_text)
            if self.whatsapp_adapter:
                self.whatsapp_adapter.send_text_message(wa_id, llm_reply_text)
            else:
                logger.error("WhatsAppAdapter not available, cannot send reply.")
        else:
            logger.error(f"LLMProvider returned no reply for text message from {wa_id}")
            if self.whatsapp_adapter:
                self.whatsapp_adapter.send_text_message(wa_id, "I'm having a little trouble thinking right now. Please try again later.")

    def handle_image_message(
        self, wa_id: str, name: str, image_id: str, caption: Optional[str]
    ) -> None:
        """Processes an image message, gets an LLM response, and sends it.

        Args:
            wa_id (str): The WhatsApp ID of the user.
            name (str): The name of the user.
            image_id (str): The ID of the received image.
            caption (Optional[str]): The caption accompanying the image, if any.
        """
        logger.info(f"ChatAssistant handling image message from {name} ({wa_id}), image_id: {image_id}, caption: '{caption}'")

        media_info = self.llm_provider.get_media_info(image_id)
        if not media_info:
            logger.error(f"Failed to get media info for image_id: {image_id} from {name} ({wa_id})")
            if self.whatsapp_adapter:
                self.whatsapp_adapter.send_text_message(wa_id, "I'm sorry, I couldn't retrieve information about the image you sent.")
            return

        download_url = media_info.get("url")
        mime_type = media_info.get("mime_type")
        if not download_url or not mime_type:
            logger.error(f"Media info for {image_id} incomplete for {name} ({wa_id}). URL or MIME type missing.")
            if self.whatsapp_adapter:
                self.whatsapp_adapter.send_text_message(wa_id, "I'm sorry, there was an issue getting the details for your image.")
            return

        image_bytes = self.llm_provider.download_media_content(download_url)
        if not image_bytes:
            logger.error(f"Failed to download image content for image_id: {image_id} from {name} ({wa_id})")
            if self.whatsapp_adapter:
                self.whatsapp_adapter.send_text_message(wa_id, "I'm sorry, I couldn't download the image you sent.")
            return

        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_image}"
        
        history_for_prompt = list(self.user_histories[wa_id]) # Use a copy
        messages_payload = self.prompt_builder.build_image_prompt(
            name=name, 
            image_data_url=data_url, 
            caption=caption, 
            history=history_for_prompt
        )
        
        # For history, store a simplified representation or just the text part if a data_url is too large/complex
        # Here we construct the user message content part that includes text and image_url for LLM.
        user_multimodal_content_parts = []
        text_part_for_history = f"User sent an image (ID: {image_id})."
        if caption:
            text_part_for_history += f" Caption: '{caption}'"
        user_multimodal_content_parts.append({"type": "text", "text": text_part_for_history})
        # For the actual LLM call, the prompt_builder already includes the image_url.
        # For storing in _CONV_HISTORY, we might simplify or store what was actually sent.
        # The current messages_payload already has the full structure.
        # The _append_to_history expects content that matches what an LLM would receive for user.
        # So, the messages_payload[-1]["content"] is what we store for the user turn if it's complex.
        self._append_to_history(wa_id, "user", messages_payload[-1]["content"]) 

        llm_reply_text = self.llm_provider.get_chat_completion(messages_payload)

        if llm_reply_text:
            self._append_to_history(wa_id, "assistant", llm_reply_text)
            if self.whatsapp_adapter:
                self.whatsapp_adapter.send_text_message(wa_id, llm_reply_text)
            else:
                logger.error("WhatsAppAdapter not initialized, cannot send reply for image.")
        else:
            logger.error(f"LLMProvider returned no reply for image message from {wa_id}")
            if self.whatsapp_adapter:
                self.whatsapp_adapter.send_text_message(wa_id, "I'm having a little trouble thinking about that image. Please try again later.")
