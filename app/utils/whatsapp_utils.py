import json
import logging

import requests
from flask import current_app, jsonify

from app.bot.assistant import ChatAssistant
# Removed: from app.services.openai_service import generate_response, generate_image_response






## Echo bot for testing
# def generate_response(response):
#     # Return text in uppercase
#     return response.upper()






def process_whatsapp_message(body):
    value = body["entry"][0]["changes"][0]["value"]
    wa_id = value["contacts"][0]["wa_id"]
    name = value["contacts"][0]["profile"]["name"]
    message_object = value["messages"][0]
    message_type = message_object["type"]

    chat_assistant = ChatAssistant() # Instantiate the assistant
    # user_histories = {} # Or manage this at a higher scope / pass in

    match message_type:
        case "text":
            message_body = message_object["text"]["body"]
            logging.info(f"Handing off text message to ChatAssistant for {name} ({wa_id}): '{message_body}'")
            chat_assistant.handle_text_message(wa_id, name, message_body)
        case "image":
            image_id = message_object["image"]["id"]
            caption = message_object["image"].get("caption")
            log_message = f"Handing off image message to ChatAssistant for {name} ({wa_id}), image_id: {image_id}"
            if caption:
                log_message += f" with caption: '{caption}'"
            logging.info(log_message)
            chat_assistant.handle_image_message(wa_id, name, image_id, caption)
        case _:
            logging.warning(
                f"Received unsupported message type '{message_type}' from {name} ({wa_id}). Forwarding to assistant for default handling."
            )
            # For now, ChatAssistant doesn't have a generic handler, so we might log or do nothing.
            # Or, we could define a ChatAssistant.handle_unsupported_message(wa_id, name, message_type)
            # For this refactoring step, we'll assume ChatAssistant might eventually send a generic reply.
            # If not, this unsupported message might need to be handled here or a generic method added to assistant.
            # For now, no explicit response will be sent for unsupported types from this function.
            pass


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
