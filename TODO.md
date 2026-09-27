# TODO

本文件列出所有预留模块和待完成的工作，是任务分工的唯一来源。

**认领方式**：先开一个 issue，标题写 `[认领] 任务编号 任务名`（例如 `[认领] B1 HTTP 协议直连驱动`），然后在下表"负责人"一栏填上你的 GitHub ID 并提交 PR，避免多人重复开发。开发约定见 [CONTRIBUTING.md](CONTRIBUTING.md)，架构说明见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

优先级：**P0** 必须先完成 · **P1** 核心功能 · **P2** 体验增强 · **P3** 锦上添花

---

## 总览

| 编号 | 任务 | 优先级 | 位置 | 负责人 | 状态 |
|---|---|---|---|---|---|
| A1 | 安装依赖、跑通测试和 lint | P0 | `tests/` | | 待开始 |
| A2 | Browser 驱动真实账号联调 | P0 | `drivers/browser/` | | 待开始 |
| A3 | 验证生图 / 生视频的触发方式 | P0 | `drivers/browser/driver.py` | | 待开始 |
| A4 | 验证会话续期 | P0 | `upstream/muse.py` | | 待开始 |
| A5 | 验证 Docker 镜像构建与运行 | P1 | `Dockerfile` | | 待开始 |
| A6 | 启用 GitHub Actions CI | P1 | `.github/workflows/ci.yml` | | 待开始 |
| B1 | HTTP 协议直连驱动 | P1 | `drivers/http/` | | 待开始 |
| B2 | 复用会话线程，降低首字延迟 | P2 | `drivers/browser/` | | 待开始 |
| B3 | 额度查询 | P2 | `MuseDriver.quota` | | 待开始 |
| C1 | `/v1/responses` 接口 | P1 | `api/routes/responses.py` | | 待开始 |
| C2 | `/v1/images/edits` 接口 | P1 | `api/routes/images.py` | | 待开始 |
| C3 | 模拟 Tool calling | P2 | `core/prompt.py` | | 待开始 |
| C4 | 流式心跳，避免客户端超时 | P2 | `api/routes/chat.py` | | 待开始 |
| D1 | 支持多种 cookie 导入格式 | P1 | `api/routes/admin.py` | | 待开始 |
| D2 | Cookie 导入浏览器扩展 | P2 | `extension/`（新建） | | 待开始 |
| D3 | Web 管理面板 | P2 | `web/`（新建） | | 待开始 |
| D4 | SQLite / Redis 存储后端 | P3 | `accounts/store.py` | | 待开始 |
| E1 | 媒体文件自动清理 | P2 | `core/media.py` | | 待开始 |
| E2 | 多 API Key 与限流 | P3 | `api/deps.py` | | 待开始 |
| E3 | 可观测性（指标、日志） | P3 | `observability/`（新建） | | 待开始 |

---

## A. 验证与联调

v0.1 的代码已全部写完，但尚未运行过。这一组任务要最先完成，否则后面的开发缺少可信的基础。

### A1 安装依赖、跑通测试和 lint · P0
- 执行 `pip install -e '.[dev]'`、`pytest`、`ruff check .`，修复所有失败项。
- 测试全部基于 Mock 驱动，不访问外网。
- **完成标准**：本地 `pytest` 和 `ruff check .` 全部通过。

### A2 Browser 驱动真实账号联调 · P0
- 用真实 muse.ai 账号导入 cookie，设置 `MUSE2API_DRIVER=browser`，逐项验证：
  - 页面能加载到"就绪"状态（`dom.PAGE_STATE`）；
  - 输入框写入和发送按钮点击生效（`dom.fill_input`、`dom.CLICK_SEND`）；
  - 助手回复能被正确读取，流式增量无重复、无丢字（`dom.CHAT_STATE`）；
  - 回复结束判断准确，既不会提前截断，也不会多等很久；
  - cookie 失效时抛出 `UpstreamAuthError`，额度用完时抛出 `UpstreamQuotaError`。
- 网页选择器尚未在真实页面上验证过，可能不准确或已经过时，需要按实际页面修改 `drivers/browser/dom.py`。
- 验证 `Target.createBrowserContext` 的多账号隔离是否正常。
- **完成标准**：两个以上账号能稳定完成流式和非流式对话，并在 `docs/` 中记录联调结论。

### A3 验证生图 / 生视频的触发方式 · P0
- 目前是在提示词前加 "Generate an image / a video" 来触发（`BrowserDriver._media_prompt`），需要确认 muse.ai 是否每次都按要求生成。
- 如果网页上有专门的生图 / 生视频入口（按钮、模式切换等），改为走该入口。
- 确认画幅（`16:9` 等）和视频时长的指定方式是否生效。
- 确认生成结果的附件选择器（`dom.ATTACHMENT`）和下载逻辑（`dom.fetch_as_base64`）。
- **完成标准**：文生图、带首帧的文生视频都能稳定拿到文件。

### A4 验证会话续期 · P0
- 验证请求 `/api/session` 是否确实会返回新的 cookie、延长 `hatch_vml` 的有效期。
- 验证 `/api/hatch/vm/wake` 的参数和效果。
- 确认合理的续期间隔，更新 `MUSE2API_KEEPALIVE_INTERVAL` 的默认值。
- **完成标准**：打开 keepalive 后，账号能连续 3 天以上保持可用。

### A5 验证 Docker 镜像构建与运行 · P1
- `docker compose up -d --build` 能构建成功，browser 驱动能在容器内启动 Chromium。
- 确认容器以非 root 用户运行时 Chromium 的沙箱参数是否需要调整。

### A6 启用 GitHub Actions CI · P1
- 仓库已包含 `.github/workflows/ci.yml`（Python 3.10 / 3.12 下跑 lint 和测试）。
- 用 token 推送该文件需要 `workflow` 权限，用 SSH 推送则不需要。
- **完成标准**：PR 能自动跑 CI 并显示结果。

---

## B. 驱动层

### B1 HTTP 协议直连驱动 · P1
不启动浏览器，直接和 muse.ai 后台通信。可以省掉 Chromium，显著降低延迟和内存占用。
1. 抓包分析网页发消息时的通信过程（接口地址、握手方式、数据帧格式、鉴权头），整理成 `docs/protocol.md`。
2. 在 `drivers/http/` 下实现传输客户端，用账号的 cookie 建立会话。
3. 实现 `chat_stream`：把上游的增量事件转换成文本片段。
4. 实现生图、生视频和附件下载。
5. 用录制下来的真实响应做测试数据，CI 中不访问真实服务。
- 更详细的分步说明见 `drivers/http/driver.py` 顶部注释。
- **完成标准**：`MUSE2API_DRIVER=http` 下对话功能可用，并且能通过和 browser 驱动相同的接口测试。

### B2 复用会话线程，降低首字延迟 · P2
- 目前 browser 驱动每次请求都打开一个新对话，页面加载会增加几秒延迟。
- 思路：配合账号池的 `AffinityStrategy`，同一个客户端（`user` 字段）的连续请求复用同一个对话页面，只发送新增的消息。
- 需要处理：怎么判断客户端发来的历史和页面上的对话一致；对话过长时如何重开；页面卡死时如何恢复。
- **完成标准**：连续对话的首字延迟明显降低，并且不会把不同用户的上下文混在一起。

### B3 额度查询 · P2
- 实现 `MuseDriver.quota`，读取账号的套餐、每周用量、剩余额度。
- 在 `/admin/accounts` 中展示额度信息，调度时可以优先选择额度充足的账号。
- 同时在 `DriverCapabilities` 中声明 `quota=True`，并在 `MockDriver` 中提供假实现。

---

## C. 协议层

### C1 `/v1/responses` 接口 · P1
- 适配 OpenAI Responses API（Codex 等新客户端默认使用）。
- 把 `input` 和 `instructions` 转换后交给 `flatten_messages`，复用 `Gateway.chat_stream`。
- 流式输出需要按 Responses API 的事件格式（`response.created`、`response.output_text.delta`、`response.completed` 等）发送。
- **完成标准**：官方 OpenAI SDK 的 `client.responses.create()` 流式和非流式都能正常调用。

### C2 `/v1/images/edits` 接口 · P1
- 解析 multipart 表单（`image` / `image[]`、`prompt`、`size`、`response_format`）。
- 把上传的图片放进 `ImageRequest.reference_images`，响应格式复用 `generate_images` 的逻辑。
- **完成标准**：官方 SDK 的 `client.images.edit()` 能正常调用。

### C3 模拟 Tool calling · P2
- muse.ai 本身不支持 function calling。可以在提示词中描述可用工具和输出格式，再从回复中解析出工具调用，转换成 OpenAI 的 `tool_calls` 格式。
- muse.ai 可能拒绝按指定格式输出，所以要先验证可行性，做成可配置开关，默认关闭。

### C4 流式心跳，避免客户端超时 · P2
- 流式请求会先等拿到第一段文字再返回响应，最长可能要等 45 秒（`first_token_timeout`），部分客户端或反向代理会因此超时断开。
- 方案：可配置为先返回 200，在等待期间定时发送 SSE 注释行（`: keepalive`）作为心跳。需要权衡的是，这样做之后，出错时就无法再返回 HTTP 错误码。

---

## D. 账号与管理

### D1 支持多种 cookie 导入格式 · P1
- 目前 `/admin/accounts` 只接受 `{"cookies": {"名称": "值"}}` 格式。
- 增加支持：浏览器请求头里的 `Cookie: a=1; b=2` 字符串、EditThisCookie 等插件导出的 JSON 数组（其中包含过期时间）。
- 支持一次批量导入多个账号。

### D2 Cookie 导入浏览器扩展 · P2
- 新建 `extension/` 目录，开发一个 Chrome / Edge 扩展。
- 用户在已登录 muse.ai 的浏览器里点一下扩展图标，就能读取所有 cookie（包括 JS 读不到的 HttpOnly cookie 及其过期时间），推送到 `/admin/accounts`。
- 需要处理服务端的 CORS 配置。

### D3 Web 管理面板 · P2
- 新建 `web/` 目录，基于现有的 `/admin/*` 接口开发。
- 功能：服务状态、账号列表（状态 / 冷却 / 错误 / 额度）、导入与编辑账号、任务列表、媒体库、在线调试接口。
- 技术栈不限。优先考虑构建产物可以直接由 FastAPI 以静态文件形式提供，不增加部署步骤。

### D4 SQLite / Redis 存储后端 · P3
- 实现 `accounts/store.py` 中的 `AccountStore` 协议，通过配置切换。
- Redis 版本可以为将来多实例部署做准备（这时账号并发计数也需要改成跨进程共享）。

---

## E. 运维

### E1 媒体文件自动清理 · P2
- 生成的图片和视频会一直保存在 `data/media/`，没有清理机制。
- 增加保留时长或容量上限配置，后台定时清理。

### E2 多 API Key 与限流 · P3
- 目前只有一个 API Key 和一个管理密钥。
- 支持多个 Key（可以为每个 Key 单独设置限流和用量统计），并通过管理接口管理。

### E3 可观测性 · P3
- 提供 Prometheus 指标：请求数、耗时、首字延迟、各账号成功 / 失败次数、队列等待时间。
- 结构化请求日志，每个请求带唯一 ID 方便排查。
