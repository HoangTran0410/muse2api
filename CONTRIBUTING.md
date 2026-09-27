# 参与开发

## 环境

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest && ruff check .
```

默认 `MUSE2API_DRIVER=mock`，不需要账号即可开发 API 层与前端。

## 认领模块

可认领模块列表见 [docs/ARCHITECTURE.md#路线图--可认领模块](docs/ARCHITECTURE.md)。开始前请先开一个 issue 说明要做的模块，避免重复劳动。代码中标记为 `TODO(contributors)` 的位置是预留的扩展点。

## 约定

- 依赖方向：`api → services → accounts/core → drivers → upstream`，不要反向引用。
- 与 muse.ai 页面结构相关的内容只放在 `drivers/browser/dom.py`，上游 URL/cookie 名只放在 `upstream/muse.py`。
- 新增 driver 能力时同步更新 `DriverCapabilities`，并在 `MockDriver` 中提供假实现，保证测试不依赖外网。
- 上游错误必须映射到 `errors.py` 中的类型；不要在 driver 里吞掉异常。
- CI 中不允许访问真实 muse.ai；需要上游数据的测试请使用录制的 fixture。
- 不要提交 cookie、`data/` 目录或 `.env`。

## 新增一个 Driver

1. 在 `src/muse2api/drivers/<name>/` 下实现 `MuseDriver` 子类。
2. 在 `drivers/registry.py` 注册，并把名字加到 `config.DriverName`。
3. 至少实现 `chat_stream`，其余能力未实现时保持抛出 `FeatureNotImplemented`。
4. 补充测试与文档。

## 提交

- 分支：`feat/<模块>`、`fix/<问题>`。
- 提交前确保 `pytest` 与 `ruff check .` 通过。
