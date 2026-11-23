---
name: apparatus-route-diagrammer
description: Use when experimental components, plumbing connections, process steps and technical-route phases must become one traceable apparatus and workflow figure.
---

# 实验装置与技术路线图

## 用途与适用条件

从装置清单、装配说明、方法段落或工艺描述中抽取部件与接口、管路连接与流向、步骤编号与分支回流、技术路线阶段与里程碑，生成装置结构图 + 流程图 + 技术路线图的结构规格，并校验部件可追溯、连接方向成立、步骤编号与正文一致。

适用条件：`/input/case.json`（或 `--case`）含部件表、连接表、步骤列表、阶段计划或装置描述文本，要求交付可编辑图稿与导出件。典型键：`components`/`parts`、`connections`、`steps`、`phases`/`milestones`、`flow`、`legend`。

不适用：不判断实验方案的科学合理性，不做数据拟合，不补造未给出的部件、管路或阶段。

## 输入

- `/input/case.json`：主输入。
- `/input/task.md`：存在时补充图型、阶段划分与导出格式。
- 引用的本地文本/JSON/CSV 会被实际读取；缺失登记到 `errors`/`uncertainty`。
- 仅标准库；不联网、不写 `/input`。

## 处理流程

1. **读入素材**：加载 case.json、task.md 与引用文件，记录来源哈希。
2. **部件抽取**：读取显式 `components`/`parts`；缺失时按部件后缀（泵、阀、反应器、柱、检测器、传感器、电极、膜、芯片等）从文本抽取，并识别接口（inlet/outlet/port）。
3. **连接与流向**：读取显式 `connections`；缺失时解析“A→B”“A 流入 B”“从 A 到 B”等表达，记录介质（物料/能量/信号）与方向。
4. **步骤顺序**：抽取带编号的步骤，保留原文与编号；识别主序列、并行支路、循环回流与终止条件。
5. **技术路线**：抽取阶段/里程碑，记录阶段目标、方法、输入输出与依赖。
6. **一致性校验**：部件未在连接中出现、连接端点悬空、同一对部件双向矛盾流、步骤编号重复/跳号/乱序、阶段依赖成环、阶段缺输出、图例线型与连接类型不符。
7. **布局约束**：装置按接口对齐与局部放大给出约束；流程按主序列自上而下、支路并列；路线按阶段横向推进。
8. **导出计划**：登记格式与检查项，`performed=false`。
9. **契约落盘**：保留 `case_id` 与全部 `output_contract` 字段。

## 评分维度对应

- **实际效果**：部件、连接、方向、步骤顺序、阶段推进均可回溯。
- **完整性**：覆盖装置结构、步骤流程、材料流向、技术路线、图例、导出六类要素。
- **可核验性**：每个部件/连接/步骤带来源与原文证据。
- **创新增益**：装置清单到接口—连接的映射、步骤编号一致性检查、阶段依赖建模。
- **可靠体验**：缺方向、矛盾流、跳号、成环均显式标记并降级。

## 输出契约

`/app/output/result.json` 顶层保留 `case_id`、`output_contract` 全部字段、`status`、`result`、`evidence`、`uncertainty`、`errors`、`stats`、`skill`、`challenge_id`、`contract_notes`。未支持字段写 `null` 并记录原因。

主要交付段：`result.apparatus_spec`、`result.process_flow`、`result.route_spec`、`result.consistency_checks`、`result.export_plan`。

## 异常处理

| 情况 | 处理 | 输出表现 |
|---|---|---|
| case.json 缺失/非法 | 结构化失败 | 退出码 `2`，`status=insufficient_input`/`failed` |
| 无部件或无步骤 | 不编造装置 | `status=partial`/`insufficient_input` |
| 连接端点缺失 | 保留连接并标悬空 | `dangling_connection` |
| 同对部件双向矛盾流 | 保留双方 | `contradictory_flow`，不擅自择一 |
| 步骤跳号/重复 | 保留原文 | `step_number_gap`/`step_number_duplicate` |
| 阶段依赖成环 | 保留并标环 | `phase_dependency_cycle` |
| 阶段缺输出 | 不补造 | `phase_missing_output` |
| 渲染工具缺失 | 只给导出计划 | `export_plan[].performed=false` |

## 限制

部件与接口抽取依赖显式清单与有限后缀/连接词；剖面图、三维装配关系与未写出的管路无法还原。布局是约束规格，不是像素结果。

## 最小调用示例（示例，非官方案例结果）

```bash
python scripts/run_skill.py --case /input/case.json --out /app/output/result.json
```

示例输入（示意）：部件“进样泵、色谱柱、检测器”，连接“进样泵→色谱柱→检测器”。示例输出（示意）：`status="success"`，`process_flow.steps` 按编号排列，`consistency_checks=[]`。仅为示例，不代表官方固定案例结果。


## 交付保证与评分对齐

调用顺序（固定）：

1. 先运行包内脚本（若存在）：`python scripts/run_skill.py`（默认读 `/input/case.json`，写 `/app/output/result.json`）；路径不同时用 `--case` / `--output` 指定。
2. 再完成脚本无法自动完成的实质工作（译文、论述、图表、修订、结论等），把结果写回 `result.json` 对应字段。
3. 最后自检：`case_id` 与输入一致；`output_contract` 每个字段都存在；`status` 按契约取 `success`/`partial`/`insufficient_input`/`failed`（缺输入或证据不足时用 `insufficient_input`/`partial`）；无 `pending` 占位；数字、引用、来源可逐条回溯。

运行保证：

- 输入缺失、JSON 损坏、字段异常、输出目录不存在时，仍须写出结构化 `result.json` 并正常结束，不得崩溃或非零退出。
- 不联网、不伪造数据、不声称平台评分或官方案例结果。
- 交付物必须是可直接编辑与复核的成品，而不是流程说明。

评分对齐（本题五个维度）：

- 实际效果（40）：完整产出任务要求的最终成品，覆盖全部输入条目，可直接进入修改流程。
- 使用增益（25）：体现相对基础 Agent 的可验证改进（结构化、术语/数字/引用核对、可编辑性）。
- 创新增益（15）：保留方法学增量（分块、对齐、二次校验、版本比对等），并用结果证明其价值。
- 可靠体验（10）：异常输入有明确降级与说明，不同长度/文体/重复运行下稳定产出。
- 生态贡献（10）：用途、调用、输入输出、限制、示例、维护信息齐全，资源可被他人复用。

### 真实图稿与预览（本次必做）

- 脚本只输出规格（如 `editable_source.produced=false`）时，调用 Agent 必须依据规格真实写出可编辑 SVG 到 `/app/output/`：部件、管路/边、箭头、标签、图例均为可编辑元素。
- 任务要求 PNG/PDF 或需要人工核看时，必须实际渲染预览文件；环境无栅格化工具时以真实 SVG 作为矢量预览，并在 `result.json` 写明格式、路径与原因。
- 仅当文件真实落盘、可打开并核对后，才将 `editable_source.produced` 与 `export_plan[].performed` 置 `true`，并写入路径、字节数与 SHA-256；未执行的检查项如实写 `false` 与原因，不伪造渲染或检查结果。

## 最终交付强制要求

1. **调用 Agent 必须交付成品，不是流程说明**：脚本产出只是索引、核对或规格骨架；调用 Agent 必须在同一 `result.json` 中补齐本题要求的最终产物（正文/译文/审稿意见/综述/分析结论/图表源文件与导出件/幻灯片页内容与讲稿/实验方案等）。交付字段为空、只有标题骨架，或含 `pending`、`TODO` 之类占位，一律视为未完成。
2. **必须覆盖全部输入条目**：输入中的每个章节、问题、文献、图、页面、指标都要有对应条目，不得只处理示例或首条；确实缺失的条目写入 `uncertainty` / `limitations` 并说明原因，不得静默跳过。
3. **必须自检后再交付**：`case_id` 与输入一致；`output_contract` 每个字段都存在；状态值取本题契约规定的枚举；数字、单位、引用、来源可逐条回溯；结果内部无自相矛盾。
4. **参数等价**：`python scripts/run_skill.py --case <输入> --out <输出>` 与 `--output <输出>` 等价；默认 `/input/case.json` → `/app/output/result.json`。
5. **平台用 3 个固定案例分别运行**：逻辑要由输入驱动，不针对某一份示例硬编码；字段命名差异走别名匹配与显式降级，并在 `uncertainty` 记录假设。
