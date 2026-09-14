# 工程起始发现

- 产品核心是约束优化，不是单次视频生成。
- 早期 VLM-first 的最小闭环应先使用 Gemini 对短窗口做结构化观察，并保存原始响应快照。
- 本地确定性层负责 beat grid、帧级边界、配额、动作转移和 FFmpeg；这样模型替换不会改变 Edit Plan 契约。
- TwelveLabs 未来可做语义检索加速，但不应成为首版数据路径或部署前置条件。
- 当前仓库没有 `tests/fixtures` 或真实媒体；离线契约尚未覆盖 ingest、beat、candidate、selection、render。
- `EditPlan` 当前主要是字段级校验；一个 1 秒计划包含 100 秒镜头时 CLI 仍返回 valid，全局时长、排序和重叠约束需要在 Phase 0 落地。
