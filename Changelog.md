### Changelog – WebAI to API

#### v0.5.0 – 2026-02-06

##### 重构 (Refactor)

- 依赖迁移: 迁移至 `uv` 包管理器，移除 Poetry，采用 PEP 621 标准的 `pyproject.toml`。
- 配置精简: 移除 Docker 相关文件 (`Dockerfile`, `docker-compose.yml`, `Makefile`)。
- 启动更新: 修改 `run.bat` 使用 `uv run` 启动服务。

##### 新增 (Added)

- 功能: 支持图片上传。
- 功能: 支持流式传输。
- 功能: 新增 Debug 模式，支持记录 API 请求与响应日志。
- 功能: 增加鉴权机制。
- 功能: 增加读取不同账户数据的能力。
- 功能: 启动脚本默认开放公网访问。
- 功能: 增加 Cookies 相关测试脚本，优化连接稳定性。
- 模型: 更新默认 Gemini 模型为 3.0 Pro。

##### 修复 (Fixed)

- 逻辑: 修复读取本地 Cookies 的逻辑。
- 系统: 统一服务运行函数，实现一致且优雅的关闭机制。

##### 构建 (Build)

- 依赖: 增加 `websocket`、`nodriver`、`platformdirs` 等依赖支持。
- 依赖: 更新依赖版本以规避报错。

---

#### v0.4.0 – 2025-06-27

##### Added

- Displayed a user message explaining how to use the `gpt4free` server.

##### Fixed

- Resolved execution issue on Windows 11.
- Improved error handling with appropriate user-facing messages.

##### Changed

- Updated internal libraries and dependencies.

---

#### v0.3.0 – 2025-06-25

##### Added

- Improved server startup information display, including available services and API endpoints.
- Added a new method using the [gpt4free v0.5.5.5](https://github.com/xtekky/gpt4free) library, which also functions as a fallback.
- Introduced support for switching between models using keyboard shortcuts (keys `1` and `2`) in the terminal.
- WebAI-to-API now uses your browser and cookies **only for Gemini**, resulting in faster performance.
- `gpt4free` integration provides access to multiple providers (ChatGPT, Gemini, Claude, DeepSeek, etc.), ensuring continuous availability of various models.

##### Changed

- Updated internal libraries.
- Upgraded to [Gemini API v1.14.0](https://github.com/HanaokaYuzu/Gemini-API).

##### Fixed

- Ensured compatibility with Windows (tested on Windows 11).
