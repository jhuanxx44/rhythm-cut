# Edit Plan Contract

`EditPlan` 是 Agent 与剪辑执行器之间的唯一写接口。它必须可序列化、可校验、可复现。

每个 shot 至少包含：`timeline_start_s`、`timeline_end_s`、`source_asset_id`、`source_in_frame`、`source_out_frame`、`beat_id`、`color_id`、`action_id` 和 `evidence_refs`。

`EditPlan` 的全局约束由 schema 校验：镜头必须按 `timeline_start_s` 非递减排序、不得重叠、不得超过 `duration_s`，且一个 `beat_id` 至多对应一个镜头。允许镜头之间存在空档。

素材先通过 `AssetManifest` 固定媒体身份和帧语义：`sha256` 是输入文件哈希，`duration_s` 使用秒，`fps` 使用帧/秒，`frame_count` 是源媒体总帧数。`source_in_frame` 为包含起点，`source_out_frame` 为排他终点；VLM 时间戳只能转换为候选窗口，不能直接作为最终切点。

禁止字段：任意 shell 命令、任意 Python 代码、未经过 schema 校验的 URL、未标注单位的时间值。
