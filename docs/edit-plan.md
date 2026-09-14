# Edit Plan Contract

`EditPlan` 是 Agent 与剪辑执行器之间的唯一写接口。它必须可序列化、可校验、可复现。

每个 shot 至少包含：`timeline_start_s`、`timeline_end_s`、`source_asset_id`、`source_in_frame`、`source_out_frame`、`beat_id`、`color_id`、`action_id` 和 `evidence_refs`。

禁止字段：任意 shell 命令、任意 Python 代码、未经过 schema 校验的 URL、未标注单位的时间值。
