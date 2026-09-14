# Rhythm Cut

服装带货素材的 AI 卡点剪辑工具。

Rhythm Cut 将音轨节拍与服装素材的视觉属性结合起来，生成一份可解释的 `Edit Plan`：每个镜头记录时间、来源片段、商品、配色、动作、节拍和置信度。Gemini 等 VLM 用于视觉理解，确定性代码负责配额约束、候选选择和 FFmpeg 渲染。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
rhythm-cut --help
```

当前仓库是工程骨架，默认不调用外部模型、不包含真实媒体。先用 `tests/fixtures` 和 `local/` 建立离线契约，再接入 Gemini。

实时 Gemini 调用使用 `.[providers]` 可选依赖和项目根目录的 `.env`：`GEMINI_API_KEY`、`GEMINI_BASE_URL`、`GOOGLE_CLOUD_PROJECT` 与 `GOOGLE_CLOUD_LOCATION`。可用 `scripts/smoke_gemini38.py` 做一次脱敏连通性检查；`.env` 永不提交。

## 设计边界

- 不依赖 `me-wiki` 或其他知识库运行时。
- 不把 TwelveLabs 作为核心依赖；它未来只能通过 provider 插件接入。
- 不让 Agent 直接生成任意 shell/FFmpeg 命令。
- 同一输入 manifest、模型响应快照和配置应能复现同一份 Edit Plan。

详见 [docs/architecture.md](docs/architecture.md) 和 [task_plan.md](task_plan.md)。
