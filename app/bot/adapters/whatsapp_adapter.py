"""WhatsApp Adapter for sending messages via the Meta Cloud API."""
import json
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

class WhatsAppAdapter:
    """Handles sending messages through the WhatsApp Cloud API."""

    def __init__(self):
        """Initializes the WhatsAppAdapter with API configuration."""
        self.api_version = current_app.config.get("VERSION", "v19.0")
        self.phone_number_id = current_app.config.get("PHONE_NUMBER_ID")
        self.access_token = current_app.config.get("ACCESS_TOKEN")

        if not self.phone_number_id:
            logger.critical("WHATSAPP_ADAPTER: PHONE_NUMBER_ID not configured.")
            # Consider raising an error if critical for operation
        if not self.access_token:
            logger.critical("WHATSAPP_ADAPTER: ACCESS_TOKEN not configured.")
            # Consider raising an error
        
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        logger.info(f"WhatsAppAdapter initialized for API v{self.api_version}, PhoneID: {self.phone_number_id}")

    def _log_http_response(self, response: requests.Response) -> None:
        """Logs details of an HTTP response."""
        logger.info(f"WhatsApp API Response Status: {response.status_code}")
        logger.debug(f"WhatsApp API Response Content-type: {response.headers.get('content-type')}")
        logger.debug(f"WhatsApp API Response Body: {response.text}")

    def _get_text_message_payload(self, recipient_wa_id_with_plus: str, text: str) -> str:
        """Formats the JSON payload for a text message.

        Args:
            recipient_wa_id_with_plus (str): The recipient's WhatsApp ID, including leading '+'.
            text (str): The message text to send.

        Returns:
            str: A JSON string representing the message payload.
        """
        return json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_wa_id_with_plus,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        })

    def send_text_message(self, recipient_wa_id: str, text: str) -> bool:
        """Sends a text message to a WhatsApp user.

        Args:
            recipient_wa_id (str): The recipient's WhatsApp ID (e.g., "65...").
                                     The '+' will be prepended automatically.
            text (str): The message text to send.

        Returns:
            bool: True if the message was sent successfully (API accepted), False otherwise.
        """
        if not self.phone_number_id or not self.access_token:
            logger.error(
                "WhatsAppAdapter cannot send message: PHONE_NUMBER_ID or ACCESS_TOKEN missing."
            )
            return False

        formatted_recipient_id = f"+{recipient_wa_id}"
        payload = self._get_text_message_payload(formatted_recipient_id, text)
        headers = {
            "Content-type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

        logger.info(f"Sending message to {formatted_recipient_id}: {text[:50]}...") # Log snippet
        try:
            response = requests.post(self.base_url, data=payload, headers=headers, timeout=10)
            self._log_http_response(response) # Log all responses
            response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
            logger.info(f"Message sent successfully to {formatted_recipient_id}")
            return True
        except requests.Timeout:
            logger.error(f"Timeout occurred while sending message to {formatted_recipient_id}")
            return False
        except requests.RequestException as e:
            logger.error(f"Request failed sending message to {formatted_recipient_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                # Log details from the error response if available
                self._log_http_response(e.response) 
            return False
