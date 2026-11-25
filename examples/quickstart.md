# 快速上手

本 Skill 在 DeepSeek Harness 中被加载为 `/skills/bohr-graphics`。
Harness 在每个案例上执行（单次运行即产出完整交付，`status=answered`）：

```bash
python /skills/bohr-graphics/scripts/sk_entry.py \
  --input /input --work /app/work --out /app/output
```

## 可选覆盖（两阶段）

默认单次运行就完成取证、成图与判断；仅当需要人工改写判断时才走下面这条覆盖路径：

```bash
# 阶段 A：取证 + 产出任务单
python /skills/bohr-graphics/scripts/sk_entry.py \
  --input /input --work /app/work --out /app/output
cat /app/work/agent_tasks.json

# 阶段 B：执行 Agent 照任务单写判断（模板见 examples/demo-case/agent_judgement.example.json）
#   → /app/work/agent_judgement.json

# 阶段 C：脚本校验引文并合并
python /skills/bohr-graphics/scripts/sk_entry.py \
  --input /input --work /app/work --out /app/output
```

## 手动复现

```bash
cd /skills/bohr-graphics
python scripts/sk_entry.py --input examples/demo-case --work /tmp/work --out /tmp/out
cat /tmp/out/result.json
cat /tmp/work/agent_tasks.json
```

## 产出

- `/app/output/result.json` —— 契约字段齐全的结果
- `/app/output/run-review.md` —— 证据索引 + 不确定性清单
- `/app/work/agent_tasks.json` —— 给执行 Agent 的任务单（阶段 A 产出）
- `/app/work/agent_judgement.json` —— 执行 Agent 的判断（阶段 B 产出，脚本读）

## 自检

```bash
python scripts/sk_selftest.py --input examples/demo-case
```
