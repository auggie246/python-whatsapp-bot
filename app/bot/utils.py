"""Bot-specific utility functions for WhatsApp message processing."""
import logging

from .assistant import ChatAssistant

logger = logging.getLogger(__name__)

def process_whatsapp_message(body):
    """Processes an incoming WhatsApp message payload and delegates to ChatAssistant."""
    try:
        value = body["entry"][0]["changes"][0]["value"]
        if not value.get("contacts") or not value.get("messages"):
            logger.warning("Webhook received without contacts or messages key in value.")
            return # Not a user message we can process

        wa_id = value["contacts"][0]["wa_id"]
        name = value["contacts"][0]["profile"]["name"]
        message_object = value["messages"][0]
        message_type = message_object["type"]
    except (IndexError, KeyError) as e:
        logger.error(f"Error parsing essential fields from webhook body: {e}. Body: {body}")
        return

    chat_assistant = ChatAssistant() 

    match message_type:
        case "text":
            message_body = message_object.get("text", {}).get("body")
            if not message_body:
                logger.warning(f"Text message from {name} ({wa_id}) has no body.")
                return
            logger.info(f"Handing off text message to ChatAssistant for {name} ({wa_id}): '{message_body}'")
            chat_assistant.handle_text_message(wa_id, name, message_body)
        case "image":
            image_object = message_object.get("image", {})
            image_id = image_object.get("id")
            if not image_id:
                logger.warning(f"Image message from {name} ({wa_id}) has no id.")
                return
            caption = image_object.get("caption")
            log_message = f"Handing off image message to ChatAssistant for {name} ({wa_id}), image_id: {image_id}"
            if caption:
                log_message += f" with caption: '{caption}'"
            logger.info(log_message)
            chat_assistant.handle_image_message(wa_id, name, image_id, caption)
        case _:
            logger.warning(
                f"Received unsupported message type '{message_type}' from {name} ({wa_id})."
            )
            # Potentially call a generic handler on chat_assistant if one is added in the future
            # e.g., chat_assistant.handle_unsupported_message(wa_id, name, message_type)
            pass

def is_valid_whatsapp_message(body):
    """Check if the incoming webhook event has a valid WhatsApp message structure."""
    if not isinstance(body, dict):
        return False
    if not body.get("object") == "whatsapp_business_account":
        return False # Not from a WhatsApp business account
    
    entries = body.get("entry")
    if not isinstance(entries, list) or not entries:
        return False
    
    changes = entries[0].get("changes")
    if not isinstance(changes, list) or not changes:
        return False

    value = changes[0].get("value")
    if not isinstance(value, dict):
        return False

    # Check for actual messages, not status updates etc.
    if "messages" not in value or not isinstance(value["messages"], list) or not value["messages"]:
        return False 
    if "contacts" not in value or not isinstance(value["contacts"], list) or not value["contacts"]:
        return False
        
    # Further check if the first message has a type
    first_message = value["messages"][0]
    if not isinstance(first_message, dict) or "type" not in first_message:
        return False
        
    return True
