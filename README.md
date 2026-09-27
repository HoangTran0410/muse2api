<h1 align="center">muse2api</h1>

<p align="center">
  把 <a href="https://muse.ai">muse.ai</a> 网页端能力封装为 <b>OpenAI 兼容 API</b> 的异步网关
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/API-OpenAI%20Compatible-green" alt="OpenAI Compatible" />
  <img src="https://img.shields.io/badge/status-v0.1%20framework-orange" alt="Status" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License" />
</p>

---

## 目录

- [项目简介](#项目简介)
- [当前进度](#当前进度)
- [架构设计](#架构设计)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
- [API 使用示例](#api-使用示例)
- [配置项](#配置项)
- [路线图与可认领模块](#路线图与可认领模块)
- [参与开发](#参与开发)
- [致谢与声明](#致谢与声明)

## 项目简介

muse2api 把 muse.ai 的对话、文生图、文生视频能力，转换成标准的 OpenAI 接口（`/v1/chat/completions`、`/v1/images/generations` 等），这样现有的 OpenAI SDK、ChatGPT-Next-Web、LobeChat、Cherry Studio 等客户端改一下 `base_url` 就能直接使用。

和同类项目相比，本项目的重点是**工程化与可协作性**：

- **可插拔 Driver**：访问上游的方式被抽象成 `MuseDriver` 接口，目前有 Mock、浏览器（CDP）两种实现，另外预留了协议直连（HTTP）实现，互相不影响。
- **严格分层**：协议层、服务层、账号池、驱动层职责单一，每一层都可以单独开发和测试。
- **全异步**：基于 FastAPI + asyncio，CDP 客户端基于 `websockets` 实现，请求处理不占用阻塞线程。
- **账号池**：支持多种调度策略、单账号并发上限、失败冷却、会话失效自动下线，以及故障自动切换账号。
- **离线开发**：Mock 驱动不需要账号也不访问外网，前端和协议层可以独立推进。

## 当前进度

> **v0.1 框架阶段**：整体架构和基础功能的代码已经写完，但尚未跑过测试，也还没有用真实 muse.ai 账号联调。

| 模块 | 状态 | 说明 |
|---|---|---|
| OpenAI 协议层（chat 流式/非流式、images、videos、models） | ✅ 已实现 | 多轮对话、System Prompt、图片输入、模型别名 |
| 账号池（调度 / 冷却 / 失效下线 / 故障转移） | ✅ 已实现 | 支持 `lru`、`round_robin`、`affinity` 三种策略 |
| 后台任务（视频） | ✅ 已实现 | 创建任务后轮询结果；服务重启时未完成的任务会被标记为中断 |
| Admin API（账号增删改查、续期、重置、状态） | ✅ 已实现 | |
| Mock 驱动 | ✅ 已实现 | 离线假数据 |
| Browser 驱动（Chromium + CDP） | 🧪 待联调 | 对话、生图、生视频的完整流程已写好 |
| 会话续期 / 保活 | 🧪 待联调 | 基于 HTTP，默认关闭 |
| HTTP 协议直连驱动 | 🚧 预留 | 调用时返回 501 |
| `/v1/responses`、`/v1/images/edits` | 🚧 预留 | 调用时返回 501 |
| Web 管理面板、Cookie 导入扩展、额度查询 | 🚧 预留 | |

## 架构设计

```
          OpenAI SDK / Chat 客户端
                    │  HTTP (Bearer Key)
┌───────────────────▼────────────────────────────────────┐
│ api/          协议层：路由 · 请求校验 · 鉴权 · SSE 流式输出 │
├────────────────────────────────────────────────────────┤
│ services/     服务层：Gateway（故障转移）· TaskManager    │
├──────────────────────────┬─────────────────────────────┤
│ accounts/  账号池         │ core/  模型别名 · prompt 转换 │
│ 调度策略 · 冷却 · 续期     │        媒体存储               │
├──────────────────────────┴─────────────────────────────┤
│ drivers/      MuseDriver 接口（唯一接触上游的层）          │
│   ├─ mock      离线假数据                                │
│   ├─ browser   Chromium + CDP，每账号独立 BrowserContext │
│   └─ http      协议直连（预留）                           │
├────────────────────────────────────────────────────────┤
│ upstream/     muse.ai 的 URL、cookie 名、会话续期接口      │
└────────────────────────────────────────────────────────┘
                    │
                 muse.ai
```

**一次对话请求的处理流程**：路由解析模型别名，并把多轮 messages 合并成一条 prompt，然后交给 Gateway。Gateway 从账号池借出一个账号，调用 Driver 获取流式文本。如果失败，按错误类型更新账号状态：会话失效的账号会被下线，额度耗尽的账号进入冷却，其他错误短暂冷却。只要还没有向客户端输出任何内容，就自动换一个账号重试。

流式请求会先拿到第一段输出再返回 200，所以"没有可用账号""上游鉴权失败"这类错误会以正确的 HTTP 状态码返回，而不是输出到一半断掉的流。

更详细的设计说明见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 目录结构

```
muse2api/
├── src/muse2api/
│   ├── app.py                 # FastAPI 应用工厂与生命周期
│   ├── config.py              # 配置（环境变量 / .env）
│   ├── errors.py              # 错误体系 → HTTP 状态码 + OpenAI 错误格式
│   ├── api/
│   │   ├── deps.py            # 鉴权、依赖注入
│   │   ├── schemas.py         # OpenAI 请求模型
│   │   └── routes/            # chat / images / videos / media / models / admin / responses
│   ├── services/
│   │   ├── gateway.py         # 在账号池上执行驱动调用，失败时换号重试
│   │   ├── tasks.py           # 后台长任务
│   │   └── container.py       # 服务装配
│   ├── accounts/              # 账号模型、JSON 存储、账号池、会话保活
│   ├── core/                  # 模型注册与别名、prompt 转换、媒体存储
│   ├── drivers/
│   │   ├── base.py            # MuseDriver 接口与数据结构
│   │   ├── mock.py
│   │   ├── browser/           # cdp.py / chromium.py / dom.py / driver.py
│   │   └── http/              # 预留
│   └── upstream/muse.py       # 上游常量与会话续期
├── tests/                     # 基于 Mock 驱动的测试，不访问外网
├── docs/ARCHITECTURE.md
├── Dockerfile · docker-compose.yml · .env.example
└── CONTRIBUTING.md
```

## 快速开始

### 本地运行

```bash
git clone https://github.com/www222fff/muse2api.git
cd muse2api
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env      # 默认 MUSE2API_DRIVER=mock，不需要账号即可启动
python -m muse2api        # 默认监听 http://127.0.0.1:18610
```

如果没有设置 `MUSE2API_API_KEY`，首次启动时会自动生成一个密钥并保存到 `data/api_key`。

### Docker

```bash
cp .env.example .env
docker compose up -d --build
```

### 接入真实账号（browser 驱动）

1. 安装 Chromium 或 Chrome，并在 `.env` 中设置 `MUSE2API_DRIVER=browser`。
2. 在已登录 muse.ai 的浏览器里导出 cookie，至少需要 `hatch_sess`、`hatch_gw`、`hatch_vml`、`hatch_native_auth_device` 这四个。
3. 调用 Admin API 导入账号（见下文示例）。

## API 使用示例

所有 `/v1/*` 接口都需要在请求头中携带 `Authorization: Bearer <API_KEY>`；`/admin/*` 接口使用 `MUSE2API_ADMIN_KEY`，未设置时与 API Key 相同。

**对话（流式）**

```bash
curl http://localhost:18610/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"你好"}],"stream":true}'
```

**OpenAI Python SDK**

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:18610/v1", api_key="<API_KEY>")
resp = client.chat.completions.create(
    model="muse-chat",
    messages=[{"role": "user", "content": "写一首关于秋天的短诗"}],
)
print(resp.choices[0].message.content)
```

**文生图**

```bash
curl http://localhost:18610/v1/images/generations \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"prompt":"赛博朋克风格的雨夜街道","size":"16:9","response_format":"url"}'
```

**文生视频（异步任务）**

```bash
# 创建任务，返回 {"id": "task_xxx", "status": "queued", ...}
curl http://localhost:18610/v1/videos \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"prompt":"枫叶在微风中飘落","duration":5,"size":"16:9"}'

# 轮询任务状态，成功后 result.url 为视频地址
curl http://localhost:18610/v1/videos/task_xxx -H "Authorization: Bearer $KEY"
```

**导入账号**

```bash
curl http://localhost:18610/admin/accounts \
  -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"label":"acc1","cookies":{"hatch_sess":"...","hatch_gw":"...","hatch_vml":"...","hatch_native_auth_device":"..."}}'
```

### 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/healthz` · `/readyz` | 存活检查 · 就绪检查（驱动状态和可用账号数） |
| GET | `/v1/models` | 模型列表，包含 `gpt-4o`、`dall-e-3` 等别名 |
| POST | `/v1/chat/completions` | 对话，支持流式和非流式 |
| POST | `/v1/images/generations` | 文生图，返回 `url` 或 `b64_json` |
| POST | `/v1/videos` · GET `/v1/videos/{id}` | 创建视频任务 · 查询任务 |
| GET | `/v1/media/{name}` | 获取生成的媒体文件 |
| GET/POST/PATCH/DELETE | `/admin/accounts[/{id}]` | 账号增删改查 |
| POST | `/admin/accounts/{id}/renew` · `/reset` | 续期会话 · 重置账号状态 |
| GET | `/admin/status` · `/admin/tasks` | 服务状态 · 任务列表 |
| POST | `/v1/responses` · `/v1/images/edits` | 预留，当前返回 501 |

## 配置项

所有配置都通过环境变量（前缀 `MUSE2API_`）或 `.env` 文件设置，完整列表见 [.env.example](.env.example)。常用配置如下：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MUSE2API_DRIVER` | `mock` | 驱动类型：`mock` / `browser` / `http` |
| `MUSE2API_HOST` · `MUSE2API_PORT` | `127.0.0.1` · `18610` | 监听地址与端口 |
| `MUSE2API_API_KEY` | 自动生成 | `/v1/*` 接口的鉴权密钥 |
| `MUSE2API_ADMIN_KEY` | 同 API Key | `/admin/*` 接口的鉴权密钥 |
| `MUSE2API_PUBLIC_BASE` | 空 | 对外访问地址，用于拼接媒体链接；留空时根据请求自动推断 |
| `MUSE2API_POOL_STRATEGY` | `lru` | 账号调度策略：`lru` / `round_robin` / `affinity` |
| `MUSE2API_MAX_FAILOVER` | `2` | 失败后最多换号重试的次数 |
| `MUSE2API_CHROMIUM_PATH` | 自动探测 | 浏览器可执行文件路径 |
| `MUSE2API_KEEPALIVE_ENABLED` | `false` | 是否在后台定期续期会话 |

## 路线图与可认领模块

| 模块 | 位置 | 说明 |
|---|---|---|
| HTTP 协议直连驱动 | `drivers/http/` | 抓包整理协议文档，实现不依赖浏览器的对话和生成 |
| 复用会话线程 | `drivers/browser/` + `AffinityStrategy` | 同一会话复用线程，降低首字延迟 |
| `/v1/responses` | `api/routes/responses.py` | 适配 Responses API（Codex 等客户端使用） |
| `/v1/images/edits` | `api/routes/images.py` | 支持 multipart 上传参考图 |
| 额度查询 | `MuseDriver.quota` | 读取账号用量，作为调度依据 |
| Web 管理面板 | `web/`（新建） | 基于 `/admin/*` API 开发 |
| Cookie 导入扩展 | `extension/`（新建） | 一键把浏览器登录态推送到账号池 |
| 存储后端 | `accounts/store.py` | 用 SQLite 或 Redis 实现 `AccountStore` |
| Tool calling | `core/prompt.py` | 通过提示词模拟 function calling |
| 可观测性 | `observability/`（新建） | Prometheus 指标、请求日志 |

代码中标记为 `TODO(contributors)` 的地方就是预留的扩展点。

## 参与开发

欢迎认领上表中的模块。开始之前请先开一个 issue 说明要做的内容，开发约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
pytest           # 测试全部基于 Mock 驱动
ruff check .     # 代码风格检查
```

## 致谢与声明

- 设计上参考了 [czg86389-hub/muse2api](https://github.com/czg86389-hub/muse2api)（用 CDP 驱动网页的思路），以及 gemini2api / gemini-webapi 一类项目（协议直连、cookie 续期）。本项目的代码是独立实现的。
- 本项目仅供学习与技术研究使用，请遵守 muse.ai 的服务条款及当地法律法规。请勿提交或公开任何账号 cookie。

## License

[MIT](LICENSE)
