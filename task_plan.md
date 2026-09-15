# Rhythm Cut 工程计划

## 目标

建立独立于 me-wiki 的服装带货短视频卡点剪辑工程，首版以 Gemini 等 VLM 为主完成素材理解，以本地确定性代码完成约束选择和 FFmpeg 渲染。

## 阶段

- [x] 创建独立目录、git 仓库和 Python 包骨架
- [x] 编写项目级 AGENTS.md，冻结 VLM-first / TwelveLabs-optional 边界
- [x] 定义 `ClipObservation`、`BeatPoint`、`Shot`、`EditPlan` 数据契约
- [x] 建立 provider 边界和 Gemini 占位适配器
- [x] 建立离线模型校验测试与质量门文档
- [~] 加入音频 beat analyzer（librosa）和 ffprobe ingest（基础实现完成，真实音频验证待补）
- [~] 加入候选镜头抽取（固定窗口已完成，PySceneDetect 待补）
- [ ] 接入 Gemini 录制响应 fixture，再实现 live provider
- [x] 实现贪心+回溯选择器和 relaxations 报告
- [ ] 实现 FFmpeg preview/render 与端到端样例
- [ ] 建立人工标注集、回归评测和成本/延迟记录

## 推进路径（按依赖顺序）

### Phase 0：冻结可执行契约（已完成）

目标：让 `EditPlan` 的全局约束可以被机器拒绝，而不只做字段级校验。

产物：

- `tests/fixtures/` 下的最小合法/非法 JSON fixture。
- 对 `EditPlan` 增加镜头时间不越界、按时间排序、不可重叠等校验；明确 beat 是否允许重复。
- 明确 Asset manifest、fps、帧与秒之间的换算规则，并同步 `docs/edit-plan.md`。

验收：非法计划在 CLI `validate` 阶段失败；合法计划 round-trip 后字节级稳定。

### Phase 1：离线媒体输入和节拍网格（基础实现完成）

目标：不调用模型，从音频和视频得到可复现的输入 manifest、帧率和 beat grid。

产物：`analysis/ingest.py`、`analysis/beats.py`、固定 WAV/MP4 fixture、输入 SHA-256 和 ffprobe 记录。

验收：同一文件和配置重复运行得到相同 manifest 与 beat 点；缺少 ffprobe 或损坏媒体有结构化错误。

### Phase 2：候选镜头抽取

状态：固定窗口基础实现完成；PySceneDetect 增强和真实视频 fixture 待补。

目标：先用固定窗口建立确定性候选集，再接 PySceneDetect 作为可选增强。

产物：候选片段 domain 模型，保留 source in/out frame、时间窗口和来源证据；固定窗口抽取器及测试。

验收：候选不越界、最小时长和帧边界满足配置；同一输入候选顺序稳定。

### Phase 3：VLM fixture 到 Gemini live

目标：先验证 provider 归一化，再接真实 Gemini。

产物：录制响应 fixture、prompt version、输入 hash、采样 FPS、原始响应和错误记录；Gemini live adapter 保持同一接口。

验收：离线 fixture 能完整生成 `ClipObservation`；live 调用只增加联网验收，不改变 domain schema。

### Phase 4：选择器和降级报告（已完成）

目标：在 beat slots 上完成可解释的贪心 + 有界回溯选择。

产物：颜色配额、动作覆盖、质量、多样性和动作转场评分；`relaxations[]` 记录每次放宽及原因。

验收：合成候选矩阵覆盖“可满足、候选不足、完全不可满足”三类；结果稳定且每个 slot 至多一个镜头。

实现：固定排序的候选评分、有限搜索节点的回溯、候选不复用、颜色配额和动作覆盖目标；不可满足目标进入 `EditPlan.relaxations`。

### Phase 5：FFmpeg 预览和成片

目标：把已校验的 `EditPlan` 转成预览和 MP4，并留下可审计 manifest。

产物：受控的 FFmpeg 参数生成器、preview/render 命令、render manifest 和结构化日志。

验收：合成媒体渲染成功；输出帧率、时长、音频存在性和音画漂移通过自动检查。真实素材质量另行标记。

### Phase 6：评测、成本和发布门

目标：建立人工标注和回归证据，决定是否进入真实使用。

产物：小规模标注集、回归报告、模型/提示词版本、成本与延迟记录、失败样本集。

验收：质量门中的误差、覆盖率和可用镜头比例有明确分母与样本；代码、测试、媒体渲染、部署和产品质量分别出具状态。

## 推荐的首个纵向切片

先完成 Phase 0 + Phase 1 的最小版本，再用固定候选和手写 `ClipObservation` 接通 Phase 4 与 Phase 5。这样可以先证明“输入 → 选择 → 渲染”的确定性闭环，再引入 Gemini 和 PySceneDetect，避免多个未完成模块同时耦合。

## 暂不进入 MVP

- TwelveLabs provider、在线检索和生产部署。
- 自动学习动作语义、复杂多目标跟踪和大规模标注平台。
- 任何未经过 fixture 和 schema 校验的模型输出直接进入渲染。

## 决策

- 核心 domain 不依赖任意 VLM SDK。
- TwelveLabs 不进入 MVP 安装、配置和验收路径。
- VLM 输出必须经过 schema 校验；时间戳只能作为候选窗口。
- 先做预标注或小规模人工校验闭环，再扩大自动化。

## 风险

- 快动作下 VLM 时间定位过粗。
- 灯光和背景造成服装颜色误判。
- 动作 A/B/C/D 的语义边界需要业务方定义。
- 素材不足时无法同时满足节拍、颜色和动作约束，必须显式降级。
