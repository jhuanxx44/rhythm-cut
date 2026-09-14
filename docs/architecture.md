# Architecture

## Pipeline

1. **Ingest**：读取素材、生成 SHA-256、调用 `ffprobe`，统一时间轴和代理文件。
2. **Audio analysis**：从音乐得到 beat grid、tempo、onset strength、能量段和候选切点。
3. **Candidate extraction**：PySceneDetect/固定窗口生成候选片段，保留 source in/out 帧。
4. **Visual analysis**：局部抽帧后调用 Gemini VLM，输出服装、配色、动作、遮挡、商品可见度和置信度；本地 CV 特征作为辅助证据。
5. **Selection**：在 beat slots 上求解配色配额、动作覆盖、镜头质量、动作转场和素材多样性的组合优化。
6. **Render**：Edit Plan 经 schema 校验后，由 FFmpeg 生成预览和 MP4；输出 render manifest 与日志。
7. **Critique**：Agent 读取结构化质量报告和联系表，不直接读取/修改任意媒体命令。

## Provider policy

Gemini 是早期默认 VLM。客户端从 `.env` 读取凭证、原生 API base URL 和 Vertex 路径所需的项目/区域；Provider 接口只接受一个视频窗口或帧包，返回 `ClipObservation`；调用记录必须包含 provider、model、prompt_version、输入 hash、时间窗口、采样 FPS、原始响应和错误。

TwelveLabs 不在核心依赖、默认配置或测试路径中。若未来接入，只能实现同一 provider 接口，并通过离线 fixture 验证，不得改变 domain schema。

## Selection policy

硬约束：每个 beat slot 至多一个镜头、候选时间合法、素材不越界、渲染参数一致。软约束：相邻配色差异、颜色配额、动作覆盖、动作转场、画面质量、来源片段多样性。候选不足时生成 `relaxations[]`，记录被放宽的约束和原因。

## Quality boundary

VLM 的时间戳是候选窗口，不是最终切点。最终切点必须 snap 到帧，并在前后窗口检查黑帧、遮挡、音画连续性和片段最小时长。

Phase 1 的本地输入层使用固定参数调用 `ffprobe` 并计算 SHA-256；节拍分析通过可选的 librosa
适配器提供，离线测试可使用固定 BPM 网格，不把默认 BPM 当作真实音频测量结果。

候选抽取先使用帧对齐的固定窗口实现；每个候选保留源帧的包含起点和排他终点。窗口生成不依赖
模型或随机数，PySceneDetect 只能作为后续增强路径。
