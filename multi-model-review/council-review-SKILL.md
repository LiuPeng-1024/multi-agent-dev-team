---
name: council-review
description: >-
  多模型流水线代码审查引擎。调用 Kimi/DeepSeek/Qwen 等异架构模型对同一份代码做独立审查→
  合并缺陷→分歧大则仲裁→归档报告。**只覆盖 Onklaud 5 的"认知多样层"（审查+仲裁）**，
  不包含业务上下文注入/离线门禁/失败回喂/阶段门禁——这些由上层 council-orchestrate 串接。
  06 审查者专用。也适用于开发者自检、重构评估、安全审计场景。
  不要用于单模型 review（那用 requesting-code-review）；不要用于 PR 级审查（那用 gitnexus-pr-review）。
---

# council-review — 多模型审查引擎

## 何时用本 skill

- **用**：需要多个不同架构模型独立审同一份代码、互相补盲点时
- **不用**：只想要单模型快速过一遍代码（→ `requesting-code-review`）
- **不用**：PR 级风险评估（→ `gitnexus-pr-review`）
- **不用**：需要完整 Onklaud 5 流水线（预设计→写→审→门禁→回喂）时（→ `council-orchestrate`）

## 定位（Onklaud 5 五层中的哪一层）

| Onklaud 5 层 | 职责 | 本 skill 是否覆盖 |
|-------------|------|------------------|
| 1. 认知守护（immune memory + ADR 注入） | 业务上下文前置 | ⚠️ 接 `immune_memory` 参数，但不负责维护 |
| 2. 认知多样（双模型审 + 仲裁） | 异架构补盲点 | ✅ **本 skill 核心** |
| 3. 执行守护（guard-check 真测试） | 离线确定性验证 | ❌ 由调用方接 `cargo test`/`vite build` |
| 4. 学习守护（失败回喂） | 修后再审 | ❌ 由调用方迭代 |
| 5. 流程守护（阶段门禁） | freeze/进退条件 | ❌ 由上层 orchestrate 管 |

**本 skill 只是 5 的一个零件**，不是 5 本身。要跑完整 Onklaud 5 流程用 `council-orchestrate`。

## 核心流程

```
代码 + 上下文(ADR/immune_memory)
    │
    ▼
┌─────────────────────────────┐
│ 模型 A 独立审（如 Kimi）     │  ← 代码审查者：逐行找 bug
└─────────────────────────────┘
    │
    ▼ （并行）
┌─────────────────────────────┐
│ 模型 B 独立审（如 DeepSeek） │  ← 架构审查者：错误传播/并发
└─────────────────────────────┘
    │
    ▼
合并缺陷（按 severity+category+issue 去重，追踪来源）
    │
    ├── 分歧 < 阈值 → 直接归档
    └── 分歧 ≥ 阈值 → Qwen 仲裁 → 归档
```

## 模型角色定义

| 角色 | 推荐模型 | 擅长 | prompt 重心 |
|------|---------|------|-----------|
| 代码审查者 | `kimi-k2.7-code` | 代码逻辑、边界、类型安全、panic 路径 | 逐行审、找 bug |
| 架构审查者 | `deepseek-v4-pro` | 错误传播、并发安全、API 设计 | 系统性、设计层面 |
| 仲裁者 | `qwen3.8-max` | 长上下文全局审视、跨模块一致性 | 综合两份报告做裁决 |

> 角色定义是 Onklaud 5 精髓之一：**不同模型拿不同目标函数**，冲突是故意的——审查者不会因为开发者说"做完了"就放过。

## 调用方式

### Python（推荐）

```python
import sys
sys.path.insert(0, "~/.zcode/llm_tools")  # 或设 PYTHONPATH
from review_engine import council_review

report = council_review(
    code=open("src/foo.rs").read(),
    file_path="src/foo.rs",
    code_type="rust",           # rust | react | architecture
    models=("kimi-k2.7-code", "deepseek-v4-pro"),
    context="ADR-002: 有效成分性价比替代 composite; ADR-003: 锚点夹逼",
    immune_memory=open("~/.zcode/llm_tools/immune_memory.md").read(),
    output_dir="reports/",
)
print(report["merged_defects"])
```

### Agent 直接调用（06 审查者）

```
用 review_engine 包审查 src-tauri/src/scene_scorer.rs
- code_type: rust
- models: kimi-k2.7-code + deepseek-v4-pro
- context: 读 PROJECT_CONTEXT 区块5 ADR-001~004
- immune_memory: 读 ~/.zcode/llm_tools/immune_memory.md
- output_dir: src-tauri/reviews/
```

## 业务需求闸门 ★铁律

**模型审出的"非缺陷"比缺陷更危险。** 改任何 blocker/critical 缺陷前必须验证：

```
模型报告缺陷
    │
    ▼
[查 PROJECT_CONTEXT 区块 3] 这个行为是需求要求的吗？
[查 ADR 区块 5] 这里有 ADR 决策吗？
[查 immune_memory] 这个已在"已确认非 bug 清单"里吗？
    │
    ├── 是业务需求 → STOP。标 business_check=confirmed_requirement，关闭
    └── 不是 → 继续改，标 business_check=confirmed_bug
```

**未标注 business_check 的 blocker/critical 缺陷，禁止直接修改代码。**

## 配置说明

- 代理地址 + key：`~/.zcode/llm_proxy.yaml`（全局共享，项目无需配置）
- key 引用：`~/.llm_proxy_keys.json` → `glm.api_key`
- 免疫记忆：`~/.zcode/llm_tools/immune_memory.md`（跨项目共享）
- 审查引擎包：`~/.zcode/llm_tools/review_engine/`

**改 key 只改 `~/.llm_proxy_keys.json` 一处，所有项目/智能体全生效。**

## 输出

每轮审查产出一份 markdown 报告，含：
- 各模型评分 + 评价 + 缺陷列表
- 合并缺陷（按 severity 排序，带 business_check + 来源追踪）
- 仲裁结果（如有）
- 业务需求验证待办清单（pending 的 blocker/critical）

报告路径：`{output_dir}/{timestamp}_{filename}_council.md`

## 借力的已有 skill

| 场景 | skill | 用途 |
|------|-------|------|
| 审查标准与流程 | `requesting-code-review` | 单模型 review 的标准方法 |
| PR 级风险 | `gitnexus-pr-review` | PR 级风险评估 |
| 放行前验证 | `verification-before-completion` | 确认真跑了测试 |
| 完整 Onklaud 5 流水线 | `council-orchestrate` | 串接预设计→审→门禁→回喂 |
