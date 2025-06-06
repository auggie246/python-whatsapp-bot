# Python WhatsApp Bot

This project is a powerful and extensible WhatsApp bot built with Python, Flask, and the Meta Cloud API. It's designed to be a robust starting point for creating intelligent, multimodal conversational agents on WhatsApp. The bot can handle both text and image messages, and it is architected to seamlessly integrate with various Large Language Model (LLM) providers like OpenAI, Azure OpenAI, and any OpenAI-compatible API (e.g., vLLM).

## Features

- **Multimodal Conversations**: Respond to both text and image messages from users.
- **Extensible LLM Integration**: Easily switch between different LLM providers (OpenAI, Azure, vLLM) through simple configuration changes.
- **Modular Architecture**: Built with a clean, object-oriented, and scalable structure using the Flask factory pattern.
- **Secure Webhooks**: Includes signature validation for incoming webhook requests from Meta to ensure security.
- **Easy Configuration**: Manage all your settings and secrets through a straightforward `.env` file.
- **Conversation History**: Maintains a history of conversations for each user to provide context for the LLM.

## Architecture Overview

The application is structured to be modular and easy to extend. The core logic is located in the `app/` directory and follows the Flask factory pattern.

- **`app/bot/`**: This is the heart of the bot.
    - **`assistant.py`**: The `ChatAssistant` class orchestrates the entire message handling process, from receiving a message to sending a reply.
    - **`providers/llm_provider.py`**: The `LLMProvider` class is a versatile interface that handles all communication with the configured LLM and the Meta Media API. It is designed to be easily extended with new providers.
    - **`adapters/whatsapp_adapter.py`**: The `WhatsAppAdapter` is responsible for formatting and sending messages back to the user via the WhatsApp Cloud API.
    - **`prompt_builder/whatsapp_prompt_builder.py`**: The `WhatsAppPromptBuilder` constructs the detailed prompts (including system messages and conversation history) that are sent to the LLM.
    - **`webhooks.py`**: Defines the Flask blueprint for handling incoming webhook requests from WhatsApp.
- **`run.py`**: The main entry point to start the Flask application.
- **`config.py`**: Manages the application's configuration by loading environment variables.

For a more detailed breakdown of the architecture, you can refer to `CLAUDE.md`.

## Getting Started

Follow these steps to get the bot up and running.

### Prerequisites

- A [Meta Developer Account](https://developers.facebook.com/).
- A Meta Business App with WhatsApp configured.
- Python 3.12 or higher.
- `uv` for package management (recommended).
- `ngrok` to expose your local server to the internet.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/auggie246/python-whatsapp-bot.git
    cd python-whatsapp-bot
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```

### Configuration

1.  **Create a `.env` file:**
    Copy the `example.env` file to a new file named `.env`.
    ```bash
    cp example.env .env
    ```

2.  **Fill in the `.env` file:**
    You will need to provide your credentials from the Meta App Dashboard and your chosen LLM provider.

    - **WhatsApp Configuration (Required)**:
        - `ACCESS_TOKEN`: Your WhatsApp Business permanent access token.
        - `APP_ID`, `APP_SECRET`: Your Meta App credentials.
        - `RECIPIENT_WAID`: Your personal WhatsApp number for testing.
        - `PHONE_NUMBER_ID`: The Phone Number ID from your WhatsApp app in the Meta dashboard.
        - `VERIFY_TOKEN`: A secret token of your choice to secure your webhook.

    - **LLM Provider Configuration (Choose one)**:
        - **`CHAT_API_PROVIDER`**: Set this to `OPENAI`, `AZURE`, or `VLLM` to select the LLM provider.

        - **For OpenAI**:
            - `OPENAI_API_KEY`: Your OpenAI API key.
            - `OPENAI_MODEL_NAME`: The model you want to use (e.g., `gpt-4o-mini`).

        - **For Azure OpenAI**:
            - `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI resource endpoint.
            - `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key.
            - `AZURE_OPENAI_DEPLOYMENT_NAME`: The name of your chat model deployment.

        - **For vLLM (or any other OpenAI-compatible API)**:
            - `VLLM_API_BASE`: The base URL of your vLLM server (e.g., `http://localhost:8000/v1`).
            - `VLLM_MODEL_NAME`: The model identifier used by your vLLM server.
            - `VLLM_API_KEY`: An API key if your server requires one (can often be a dummy value).

## Running the Application

1.  **Start the Flask server:**
    ```bash
    python run.py
    ```
    The application will start on `http://localhost:8000`.

2.  **Expose your server with ngrok:**
    Open a new terminal window and run the following command. You will need a static ngrok domain, which is available on their free plan.
    ```bash
    ngrok http 8000 --domain your-static-domain.ngrok-free.app
    ```

3.  **Configure the Webhook in the Meta App Dashboard:**
    - Go to your app in the Meta Developer Dashboard, navigate to **WhatsApp > Configuration**.
    - Set the **Callback URL** to your ngrok URL (e.g., `https://your-static-domain.ngrok-free.app/webhook`).
    - Set the **Verify token** to the same `VERIFY_TOKEN` you set in your `.env` file.
    - Subscribe to the **messages** webhook field.

You can now send messages to your bot's WhatsApp number and receive AI-powered responses!

## License

This project is licensed under the terms of the `LICENCE.txt` file.
