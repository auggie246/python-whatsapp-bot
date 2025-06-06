"""Prompt builder for WhatsApp interactions.

This module defines the WhatsAppPromptBuilder class, responsible for
constructing the message payloads (prompts) to be sent to the LLM,
including system messages, conversation history, and current user input
(text or multimodal for images).
"""
from typing import List, Dict, Any, Optional

class WhatsAppPromptBuilder:
    """Constructs prompts for LLM interactions based on WhatsApp messages."""

    def __init__(self):
        """Initializes the prompt builder."""
        self.default_text_system_prompt_template = (
            "You are a helpful, concise assistant chatting on WhatsApp with {name}. "
            "Keep answers short and conversational."
        )
        self.default_image_system_prompt_template = (
            "You are a helpful, concise assistant chatting on WhatsApp with {name}. "
            "The user has sent an image. Describe it briefly if you can, "
            "and respond to their caption or the image context. "
            "If you cannot process or describe the image, acknowledge it gracefully."
        )

    def build_text_prompt(
        self, 
        name: str, 
        text_body: str, 
        history: List[Dict[str, Any]], 
        system_message_override: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Constructs a prompt for a text-only LLM interaction.

        Args:
            name (str): The name of the user.
            text_body (str): The user's current text message.
            history (List[Dict[str, Any]]): A list of previous messages in the conversation.
            system_message_override (Optional[str], optional): An overriding system message.
                                                            Defaults to None.

        Returns:
            List[Dict[str, Any]]: The list of messages formatted for the LLM.
        """
        messages = []
        system_prompt = system_message_override if system_message_override else \
                        self.default_text_system_prompt_template.format(name=name)
        
        messages.append({"role": "system", "content": system_prompt})
        messages.extend(history) # Add a copy of history
        messages.append({"role": "user", "content": text_body})
        return messages

    def build_image_prompt(
        self, 
        name: str, 
        image_data_url: str, 
        caption: Optional[str], 
        history: List[Dict[str, Any]],
        system_message_override: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Constructs a prompt for a multimodal (image + text) LLM interaction.

        Args:
            name (str): The name of the user.
            image_data_url (str): The data URL of the image (e.g., base64 encoded).
            caption (Optional[str]): The caption for the image, if any.
            history (List[Dict[str, Any]]): A list of previous messages in the conversation.
            system_message_override (Optional[str], optional): An overriding system message.
                                                            Defaults to None.

        Returns:
            List[Dict[str, Any]]: The list of messages formatted for the LLM.
        """
        messages = []
        system_prompt = system_message_override if system_message_override else \
                        self.default_image_system_prompt_template.format(name=name)

        messages.append({"role": "system", "content": system_prompt})
        messages.extend(history) # Add a copy of history

        user_message_content_parts = []
        text_prompt_content = f"Image received from {name}."
        if caption:
            text_prompt_content += f" The caption is: '{caption}'."
        else:
            text_prompt_content += " There was no caption."
        
        user_message_content_parts.append({"type": "text", "text": text_prompt_content})
        user_message_content_parts.append({"type": "image_url", "image_url": {"url": image_data_url}})
        
        messages.append({"role": "user", "content": user_message_content_parts})
        return messages
