# multi-agent-dev-team

**用专业化、可协作的多智能体团队开发软件——单模型约束下，用结构保质量。**

> Assign specialized roles to LLMs, orchestrate them with source-of-truth documents and adversarial goals, and verify everything with machine-checkable gates — not with model claims.

[English summary at the bottom](#english-summary)

---

## 这是什么

一套跑在编码智能体（Claude Code / ZCode / Kimi CLI 等支持 skill 的 harness）之上的**多智能体开发团队框架**：9 个角色 + 双层循环 + 事实来源文档 + 可执行门禁 + 多模型审查。

它回答的核心问题：**当所有角色共用同一个模型时，软件质量从哪里来？**

答案是结构，不是模型能力：

1. **目标函数不同** —— 开发者=完成，测试=让它失败，审查=找缺陷，红队=攻破，调试=找根因不盲改。同一模型，目标对立，行为就分化。
2. **工具授权不同** —— 审查者只读（Read/Grep/Glob，不给 Bash）；结构性只读 > 策略承诺。
3. **上下文范围不同** —— 每个角色只拿自己需要的区块，不共享全量上下文。
4. **行为指令不同** —— 角色文档（`references/roles/`）定义各自的工作方式。

> 这四条是单模型下质量保证的全部来源。少一条，质量塌一截。

## 核心机制一览

| 机制 | 内容 | 文档 |
|------|------|------|
| **事实来源文档** | `PROJECT_CONTEXT.md` 区块 0-13：需求/ADR/验收标准/验证规则/幻觉日志…所有角色先读后写 | `references/project-context-template.md` |
| **规格化阶段** | 0.0a 问题空间 → 0.0b 早期人 gate → 0.0c PRD+交互规约 → 0.0d 多角色评审 → 0.0e 人 gate → 0.0f freeze，freeze 才准开工 | `references/collaboration-flow.md` |
| **双层循环** | 外层：需求→设计→开发→测试→审查→交付；内层：dev→test→review 小步快跑 | 同上 |
| **三基石安全系统** | 防幻觉（claim→verify）、防失控（步数/时长/预算限制）、异常处理+任务画像（P1-P4 分级限参） | `references/anti-hallucination.md` / `guardrails.md` / `exception-handling.md` |
| **可执行门禁** | `guard-check.py`：区块级检查 1-9，`--execute` 模式用真实退出码/文件存在性裁决，**不信模型声称** | `references/scripts/guard-check.py` |
| **退出门禁 5 条** | 测试全绿且本轮新鲜复现 / 多模型审查通过 / 完成声明有非作者复现证据 / 回归全绿 / 无未解决高优问题 | `references/collaboration-flow.md` |
| **保证度三因子** | 完备性 × 不可绕过 × 网自验（乘法模型）——直接指出该补哪个短板 | `SKILL.md` §可靠性度量 |
| **多模型审查层** | 双模型异架构独立审 → 分歧仲裁 → 免疫记忆注入 → delta 回喂（Onklaud 5 五层，见 `multi-model-review/`） | `multi-model-review/README.md` |

## 快速开始

1. 把本仓库放到你的 skills 目录（以支持 skill 的 harness 为例）：

```bash
git clone https://github.com/<you>/multi-agent-dev-team ~/.agents/skills/multi-agent-dev-team
```

2. 对你的项目说：

```
用 multi-agent-dev-team 开发 <需求>
```

编排者会先读框架 `SKILL.md`，再引导你走规格化阶段（0.0a-f），产出 `PROJECT_CONTEXT.md`（照 `references/project-context-template.md` 填），然后进入双层循环。

3. （可选）配置多模型审查层，见 [`multi-model-review/README.md`](multi-model-review/README.md)。

## 目录结构

```
SKILL.md                        # 框架入口：核心原则/角色表/铁律/保证度
references/
  ARCHITECTURE.md               # 架构总览与设计哲学
  collaboration-flow.md         # 规格化阶段 + 双层循环 + 退出门禁
  guardrails.md                 # 防失控：步数/时长/预算/升级路径
  exception-handling.md         # 任务画像 P1-P4 + 异常处理总表
  anti-hallucination.md         # 防幻觉：claim→verify + 幻觉日志
  cross-verification.md         # 非作者复现 + 交叉核对强度
  change-impact-analysis.md     # 改前评估 + 改后查逻辑错误
  isolation-protocol.md         # worktree/分支隔离协议
  agency-inject-design.md       # 专家注入的风险设计（注入前必读）
  prd-template.md               # PRD 模板
  interaction-spec-template.md  # 交互规约模板
  project-context-template.md   # PROJECT_CONTEXT 区块 0-13 模板（事实来源）
  roles/                        # 9+1 角色文档（目标函数+工具授权+行为指令）
  scripts/guard-check.py        # 可执行门禁（--execute 真跑验证规则）
multi-model-review/             # 多模型审查子系统（可选但强烈推荐）
  council-review-SKILL.md       # 双模型审+仲裁引擎
  council-orchestrate-SKILL.md  # Onklaud 5 五层流水线
  review_engine/                # Python 实现（client/config/merge/delta/memory/...）
  examples/                     # llm_proxy / immune_memory 示例配置
ROADMAP.md                      # 已知缺口与演进方向（欢迎认领）
```

> **注**：`references/skills/`（专家注入包：UI/设计/安全专家快照等）**不随本仓库分发**——它们是第三方许可内容。框架文档中对 `ui-ux-pro-max` 等的引用描述的是集成方式，你可以用自己的专家包按同样方式接入（机制见 `references/agency-inject-design.md` 与 `references/roles/10-design.md`）。

## 与同类项目的关系

- **MetaGPT**（`Code = SOP(Team)`）：思想同源——用结构化流程约束多智能体。MetaGPT 把 SOP 编译进代码管线；本框架把 SOP 编译进**文档与门禁**，harness 无关、模型无关，可直接骑在任意编码智能体上。
- **MCP / A2A**：MCP 解决"模型↔工具"，A2A 解决"模型↔模型"的传输与发现。本框架当前是进程内/会话内协作；协议化（能力发现、跨进程传输、认知预算）见 [ROADMAP](ROADMAP.md)。

## 没发布什么（以及为什么）

- **真实项目的 `PROJECT_CONTEXT.md` 实例**（含幻觉日志与业务验收标准）——商业内容。模板 + 区块注释足以复刻填写过程，欢迎 PR 脱敏范例。
- **LLM 代理端点与密钥引用**——`review_engine` 的所有端点/密钥均改为环境变量或本地配置，仓库不含任何真实端点。
- **第三方专家注入包**——许可不明，不代分发。

## 参与贡献

- 用框架做了真实项目？欢迎 PR 脱敏后的 `examples/` 实战范例。
- 发现门禁漏洞（能绕过 guard-check 的路径）？开 Issue，这是本项目最重视的缺陷类型。
- 演进方向见 [ROADMAP.md](ROADMAP.md)。

## License

[MIT](LICENSE)

---

## English Summary

**multi-agent-dev-team** is a framework for running a specialized, collaborative AI dev team (9 roles, dual-loop workflow, source-of-truth docs, executable gates, multi-model review) on top of any skill-capable coding agent. Its core thesis: under a single-model constraint, quality comes from **structure** — opposing objective functions, split tool authorization, scoped context, and role-specific behavior — not from model capability. All "done" claims must survive machine-checkable gates (`guard-check.py --execute`, real exit codes) and multi-model adversarial review; model assertions alone are never trusted. See `SKILL.md` for the full mechanism set and `ROADMAP.md` for where this is heading (capability discovery, inter-agent protocol layers, cognitive budgets).
