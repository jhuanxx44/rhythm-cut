# Architecture Decisions

## ADR-001：VLM-first，确定性约束后置

状态：accepted（首版）

Gemini 等 VLM 负责视觉语义理解；配色配额、动作覆盖、时间合法性和渲染由本地代码执行。原因是 VLM 的时间定位和计数能力不稳定，而这些约束需要可测试、可解释、可降级。

## ADR-002：TwelveLabs 不是核心路径

状态：accepted（首版）

TwelveLabs 作为未来可选检索 provider，不进入默认安装和 MVP 验收。首版先验证 Gemini + 本地抽帧/候选窗口是否足够。
