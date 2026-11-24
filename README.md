# 实验装置与技术路线图

本题：实验装置与技术路线图（challenge-9034312d，赛道 graphics）。

能力定位：把科研内容转成可执行的图形制作规格（图型、元素清单、坐标轴与单位、数据点、图例、配色），并给出真实渲染的 PNG 预览供复核

交付物：result.json（契约齐全）、图形规格、渲染预览 PNG


## 这个 Skill 做什么

一条流水线，四段职责，全程可回溯到材料原文：

| 阶段 | 谁做 | 产物 |
|---|---|---|
| 1 取证 | `scripts/sk_entry.py` + `scripts/sk_base.py` | 材料 → 段落 id → 证据锚点 |
| 2 判断 | 执行 Agent（读 `agent_tasks.json`） | `agent_judgement.json`（领域判断） |
| 3 校验合并 | `scripts/topic.py` | 引文逐字核对，退回编造的条目 |
| 4 出品 | 赛道专用引擎 | **真实文件**（不是规格描述） |

## 真实交付物

| 文件 | 作用 |
|---|---|
| `result.json` | 契约齐全的结构化结果与元素清单 |
| `figure.svg` | **真实可编辑矢量源**：分层节点，每个节点带 `data-source-paragraph` / `data-quote` 属性 |
| `figure.png` | 由 `figure.svg` **真实渲染**的预览图 |
| `figure-provenance.json` | 元素 → 原文段落的映射与修改记录 |
| `figure.pdf` | 由 `figure.svg` 导出的 PDF（矢量优先；本机无矢量转换器时如实标注为位图兜底） |
| `figure-export-checks.json` | **导出前合规检查**：目标格式、画布尺寸、实测分辨率、字体嵌入与回退、色彩空间、线宽、分层、数据一致性、人工确认清单 |


`result.json` 里的 `editable_source` / `exports` / `provenance_and_changes`
三组键**指向磁盘上真实存在的文件**，每条记录都带 `sha256` 与字节数，
评审可以直接打开文件核对。

## 目录

```
SKILL.md                     Skill 定义（frontmatter: name / description）
environment/resources.yaml   资源入口（评测方读这个文件定位脚本与依赖）
scripts/sk_entry.py          入口脚本（发现输入 → 执行 → 装配 → 自检）
scripts/sk_base.py           公共库（契约解析、证据构造、结果装配）
scripts/topic.py             题目逻辑（契约自适应 + 赛道分流）
scripts/artifacts.py         graphics 引擎：实体—连接—步骤 IR → 分层 SVG → 渲染 PNG
scripts/pptxgen.py           slides 引擎：stdlib-only 真实 PPTX + 逐页 SVG/PNG
scripts/specialize.py        reading/writing 引擎：逐字段抽取 / 可编辑稿件 + 改动记录
scripts/sk_selftest.py       独立自检
assets/result-schema.md      result.json 字段说明
assets/policy.json           不编造承诺
references/                  证据纪律 / 契约处理 / 失败模式 / 产物流水线
examples/demo-case/          可离线复现的最小案例
```

## 离线复现

```bash
# 阶段 A：取证 + 出任务单
python scripts/sk_entry.py --input examples/demo-case --work /tmp/w --out /tmp/o
cat /tmp/w/agent_tasks.json

# 阶段 B：照任务单写判断（模板见 examples/demo-case/agent_judgement.example.json）
#   → /tmp/w/agent_judgement.json

# 阶段 C：校验引文并合并进 result.json
python scripts/sk_entry.py --input examples/demo-case --work /tmp/w --out /tmp/o
ls -l /tmp/o
```

## 自检

```bash
python scripts/sk_selftest.py --input examples/demo-case
```

自检覆盖：契约键是否全部非空、每条 claim 是否带 `paragraph_id` + 原文 `quote`、
引文是否能在材料里逐字找回、是否残留 `__pycache__`。

## 环境要求

- Python >= 3.10
- **仅标准库**，无需 `pip install`
- 无网络访问
- 渲染预览优先用环境里已有的渲染器（ImageMagick / CairoSVG / Pillow），
  都没有时回退到纯 Python 光栅化，SVG 源文件始终交付

## 复用

`scripts/` 下的五个模块可以单独 import 使用，与 Harbor 运行时解耦：

```python
import sys; sys.path.insert(0, "scripts")
import sk_base, topic, specialize, artifacts, pptxgen
```

- `sk_base.make_evidence()` —— 构造带段落定位与原文短引的证据条目
- `sk_base.assemble_result()` —— 按契约装配 `result.json`
- `specialize.extract_target_fields()` —— 逐 `field_id` 抽取并给出四态状态
- `artifacts.extract_structure()` / `build_svg()` —— 从材料抽出结构并生成分层 SVG
- `pptxgen.build_pages()` / `write_slides_artifacts()` —— 生成真实 PPTX 与逐页预览

## 提交

```bash
playground submit --challenge-id challenge-9034312d --outputs . --trace trace.jsonl
```

## 许可证

MIT（见 `LICENSE`）。
