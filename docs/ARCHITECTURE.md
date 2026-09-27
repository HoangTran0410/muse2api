# 架构设计

## 分层

```
┌─────────────────────────────────────────────────────────────┐
│ api/            OpenAI 协议层（FastAPI 路由、schema、鉴权）   │
│   routes/chat.py  images.py  videos.py  media.py  admin.py   │
├─────────────────────────────────────────────────────────────┤
│ services/       服务层                                        │
│   gateway.py    在账号池上执行 driver 调用 + 故障转移          │
│   tasks.py      后台长任务（视频等）                           │
│   container.py  依赖装配（app.state.services）                 │
├──────────────────────────────┬──────────────────────────────┤
│ accounts/  账号池             │ core/  与上游无关的纯逻辑      │
│   model / store / pool        │   models   模型注册与别名      │
│   keepalive  会话续期          │   prompt   messages→单条 prompt│
│                               │   media    媒体落盘/图片输入    │
├──────────────────────────────┴──────────────────────────────┤
│ drivers/        唯一与 muse.ai 交互的层                        │
│   base.py   MuseDriver 抽象 + 请求/结果数据结构                │
│   mock.py   离线驱动                                          │
│   browser/  Chromium + CDP（cdp.py / chromium.py / dom.py）    │
│   http/     协议直连（预留）                                   │
├─────────────────────────────────────────────────────────────┤
│ upstream/muse.py  上游常量（URL、cookie 名）与 HTTP 会话续期    │
└─────────────────────────────────────────────────────────────┘
```

依赖方向严格自上而下：`api → services → accounts/core → drivers → upstream`。路由不直接调用 driver，driver 不感知 HTTP 协议格式。

## 一次请求的生命周期（chat）

1. `routes/chat.py` 校验请求 → `resolve_model` 解析别名 → `flatten_messages` 把多轮消息压成一条 prompt 并提取图片。
2. `Gateway.chat_stream` 通过 `AccountPool.lease()` 借出一个账号（按策略挑选、受单账号并发上限约束）。
3. 调用 `driver.chat_stream(account, ChatRequest)`，得到文本增量。
4. 失败时：
   - `UpstreamAuthError` → 账号标记 `invalid`；
   - `UpstreamQuotaError` → 冷却 ≥1 小时；
   - 其他可重试错误 → 冷却 `account_cooldown` 秒；
   - 若还没有向客户端输出任何内容，自动换号重试（最多 `max_failover` 次）。
5. 流式场景下，路由先拉取第一个增量再返回 200，保证"无可用账号 / 上游鉴权失败"等错误以正确的 HTTP 状态码返回。

## Driver 契约

```python
class MuseDriver(ABC):
    name: str
    requires_account: bool
    capabilities: DriverCapabilities

    async def startup(self) / shutdown(self)
    async def health(self) -> dict
    def chat_stream(self, account, ChatRequest) -> AsyncIterator[str]   # 必须实现
    async def generate_image(self, account, ImageRequest) -> list[MediaResult]
    async def generate_video(self, account, VideoRequest) -> MediaResult
    async def renew_session(self, account) -> SessionInfo
    async def quota(self, account) -> dict
```

- 未实现的能力抛 `FeatureNotImplemented`（HTTP 501），上层据此降级。
- 错误必须映射到 `errors.py` 中的 `Upstream*` 类型，账号池依赖它们判断账号状态。
- driver 不负责重试、落盘、URL 拼装。

## Browser 驱动要点

- 一个 Chromium 进程；每个账号一个 `Target.createBrowserContext` 隔离上下文 + 一个复用的 tab，切号无需清 cookie。
- 所有 DOM 选择器与页面脚本集中在 `drivers/browser/dom.py`，muse.ai 改版时通常只需改这一个文件。
- 输入通过原生 setter + `input` 事件写入 textarea（React 可感知，长文本也快），失败时回退 Enter 键。
- 输出检测：轮询最后一个助手气泡文本做增量；Stop 按钮消失且文本稳定即结束。
- 媒体：等待新出现的附件节点，在页面上下文内 `fetch(blob:)` 转 base64 取回字节。

## 路线图 / 可认领模块

预留模块和待完成的工作统一记录在根目录的 [TODO.md](../TODO.md)。
