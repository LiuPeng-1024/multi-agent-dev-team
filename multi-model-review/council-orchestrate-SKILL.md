---
name: council-orchestrate
description: >-
  Onklaud 5 完整开发流水线编排。串接五层：认知守护(immune_memory+ADR注入)→
  认知多样(双模型审+仲裁)→执行守护(guard-check真测试)→学习守护(失败回喂)→
  流程守护(阶段门禁)。把 LLM 当不可信执行器，让"演"变成"必须真做"。
  06 审查者做完整轮审查时用本 skill 而非 council-review。
  不要用于单步审查（→ council-review）；不要用于单 PR 风险评估（→ gitnexus-pr-review）。
---

# council-orchestrate — Onklaud 5 完整流水线

## 何时用本 skill

- **用**：需要跑完整 Onklaud 5 流水线——从设计到验收全闭环时
- **用**：06 审查者要做"审→修→再审→门禁"完整轮次时
- **不用**：只想要单步双模型审查（→ `council-review`）
- **不用**：单 PR 风险评估（→ `gitnexus-pr-review`）

## ★角色执行分工（铁律——避免 06 工具墙矛盾）

06 审查者工具授权是 Read/Grep/Glob（无 Bash），**跑不了 `from review_engine import` 这种 Python 代码**。各层执行分工：

| 层 | 谁跑 | 怎么跑 | 06 做什么 |
|----|------|--------|---------|
| ① 认知守护 | 06 自己 | Read 读 immune_memory.json + ADR | ✅ 06 能做 |
| ② 双模型审+仲裁 | **02 路由给 05/04 代跑** | 05/04 用 Bash 跑 `python -c "from review_engine import council_review; ..."` | 06 只读产出的报告做静态核对 |
| ③ 执行守护 | **05 测试工程师** | 05 用 Bash 跑 `verify_preset()` / `guard-check --execute` / `cargo test` | 06 不参与（06-reviewer.md L67：动态验证归测试方） |
| ④ 修复闭环 | **02 路由给 05/04 代跑** | 05/04 用 Bash 跑 `python -c "from review_engine import delta_review; ..."` | 06 只读 delta 报告确认 can_release |
| ⑤ 阶段门禁 | 02 汇总 | guard-check.py（05 代跑） | 06 只回写结论到区块4.2 |

**06 的职责边界**：读代码+读 ADR+读 immune_memory+读 review_engine 产出的报告 → 写审查结论文本（含 council 标记 + 报告路径）回区块4.2。**06 不亲自跑任何 Python/Bash 命令。**

**02 编排者的职责**：dispatch 06 时在 task 描述里点名"用 council-orchestrate"，同时把需要代跑的②③④层任务路由给 05/04（有 Bash 的角色），跑完把报告路径回 06 做静态核对。

## Onklaud 5 五层精髓

```
① 认知守护  immune_memory + ADR 前置注入
              ↓ 业务上下文进所有角色的 prompt
② 认知多样  双模型独立审 + 分歧仲裁
              ↓ 异架构补盲点，冲突是故意的
③ 执行守护  guard-check --execute + cargo test + vite build
              ↓ 完全不靠 LLM，二进制可执行是诚实的
④ 学习守护  修后→再审→还失败→带上一轮缺陷回喂
              ↓ 单调下降，不在同一坑反复栽
⑤ 流程守护  阶段 0 freeze → 阶段 1 写 → 阶段 2 验收
              ↓ 每阶段有进退条件，不满足不准进下一阶段
```

## 与 council-review 的关系

`council-review` 是本 skill 的**第 ② 层**——只做双模型审 + 仲裁。
本 skill 在它之上加 4 层：业务注入、真测试、回喂迭代、阶段门禁。

```
council-orchestrate (上层，串 5 层)
    ├── 调 council-review 做第②层
    ├── 调 guard-check 做第③层
    ├── 自己管第①④⑤层
    └── 借力 multi-agent-dev-team 的角色定义
```

## 完整一轮流水线

```
[阶段 0: 规格化]
    │
    ▼ freeze（PRD + INTERACTION_SPEC + ADR 锁定）
[阶段 1: 开发]
    │
    ├── ① 注入 immune_memory + ADR 到开发者 prompt
    ├── 开发者写代码
    ├── ①verify 完成声明验证——真跑 cargo test / npm test / pytest
    │      └── 测试不过=没完成，打回（不信模型说"完成"）
    ├── ② council-review 双模型审
    │      └── 分歧大 → Qwen 仲裁
    ├── ③ guard-check --execute + cargo test + vite build
    │      └── 挂了 → ④ 失败回喂
    ├── ④ delta_review 修复闭环——带上一轮缺陷重审
    │      └── 确认旧缺陷消失 + 无新引入；不过→再修→再 delta（最多 2 轮）
    └── 全绿 → 进入阶段 2
[阶段 2: 验收]
    │
    ├── ② 最终轮 council-review（带累积 immune_memory）
    ├── ③ 最终 guard-check + 全量测试
    └── 人 gate 放行
```

## 三层防幻觉闭环（核心机制）

### 第①层：完成声明验证（防"说完成≠真完成"）

**04 开发者说"完成"时，自动真跑测试。测试不过=没完成=打回。**

```python
from review_engine import verify_completion, verify_preset

# 预设命令（rust/node/python/tauri）
result = verify_preset("project_root", "rust")
# 或自定义命令
result = verify_completion(
    project_root=".",
    test_cmd="npm test",
    build_cmd="npx vite build",
)
# result.passed = True 才能进入审查
```

### 第②层：双模型审查（防盲点）

直接调 `council-review` skill 或 `review_engine.council_review()`。

**角色冲突是故意的**：代码审查者（Kimi）找 bug，架构审查者（DeepSeek）找架构问题，仲裁者（Qwen）综合裁决。

### 第③层：修复闭环（防"修了引入新缺陷 + 修了破坏业务需求"）

**04 修完后，不是从零重审，是带着上一轮 defect list + 业务验收标准做 delta 审。**
确认三件事：①旧缺陷消失 ②没引入新缺陷 ③业务验收标准仍然满足。

```python
from review_engine import delta_review, load_memory

# 从 PROJECT_CONTEXT §3 提取业务验收标准（★关键，不能省）
acceptance = """
- <从你的 PROJECT_CONTEXT §3 抄录业务验收标准>
- 例：折扣商品不参与满减叠加（业务规则，不是 bug）
- 例：同输入两次调用核心排序函数输出完全一致（幂等）
"""

result = delta_review(
    code=fixed_code,
    file_path="src/foo.rs",
    previous_defects=council_result["merged_defects"],
    context="ADR-002 ...",
    immune_memory=load_memory("<你的项目名>"),
    acceptance_criteria=acceptance,  # ★修复后必须仍然满足这些
    model="kimi-k2.7-code",
)
# result.can_release = True 才能放行
# verdict: all_fixed | partially_fixed | new_defects_introduced | business_regression
```

**判定规则**：
- `all_fixed` = 旧缺陷全修 + 无新缺陷 + 业务验收标准全满足 → 放行
- `partially_fixed` = 部分还在（无新缺陷，业务未回归）→ 继续修残留
- `new_defects_introduced` = 引入新缺陷 → 必须修新缺陷 + 继续修残留
- `business_regression` = **业务验收标准不再满足** → 🔴 最高优先级，回滚或重新设计修复方案
- 最多 2 轮 delta，超过则升级到人 review

## 第 ① 层：认知守护（业务注入）

**目的**：让模型知道"什么不是 bug"，避免把业务需求误判为缺陷。

```python
# 读全局免疫记忆 + 项目 ADR
immune = open("~/.zcode/llm_tools/immune_memory.md").read()
adr = open("PROJECT_CONTEXT.md").read()  # 区块 5 ADR 部分

# 注入到 council_review
council_review(
    code=...,
    context=adr,
    immune_memory=immune,  # ← 前置注入到 prompt 头部
)
```

**铁律**：审查者每轮发现"模型误判为 bug 但实际是业务需求"的项 → 追加到 `immune_memory.md` 对应分类。**不删已确认项**——它们是历史教训。

## 第 ② 层：认知多样（双模型审 + 仲裁）

直接调 `council-review` skill 或 `review_engine.council_review()`。详见 council-review SKILL.md。

**角色冲突是故意的**：
- 代码审查者（Kimi）拿"找 bug"目标函数
- 架构审查者（DeepSeek）拿"找架构问题"目标函数
- 仲裁者（Qwen）拿两份报告 + ADR 做终审
- **三者不会合谋**——因为目标函数不同

## 第 ③ 层：执行守护（离线门禁）

**模型说"通过"=噪声；`cargo test` 跑过=信号。**

```bash
# Rust 项目
cd src-tauri && cargo check && cargo test

# 前端项目
npx vite build && npm run lint

# 多智能体项目
python references/scripts/guard-check.py --execute
```

**这一层完全不依赖 LLM**——是 Onklaud 5 区别于所有"AI 审 AI"方案的地方。两份审查报告都说 8.5/10，guard-check 跑挂，照样打回。

## 第 ④ 层：学习守护（失败回喂）

```
审查发现缺陷 #1 #2 #3
    │
    ▼
开发者修 #1 #3（#2 确认为业务需求关闭）
    │
    ▼
带上一轮 defect list 重审（delta 审，不是从零重审）
    │
    ├── #1 #3 确认修复且无新缺陷 → 通过
    └── 还有缺陷或引入新缺陷 → 再回喂（最多 2 轮）
```

**关键**：不是从零重审，是带着上一轮 defect list 做 delta 审——确认旧缺陷消失、检查没引入新缺陷。

## 第 ⑤ 层：流程守护（阶段门禁）

| 阶段 | 进入条件 | 退出条件 |
|------|---------|---------|
| 0 规格化 | PRD 草案 | freeze（PRD + INTERACTION_SPEC + ADR 锁定） |
| 1 开发 | freeze 完成 | council-review 通过 + guard-check 全绿 + 失败回喂收敛 |
| 2 验收 | 阶段 1 退出 | 最终轮审查 + 全量测试 + 人 gate 放行 |

**编排者只做调度，不替任何角色干活。** 每阶段不满足退出条件不准进下一阶段。

## 借力的已有 skill

| 场景 | skill | 用途 |
|------|-------|------|
| 双模型审查（第②层） | `council-review` | 异架构独立审 + 仲裁 |
| 审查标准 | `requesting-code-review` | 单模型 review 标准 |
| 放行前验证（第③层） | `verification-before-completion` | 确认真跑了测试 |
| 完整多智能体框架 | `multi-agent-dev-team` | 9 角色协作 + guard-check 脚本 |
| 系统化调试（第④层） | `systematic-debugging` | 失败回喂时的根因分析 |

## 铁律

1. **模型说"通过"不算数**——第 ③ 层 guard-check 真跑过才算
2. **未标注 business_check 的 blocker/critical 禁止改代码**
3. **修后必须回喂重审**——不做 delta 审等于没修
4. **修复不能破坏业务需求**——delta_review 必须带 acceptance_criteria，business_regression = 🔴 必须回滚
5. **immune_memory 只增不删**——历史教训防止重蹈
6. **编排者不替角色干活**——只调度，不写代码/不审查/不测试
