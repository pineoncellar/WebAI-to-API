## Disclaimer

> **This project is intended for research and educational purposes only.**  
> Please refrain from any commercial use and act responsibly when deploying or modifying this tool.

### 🛠️ 技术声明与运行环境
- **逻辑增强**：代码库的部分模块采用了自动化指令集进行结构优化。鉴于逻辑生成的演进性，使用者应在使用前根据实际需求对核心业务流进行充分验证。
- **兼容参考**：本分支已针对 **Windows Server 2022** 与 **Microsoft Edge** 的组合进行了调优及稳定性验证。
- **行为规范**：使用者需独立承担其请求行为的合规性，并严格遵守相关第三方服务的使用细则与当地法律法规。

---

# WebAI-to-API

<p align="center">
  <img src="./assets/Server-Run-WebAI.png" alt="WebAI-to-API Server" height="160" />
  <img src="./assets/Server-Run-G4F.png" alt="gpt4free Server" height="160" />
</p>

**WebAI-to-API** is a modular web server built with FastAPI that allows you to expose your preferred browser-based LLM (such as Gemini) as a local API endpoint.

---

This project supports **two operational modes**:

1. **Primary Web Server**

   > WebAI-to-API

   Connects to the Gemini web interface using your browser cookies and exposes it as an API endpoint. This method is lightweight, fast, and efficient for personal use.

2. **Fallback Web Server (gpt4free)**

   > [gpt4free](https://github.com/xtekky/gpt4free)

   A secondary server powered by the `gpt4free` library, offering broader access to multiple LLMs beyond Gemini, including:

   - ChatGPT
   - Claude
   - DeepSeek
   - Copilot
   - HuggingFace Inference
   - Grok
   - ...and many more.

This design provides both **speed and redundancy**, ensuring flexibility depending on your use case and available resources.

---

## Features

- 🌐 **Available Endpoints**:

  - **WebAI Server**:

    - `/v1/chat/completions`
    - `/v1/models`
    - `/gemini`
    - `/gemini-chat`
    - `/gemini-image`
    - `/translate`
    - `/v1beta/models/{model}` (Google Generative AI v1beta API)

  - **gpt4free Server**:
    - `/v1`
    - `/v1/chat/completions`

- 🔄 **Server Switching**: Easily switch between servers in terminal.

- 🖼️ **Multimodal Support**: Support for OpenAI-compatible Base64 image messages in `/v1/chat/completions`.

- 🎨 **Image Generation**: Support for generating images via Gemini models. Images are automatically downloaded, saved locally, and returned as Base64.

- 🛠️ **Modular Architecture**: Organized into clearly defined modules for API routes, services, configurations, and utilities, making development and maintenance straightforward.

<p align="center">
  <img src="./assets/Endpoints-Docs.png" alt="Endpoints" height="280" />
</p>

---

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Amm1rr/WebAI-to-API.git
   cd WebAI-to-API
   ```

2. **Install dependencies using Poetry:**

   ```bash
   poetry install
   ```

3. **Create and update the configuration file:**

   ```bash
   cp config.conf.example config.conf
   ```

   Then, edit `config.conf` to adjust service settings and other options.

4. **Run the server:**

   ```bash
   poetry run python src/run.py
   ```

---

## Usage

Send a POST request to `/v1/chat/completions` (or any other available endpoint) with the required payload.

### Example Request

```json
{
  "model": "gemini-3.0-pro",
  "messages": [{ "role": "user", "content": "Hello!" }]
}
```

### Example Response

```json
{
  "id": "chatcmpl-12345",
  "object": "chat.completion",
  "created": 1693417200,
  "model": "gemini-3.0-pro",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Hi there!"
      },
      "finish_reason": "stop",
      "index": 0
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

---

## Authentication

To secure your API (especially when exposing to the public), you can configure an API Key in `config.conf`.

1. Open `config.conf`.
2. Find or add the `[Auth]` section.
3. Set your desired API key:
   ```ini
   [Auth]
   api_key = your-secret-key-here
   ```
4. Restart the server.

Once enabled, all requests must include the `Authorization` header:
```http
Authorization: Bearer your-secret-key-here
```

---

## Documentation

### WebAI-to-API Endpoints

> `POST /gemini`

Initiates a new conversation with the LLM. Each request creates a **fresh session**, making it suitable for stateless interactions.

> `POST /gemini-chat`

Continues a persistent conversation with the LLM without starting a new session. Ideal for use cases that require context retention between messages.

> `POST /translate`

Designed for quick integration with the [Translate It!](https://github.com/iSegaro/Translate-It) browser extension.
Functionally identical to `/gemini-chat`, meaning it **maintains session context** across requests.

> `POST /v1/chat/completions`

A **minimalistic implementation** of the OpenAI-compatible endpoint.
Built for simplicity and ease of integration with clients that expect the OpenAI API format.

> `POST /v1beta/models/{model}`

**Google Generative AI v1beta API** compatible endpoint.
Provides access to the latest Google Generative AI models with standard Google API format including safety ratings and structured responses.

---

### gpt4free Endpoints

These endpoints follow the **OpenAI-compatible structure** and are powered by the `gpt4free` library.  
For detailed usage and advanced customization, refer to the official documentation:

- 📄 [Provider Documentation](https://github.com/gpt4free/g4f.dev/blob/main/docs/selecting_a_provider.md)
- 📄 [Model Documentation](https://github.com/gpt4free/g4f.dev/blob/main/docs/providers-and-models.md)

#### Available Endpoints (gpt4free API Layer)

```
GET  /                              # Health check
GET  /v1                            # Version info
GET  /v1/models                     # List all available models
GET  /api/{provider}/models         # List models from a specific provider
GET  /v1/models/{model_name}        # Get details of a specific model

POST /v1/chat/completions           # Chat with default configuration
POST /api/{provider}/chat/completions
POST /api/{provider}/{conversation_id}/chat/completions

POST /v1/responses                  # General response endpoint
POST /api/{provider}/responses

POST /api/{provider}/images/generations
POST /v1/images/generations
POST /v1/images/generate            # Generate images using selected provider

POST /v1/media/generate             # Media generation (audio/video/etc.)

GET  /v1/providers                  # List all providers
GET  /v1/providers/{provider}       # Get specific provider info

POST /api/{path_provider}/audio/transcriptions
POST /v1/audio/transcriptions       # Audio-to-text

POST /api/markitdown                # Markdown rendering

POST /api/{path_provider}/audio/speech
POST /v1/audio/speech               # Text-to-speech

POST /v1/upload_cookies             # Upload session cookies (browser-based auth)

GET  /v1/files/{bucket_id}          # Get uploaded file from bucket
POST /v1/files/{bucket_id}          # Upload file to bucket

GET  /v1/synthesize/{provider}      # Audio synthesis

POST /json/{filename}               # Submit structured JSON data

GET  /media/{filename}              # Retrieve media
GET  /images/{filename}             # Retrieve images
```

---

## Roadmap

- ✅ Maintenance

---

<details>
  <summary>
    <h2>Configuration ⚙️</h2>
  </summary>

### Key Configuration Options

| Section     | Option     | Description                                | Example Value           |
| ----------- | ---------- | ------------------------------------------ | ----------------------- |
| [AI]        | default_ai | Default service for `/v1/chat/completions` | `gemini`                |
| [Browser]   | name       | Browser for cookie-based authentication    | `edge`                  |
| [EnabledAI] | gemini     | Enable/disable Gemini service              | `true`                  |
| [Proxy]     | http_proxy | Proxy for Gemini connections (optional)    | `http://127.0.0.1:2334` |

The complete configuration template is available in [`WebAI-to-API/config.conf.example`](WebAI-to-API/config.conf.example).  
If the cookies are left empty, the application will automatically retrieve them using the default browser specified.

---

### Sample `config.conf`

```ini
[AI]
# Default AI service.
default_ai = gemini

# Default model for Gemini.
default_model_gemini = gemini-3.0-pro

# Gemini cookies (leave empty to use browser_cookies3 for automatic authentication).
gemini_cookie_1psid =
gemini_cookie_1psidts =

[EnabledAI]
# Enable or disable AI services.
gemini = true

[Browser]
# Default browser options: firefox, brave, chrome, edge, safari.
name = edge

# --- Proxy Configuration ---
# Optional proxy for connecting to Gemini servers.
# Useful for fixing 403 errors or restricted connections.
[Proxy]
http_proxy =
```

</details>

---

## Project Structure

The project now follows a modular layout that separates configuration, business logic, API endpoints, and utilities:

```plaintext
src/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app creation, configuration, and lifespan management.
│   ├── config.py              # Global configuration loader/updater.
│   ├── logger.py              # Centralized logging configuration.
│   ├── endpoints/             # API endpoint routers.
│   │   ├── __init__.py
│   │   ├── gemini.py          # Endpoints for Gemini (e.g., /gemini, /gemini-chat).
│   │   ├── chat.py            # Endpoints for translation and OpenAI-compatible requests.
│   │   └── google_generative.py  # Google Generative AI v1beta API endpoints.
│   ├── services/              # Business logic and service wrappers.
│   │   ├── __init__.py
│   │   ├── gemini_client.py   # Gemini client initialization, content generation, and cleanup.
│   │   └── session_manager.py # Session management for chat and translation.
│   └── utils/                 # Helper functions.
│       ├── __init__.py
│       └── browser.py         # Browser-based cookie retrieval.
├── models/                    # Models and wrappers (e.g., MyGeminiClient).
│   └── gemini.py
├── schemas/                   # Pydantic schemas for request/response validation.
│   └── request.py
├── config.conf                # Application configuration file.
└── run.py                     # Entry point to run the server.
```

---

## Developer Documentation

### Overview

The project is built on a modular architecture designed for scalability and ease of maintenance. Its primary components are:

- **app/main.py:** Initializes the FastAPI application, configures middleware, and manages application lifespan (startup and shutdown routines).
- **app/config.py:** Handles the loading and updating of configuration settings from `config.conf`.
- **app/logger.py:** Sets up a centralized logging system.
- **app/endpoints/:** Contains separate modules for handling API endpoints. Each module (e.g., `gemini.py` and `chat.py`) manages routes specific to their functionality.
- **app/services/:** Encapsulates business logic, including the Gemini client wrapper (`gemini_client.py`) and session management (`session_manager.py`).
- **app/utils/browser.py:** Provides helper functions, such as retrieving cookies from the browser for authentication.
- **models/:** Holds model definitions like `MyGeminiClient` for interfacing with the Gemini Web API.
- **schemas/:** Defines Pydantic models for validating API requests.

### How It Works

1. **Application Initialization:**  
   On startup, the application loads configurations and initializes the Gemini client and session managers. This is managed via the `lifespan` context in `app/main.py`.

2. **Routing:**  
   The API endpoints are organized into dedicated routers under `app/endpoints/`, which are then included in the main FastAPI application.

3. **Service Layer:**  
   The `app/services/` directory contains the logic for interacting with the Gemini API and managing user sessions, ensuring that the API routes remain clean and focused on request handling.

4. **Utilities and Configurations:**  
   Helper functions and configuration logic are kept separate to maintain clarity and ease of updates.

---

## 🐳 Docker Deployment Guide

For Docker setup and deployment instructions, please refer to the [Docker.md](Docker.md) documentation.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Amm1rr/WebAI-to-API&type=Date)](https://www.star-history.com/#Amm1rr/WebAI-to-API&Date)

## License 📜

This project is open source under the [MIT License](LICENSE).

---

> **Note:** This is a research project. Please use it responsibly, and be aware that additional security measures and error handling are necessary for production deployments.

<br>

[![](https://visitcount.itsvg.in/api?id=amm1rr&label=V&color=0&icon=2&pretty=true)](https://github.com/Amm1rr/)
