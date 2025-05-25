# Test script for app.services.combined_openai_service.py
#
# This script demonstrates how to use the combined OpenAI service for generating
# text responses and embeddings.
#
# How to run:
# 1. Ensure you are in the root directory of the project.
# 2. Set the required environment variables (see below).
# 3. Run the script using: python start/test_combined_service.py
#
# Environment Variables:
# ----------------------
# You MUST set these environment variables in your shell or a .env file
# in the root of the project before running this script.
#
# 1. LLM_PROVIDER:
#    - Set to "openai" for standard OpenAI API.
#    - Set to "azure" for Azure OpenAI Service.
#
# 2. If LLM_PROVIDER="openai":
#    - OPENAI_API_KEY: Your OpenAI API key.
#    - OPENAI_MODEL_NAME: The model to use (e.g., "gpt-3.5-turbo").
#    - (Optional) OPENAI_EMBEDDING_MODEL_NAME: (e.g., "text-embedding-3-small")
#
# 3. If LLM_PROVIDER="azure":
#    - AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint (e.g., "https://<your-resource-name>.openai.azure.com/").
#    - AZURE_OPENAI_API_KEY: Your Azure OpenAI API key.
#    - AZURE_OPENAI_DEPLOYMENT_NAME: Your Azure deployment name for chat models.
#    - (Optional) AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME: Your Azure deployment name for embedding models.
#      If not set, it will try to use the chat deployment name for embeddings.
#    - (Optional) AZURE_OPENAI_API_VERSION: (e.g., "2023-07-01-preview")
#
# Note: Actual API calls will only succeed if valid credentials for the selected
# provider are available and correctly configured. This script does not mock API calls.

import os
from flask import Flask, current_app
from dotenv import load_dotenv

# Assuming the script is run from the project root or `start/` directory,
# adjust path if necessary to find app.config and app.services
import sys

# Ensure the app directory is in the Python path
# This is a common way to handle running scripts in subdirectories
# that need to import modules from sibling directories (like 'app')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import load_configurations
from app.services.combined_openai_service import (
    initialize_openai_client,
    generate_response,
    embed
)

def main():
    # Load .env file from the project root
    # Correct path assuming this script is in 'start/' and .env is in project root
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Attempting to load .env file from: {dotenv_path}")
    if os.path.exists(dotenv_path):
        print(".env file found and loaded.")
    else:
        print(".env file NOT found. Please ensure it exists in the project root or that environment variables are set externally.")


    # Create a minimal Flask application instance
    app = Flask(__name__)

    # Load configurations into the app
    # load_configurations function expects app.config to exist.
    # It also loads .env by itself if not already loaded, but explicit loading above is clearer.
    load_configurations(app)

    # Push an application context
    with app.app_context():
        try:
            # Initialize the OpenAI client
            # This needs to be called within an app context because it uses current_app
            initialize_openai_client()
            print("OpenAI client initialized successfully.")

            # Retrieve the configured provider
            provider = current_app.config.get("OPENAI_SERVICE_PROVIDER")
            print(f"--- Testing with provider: {provider} ---")

            # --- Demonstrate generate_response ---
            print("\n--- Testing generate_response ---")
            try:
                response = generate_response(
                    message_body="Hello, this is a test prompt for the LLM.",
                    wa_id="test_user_123",
                    name="TestBot"
                )
                print(f"Raw response object: {type(response)}")
                print(f"Generated response: {response}")
            except RuntimeError as e:
                print(f"Error during generate_response: {e}")
            except Exception as e:
                print(f"An unexpected error occurred during generate_response: {e}")

            # --- Demonstrate embed ---
            print("\n--- Testing embed ---")
            test_sentence = "This is a test sentence to generate an embedding."
            try:
                embedding = embed(text=test_sentence)
                print(f"Raw embedding object: {type(embedding)}")
                if embedding:
                    print(f"Embedding generated for: '{test_sentence}'")
                    print(f"Embedding type: {type(embedding)}")
                    print(f"Embedding length: {len(embedding)}")
                    print(f"First 5 dimensions: {embedding[:5]}")
                else:
                    print("Embedding generation returned None or empty.")
            except RuntimeError as e:
                print(f"Error during embed: {e}")
            except Exception as e:
                print(f"An unexpected error occurred during embed: {e}")

        except RuntimeError as e:
            print(f"Error during client initialization or context setup: {e}")
            print("Please ensure that your .env file is correctly set up in the project root,")
            print("or that all required environment variables are exported in your session.")
            print("Refer to the comments at the top of this script for required variables.")
        except Exception as e:
            print(f"An critical unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
