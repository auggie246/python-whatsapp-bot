import json
import logging
import re

import requests
from flask import current_app, jsonify

from app.bot.assistant import ChatAssistant
# Removed: from app.services.openai_service import generate_response, generate_image_response


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


## Echo bot for testing
# def generate_response(response):
#     # Return text in uppercase
#     return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


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
