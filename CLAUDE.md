# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. This document also outlines best practices for working with Claude Code to ensure efficient and successful software development tasks.

## Task Management

For complex or multi-step tasks, Claude Code will use:
*   **TodoWrite**: To create a structured task list, breaking down the work into manageable steps. This provides clarity on the plan and allows for tracking progress.
*   **TodoRead**: To review the current list of tasks and their status, ensuring alignment and that all objectives are being addressed.

## File Handling and Reading

Understanding file content is crucial before making modifications.

1.  **Targeted Information Retrieval**:
    *   When searching for specific content, patterns, or definitions within a codebase, prefer using search tools like `Grep` or `Task` (with a focused search prompt). This is more efficient than reading entire files.

2.  **Reading File Content**:
    *   **Small to Medium Files**: For files where full context is needed or that are not excessively large, the `Read` tool can be used to retrieve the entire content.
    *   **Large File Strategy**:
        1.  **Assess Size**: Before reading a potentially large file, its size should be determined (e.g., using `ls -l` via the `Bash` tool or by an initial `Read` with a small `limit` to observe if content is truncated).
        2.  **Chunked Reading**: If a file is large (e.g., over a few thousand lines), it should be read in manageable chunks (e.g., 1000-2000 lines at a time) using the `offset` and `limit` parameters of the `Read` tool. This ensures all content can be processed without issues.
    *   Always ensure that the file path provided to `Read` is absolute.

## File Editing

Precision is key for successful file edits. The following strategies lead to reliable modifications:

1.  **Pre-Edit Read**: **Always** use the `Read` tool to fetch the content of the file *immediately before* attempting any `Edit` or `MultiEdit` operation. This ensures modifications are based on the absolute latest version of the file.

2.  **Constructing `old_string` (The text to be replaced)**:
    *   **Exact Match**: The `old_string` must be an *exact* character-for-character match of the segment in the file you intend to replace. This includes all whitespace (spaces, tabs, newlines) and special characters.
    *   **No Read Artifacts**: Crucially, do *not* include any formatting artifacts from the `Read` tool's output (e.g., `cat -n` style line numbers or display-only leading tabs) in the `old_string`. It must only contain the literal characters as they exist in the raw file.
    *   **Sufficient Context & Uniqueness**: Provide enough context (surrounding lines) in `old_string` to make it uniquely identifiable at the intended edit location. The "Anchor on a Known Good Line" strategy is preferred: `old_string` is a larger, unique block of text surrounding the change or insertion point. This is highly reliable.

3.  **Constructing `new_string` (The replacement text)**:
    *   **Exact Representation**: The `new_string` must accurately represent the desired state of the code, including correct indentation, whitespace, and newlines.
    *   **No Read Artifacts**: As with `old_string`, ensure `new_string` does *not* contain any `Read` tool output artifacts.

4.  **Choosing the Right Editing Tool**:
    *   **`Edit` Tool**: Suitable for a single, well-defined replacement in a file.
    *   **`MultiEdit` Tool**: Preferred when multiple changes are needed within the same file. Edits are applied sequentially, with each subsequent edit operating on the result of the previous one. This tool is highly effective for complex modifications.

5.  **Verification**:
    *   The success confirmation from the `Edit` or `MultiEdit` tool (especially if `expected_replacements` is used and matches) is the primary indicator that the change was made.
    *   If further visual confirmation is needed, use the `Read` tool with `offset` and `limit` parameters to view only the specific section of the file that was changed, rather than re-reading the entire file.

### Reliable Code Insertion with MultiEdit

When inserting larger blocks of new code (e.g., multiple functions or methods) where a simple `old_string` might be fragile due to surrounding code, the following `MultiEdit` strategy can be more robust:

1.  **First Edit - Targeted Insertion Point**: For the primary code block you want to insert (e.g., new methods within a class), identify a short, unique, and stable line of code immediately *after* your desired insertion point. Use this stable line as the `old_string`.
    *   The `new_string` will consist of your new block of code, followed by a newline, and then the original `old_string` (the stable line you matched on).
    *   Example: If inserting methods into a class, the `old_string` might be the closing brace `}` of the class, or a comment that directly follows the class.

2.  **Second Edit (Optional) - Ancillary Code**: If there's another, smaller piece of related code to insert (e.g., a function call within an existing method, or an import statement), perform this as a separate, more straightforward edit within the `MultiEdit` call. This edit usually has a more clearly defined and less ambiguous `old_string`.

**Rationale**:
*   By anchoring the main insertion on a very stable, unique line *after* the insertion point and prepending the new code to it, you reduce the risk of `old_string` mismatches caused by subtle variations in the code *before* the insertion point.
*   Keeping ancillary edits separate allows them to succeed even if the main insertion point is complex, as they often target simpler, more reliable `old_string` patterns.
*   This approach leverages `MultiEdit`'s sequential application of changes effectively.

**Example Scenario**: Adding new methods to a class and a call to one of these new methods elsewhere.
*   **Edit 1**: Insert the new methods. `old_string` is the class's closing brace `}`. `new_string` is `
    [new methods code]
    }`.
*   **Edit 2**: Insert the call to a new method. `old_string` is `// existing line before call`. `new_string` is `// existing line before call
    this.newMethodCall();`.

This method provides a balance between precise editing and handling larger code insertions reliably when direct `old_string` matches for the entire new block are problematic.

## Handling Large Files for Incremental Refactoring

When refactoring large files incrementally rather than rewriting them completely:

1. **Initial Exploration and Planning**:
   * Begin with targeted searches using `Grep` to locate specific patterns or sections within the file.
   * Use `Bash` commands like `grep -n "pattern" file` to find line numbers for specific areas of interest.
   * Create a clear mental model of the file structure before proceeding with edits.

2. **Chunked Reading for Large Files**:
   * For files too large to read at once, use multiple `Read` operations with different `offset` and `limit` parameters.
   * Read sequential chunks to build a complete understanding of the file.
   * Use `Grep` to pinpoint key sections, then read just those sections with targeted `offset` parameters.

3. **Finding Key Implementation Sections**:
   * Use `Bash` commands with `grep -A N` (to show N lines after a match) or `grep -B N` (to show N lines before) to locate function or method implementations.
   * Example: `grep -n "function findTagBoundaries" -A 20 filename.js` to see the first 20 lines of a function.

4. **Pattern-Based Replacement Strategy**:
   * Identify common patterns that need to be replaced across the file.
   * Use the `Bash` tool with `sed` for quick previews of potential replacements.
   * Example: `sed -n "s/oldPattern/newPattern/gp" filename.js` to preview changes without making them.

5. **Sequential Selective Edits**:
   * Target specific sections or patterns one at a time rather than attempting a complete rewrite.
   * Focus on clearest/simplest cases first to establish a pattern of successful edits.
   * Use `Edit` for well-defined single changes within the file.

6. **Batch Similar Changes Together**:
   * Group similar types of changes (e.g., all references to a particular function or variable).
   * Use `Bash` with `sed` to preview the scope of batch changes: `grep -n "pattern" filename.js | wc -l`
   * For systematic changes across a file, consider using `sed` through the `Bash` tool: `sed -i "s/oldPattern/newPattern/g" filename.js`

7. **Incremental Verification**:
   * After each set of changes, verify the specific sections that were modified.
   * For critical components, read the surrounding context to ensure the changes integrate correctly.
   * Validate that each change maintains the file's structure and logic before proceeding to the next.

8. **Progress Tracking for Large Refactors**:
   * Use the `TodoWrite` tool to track which sections or patterns have been updated.
   * Create a checklist of all required changes and mark them off as they're completed.
   * Record any sections that require special attention or that couldn't be automatically refactored.

## Commit Messages

When Claude Code generates commit messages on your behalf:
*   The `Co-Authored-By: Claude <noreply@anthropic.com>` line will **not** be included.
*   The `🤖 Generated with [Claude Code](https://claude.ai/code)` line will **not** be included.

## General Interaction

Claude Code will directly apply proposed changes and modifications using the available tools, rather than describing them and asking you to implement them manually. This ensures a more efficient and direct workflow.

## Common Commands

### Setup
- Install dependencies: `uv sync` (This is preferred. `pip install -r requirements.txt` is also mentioned.)

### Running the Application
- Start the Flask application: `python run.py`
- Expose the local application to the internet (requires ngrok setup): `ngrok http 8000 --domain your-domain.ngrok-free.app` (Replace `your-domain.ngrok-free.app` with your actual ngrok static domain)

## Code Architecture

This project is a WhatsApp bot built with Python and Flask, using the Meta Cloud API.

### Project Structure Overview (`app/` directory)
The application follows the Flask Factory Pattern, with bot-specific logic organized into the `app/bot/` package.

- **`app/__init__.py`**: Initializes the Flask app using the `create_app` factory function. Registers the bot's webhook blueprint.
- **`app/config.py`**: Manages configurations and settings for the Flask application. Environment variables and secrets are loaded here.
- **`app/bot/`**: Core package for all WhatsApp bot functionalities.
    - `__init__.py`: Makes `bot` a Python package.
    - `assistant.py`: Defines `ChatAssistant`, the central orchestrator for message processing, managing conversation history, and coordinating `LLMProvider`, `WhatsAppPromptBuilder`, and `WhatsAppAdapter`.
    - `webhooks.py`: (Formerly `app/views.py`) Defines the Flask blueprint and handles incoming webhook requests from WhatsApp, delegating to `app/bot/utils.py`.
    - `utils.py`: (Consolidated from the old `app/utils/whatsapp_utils.py`) Contains bot-specific utilities for validating and initially processing incoming WhatsApp messages before they are handled by `ChatAssistant`.
    - `adapters/`: Package for platform-specific adapters.
        - `__init__.py`: Makes `adapters` a Python package.
        - `whatsapp_adapter.py`: Defines `WhatsAppAdapter`, responsible for formatting and sending outgoing messages via the WhatsApp Cloud API.
    - `decorators/`: Package for bot-specific decorators.
        - `__init__.py`: Makes `decorators` a Python package.
        - `security.py`: Contains the `@signature_required` decorator for webhook signature validation.
        - `service_decorators.py`: Contains the `@require_env_vars` decorator for environment variable checks (used by `LLMProvider`).
    - `prompt_builder/`: Package for prompt construction logic.
        - `__init__.py`: Makes `prompt_builder` a Python package.
        - `whatsapp_prompt_builder.py`: Defines `WhatsAppPromptBuilder`, responsible for constructing prompts (text and multimodal) for the LLM, including system messages and history.
    - `providers/`: Package for external service providers.
        - `__init__.py`: Makes `providers` a Python package.
        - `llm_provider.py`: Defines `LLMProvider`, which handles all interactions with the LLM (OpenAI, Azure) and the Meta Media API (for downloading images).

### Main Files (Root Directory)
- **`run.py`**: The entry point to run the Flask application.
- **`example.env`**: Template for environment variables. A `.env` file should be created based on this.
- **`pyproject.toml`**: Defines project metadata and dependencies.

### Key Functionality
The bot's operation revolves around a modular, class-based architecture:

1.  **Webhook Handling (`app/bot/webhooks.py`)**:
    *   Receives WhatsApp messages via a webhook configured in the Meta Developer portal.
    *   The `/webhook` endpoint uses `@signature_required` (from `app/bot/decorators/security.py`) for request validation.
    *   Valid requests are passed to `process_whatsapp_message` in `app/bot/utils.py`.

2.  **Initial Message Processing (`app/bot/utils.py`)**:
    *   `is_valid_whatsapp_message` validates the incoming payload structure.
    *   `process_whatsapp_message` extracts essential details (sender WAID, name, message type, content) and instantiates `ChatAssistant`.
    *   It then calls the appropriate handler on `ChatAssistant` (e.g., `handle_text_message` or `handle_image_message`).

3.  **Core Logic Orchestration (`app/bot/assistant.py` - `ChatAssistant`)**:
    *   Initializes instances of `LLMProvider`, `WhatsAppPromptBuilder`, and `WhatsAppAdapter`.
    *   Manages conversation history for each user (`self.user_histories`).
    *   For an incoming message:
        *   Retrieves the current conversation history for the user.
        *   If it's an image message, it first uses `LLMProvider`'s media functions (`get_media_info`, `download_media_content`) to get image bytes and create a data URL.
        *   Uses `WhatsAppPromptBuilder` (`build_text_prompt` or `build_image_prompt`) to construct a detailed prompt payload for the LLM, including the system message, formatted history, and current user message content (text or multimodal image data).
        *   Calls the appropriate method on `LLMProvider` (`get_chat_completion`) to get a response from the configured multimodal LLM.
        *   Updates the conversation history with the user's message (or its representation) and the LLM's response.
        *   Uses `WhatsAppAdapter` (`send_text_message`) to send the LLM's (textual) response back to the user.

4.  **LLM and Media Interaction (`app/bot/providers/llm_provider.py` - `LLMProvider`)**:
    *   Initializes the underlying LLM client (OpenAI, Azure) based on `CHAT_API_PROVIDER` and other environment variables.
    *   Provides methods for:
        *   Fetching media information (`get_media_info`) and content (`download_media_content`) from the Meta Media API.
        *   Getting chat completions (`get_chat_completion`) from the LLM; this method handles both text-only and multimodal message lists.
    *   Uses `@require_env_vars` (from `app/bot/decorators/service_decorators.py`) for validating necessary API configurations during initialization.

5.  **Prompt Construction (`app/bot/prompt_builder/whatsapp_prompt_builder.py` - `WhatsAppPromptBuilder`)**:
    *   Generates the structured `messages` list (prompt payload) required by the LLM.
    *   Responsible for defining default system prompts (customizable per text/image context) and incorporating them.
    *   Formats and includes conversation history.
    *   Formats the current user message, including creating the correct structure for multimodal image inputs (text part + image_url part with base64 data).

6.  **Message Sending (`app/bot/adapters/whatsapp_adapter.py` - `WhatsAppAdapter`)**:
    *   Handles formatting of outgoing text messages for WhatsApp (e.g., markdown bold conversion, custom bracket removal via `_format_outgoing_text`).
    *   Manages the HTTP API calls to the WhatsApp Cloud API to send messages, including URL construction, headers, and error handling.

7.  **Configuration (`app/config.py`)**:
    *   Loads and provides all necessary configurations (API keys, tokens, model names, API version, etc.) from environment variables using `python-dotenv`. It's where `load_dotenv()` is called.

### Development Workflow
1.  Set up environment variables in a `.env` file (based on `example.env`).
2.  Install dependencies using `uv sync`.
3.  Run the Flask application locally using `python run.py`.
4.  Use ngrok to expose the local server to the internet so Meta's servers can send webhook events. The ngrok URL is configured in the Meta App Dashboard.
5.  Test by sending messages to the configured WhatsApp number.
