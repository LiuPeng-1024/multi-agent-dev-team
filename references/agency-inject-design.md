# Agency-Agents 注入设计

> 将 `msitarzewski/agency-agents`（230+ 专业 Agent Prompt 库）的精选 agent 作为"增强知识层"注入 `multi-agent-dev-team` 框架的 10 个角色中。
>
> 本文是设计文档，不是实施计划。实施计划在写代码前由 writing-plans skill 生成。

---

## 1. 背景与目标

### 1.1 为何注入

两个系统定位不同、能力互补：

| | agency-agents | multi-agent-dev-team |
|---|---|---|
| 定位 | Agent 角色配置文件集（Prompt 库） | 多智能体协作框架+运行时 |
| 强项 | 单 agent 深度：230+ 专家，含具体代码示例 | 多角色编排：信息隔离/交叉验证/门禁/安全系统 |
| 弱项 | 无编排/无验证/无门禁 | 单角色知识密度不足，领域覆盖窄 |

注入的目标不是替代框架的 10 个角色，而是**把 agency-agents 的专家知识密度"灌入"框架角色的技术交付物中**，框架负责编排和验证，agency-agents 提供"怎么做"的具体模式。

### 1.2 第一性原理

"稳定可靠交付产品"的必要条件：

| # | 条件 | 框架覆盖 | agency-agents 贡献 |
|---|---|---|---|
| A | 做正确的事 | ✅ 规格化+人gate | — |
| B | 正确地做事 | ✅ 双层循环+对抗验证 | 提供领域级"怎么做"的具体代码模式 |
| C | 知道做完了 | ✅ 5门禁+保证度 | — |
| D | 不出意外地失败 | ✅ 三基石安全系统 | — |
| E | 能持续演进 | ✅ 变更影响分析+回归 | — |

A/C/D/E 完全由框架覆盖，不需要注入。**注入只服务 B（正确地做事）**，给执行型角色（开发者/测试/审查/架构/红队/设计师）补充领域专业知识。

---

## 2. 注入映射表（6 角色 × 16 agent）

### 角色 01 需求分析师 — 不注入
理由：核心工作是"问题空间→早期人gate→freeze"，这个流程是框架特有的。

### 角色 02 编排者 — 不注入
理由：4问决策树+任务分解+脱敏路由是框架独有调度能力。

### 角色 03 架构师 — 3 agent

| agent | 注入内容 | 最大价值 |
|-------|---------|---------|
| Software Architect | 系统设计 pattern、DDD、trade-off 分析 | 架构师缺具体的 trade-off 分析框架 |
| Multi-Agent Systems Architect | 多智能体拓扑/信任/故障恢复模式 | 框架本身就是多智能体，架构师需要 |
| Security Architect | 威胁建模、信任边界、防御纵深 | 现有"安全架构"较泛，缺具体方法论 |

### 角色 04 开发者 — 6 agent（核心注入点）

| agent | 注入内容 | 最大价值 |
|-------|---------|---------|
| Frontend Developer | 组件模式、CWV、检查清单 | 现有缺具体检查清单 |
| Backend Architect | API 设计 pattern、微服务模式 | 现有只有原则缺 pattern |
| Database Optimizer | 查询优化、索引策略、迁移规划 | 开发者常写 SQL，缺实际模式 |
| API Platform Engineer | API 网关/版本/限流 | 现有后端内化没覆盖 |
| Code Reviewer（仅清单格式） | 🔴/🟡/💭 分级审查 | 开发者自测可用此评审代码 |
| Test Automation Engineer（仅 fixture） | Playwright 无 sleep 原则 + 确定性测试模式 | 写 E2E 时需代码级参考 |

### 角色 05 测试工程师 — 3 agent

| agent | 注入内容 | 最大价值 |
|-------|---------|---------|
| Test Automation Engineer | Playwright fixture、selctor 策略、flake 消除、CI 并行化 | 现有只有方法论，缺工具级代码 |
| Performance Benchmarker | k6 配置、性能基准、Core Web Vitals | 现有"性能测试"要求缺具体工具 |
| API Tester | API 验证、cURL 模式、集成测试 | 缺少 API 层具体模式 |

### 角色 06 审查者 — 2 agent

| agent | 注入内容 | 最大价值 |
|-------|---------|---------|
| Code Reviewer（仅评语格式） | 🔴/🟡/💭 三级清单 + 评语模板 | 审查清单是"方向性"的，缺具体模板 |
| Reality Checker（仅判定标准） | "默认 NEEDS WORK" + evidence-based certification | 审查者缺最后防线放行标准 |

### 角色 07 知识管理者 — 不注入
理由：文档维护+版本化，agency-agents 无对应角色。

### 角色 08 红队 — 2 agent

| agent | 注入内容 | 最大价值 |
|-------|---------|---------|
| Penetration Tester | 渗透测试方法论、工具链、漏洞利用技术 | 现有攻击场景库较泛 |
| AppSec Engineer | SAST/DAST、安全编码审查、SDL | 红队需知道开发者在哪引入漏洞 |

### 角色 09 调试专家 — 1 agent

| agent | 注入内容 | 最大价值 |
|-------|---------|---------|
| Codebase Onboarding Engineer | 代码路径追踪、"只陈述事实"的读代码方式 | 调试专家核心是读代码找根因 |

### 角色 10 设计师 — 3 agent

| agent | 注入内容 | 最大价值 |
|-------|---------|---------|
| UX Researcher | 用户测试方法、行为分析、认知走查 | 现有 Research 三层缺具体方法 |
| Visual Storyteller | 品牌叙事、视觉层次、叙事→设计转化 | 缺从故事到设计的转化方法 |
| Whimsy Injector | Purposeful Whimsy + 情感设计分类学 | 设计师缺"情感层设计"维度 |

---

## 3. 注入协议（核心机制）

### 3.1 注入不是粘贴，是提取

从每个 agency-agent 文件中**只提取**：
```
✅ 提取: 📋 Technical Deliverables（技术交付物，含代码示例）
✅ 提取: 🚨 Critical Rules（技术规则，如"无 hard sleep"）
✅ 提取: 📝 Workflow/Methodology（工作流/方法论）
✅ 提取: 📊 Success Metrics（成功指标，作为期望基准，不覆盖门禁）

❌ 丢弃: 🧠 Identity & Memory（人格定义，与框架角色冲突）
❌ 丢弃: You are XXX 身份声明（框架角色身份优先）
❌ 丢弃: 💬 Communication Style（交互风格，框架角色已定义）
❌ 丢弃: Vibe（同样是人格，会稀释框架角色指令）
```

### 3.2 加载规则

```
- 每轮最多加载 1 个 agent（按任务画像选择）
- 加载时机：编排者 dispatch 时在角色 prompt 末尾追加
- 注入前加优先级声明（锚定段），让框架规则始终优先
- Context 预算软指导：注入材料占子代理 task context ≤ 30%（编排者按任务规模裁量）
- 注：优先级安全不靠注实体长短保，靠①提取时丢弃 Identity ②注入段前锚定句 ③工具授权墙。
  见 `injection-protocol.md` §2 > 不再设行数硬限
```

### 3.3 冲突裁决优先级

```
P1（最高）: 框架安全系统层 — 防幻觉/防失控/异常处理
P2: 框架角色 DoD — 完成判定/工具授权/边界
P3: 框架角色行为指令 — 核心思维方式/铁律
P4: 注入材料技术交付物 — 参考最佳实践，可被 P1-P3 覆盖
```

**典型冲突示例及其裁决**：

| 冲突场景 | 裁定 |
|---------|------|
| Reality Checker 说"C+/B- 评分正常"，但框架门禁要求"测试全绿" | 门禁优先，B- 不能过门禁 |
| Code Reviewer 说"🔴/🟡/💭 分级"，框架审查者说"高优缺陷不得降级" | 不得降级优先 |
| Test Automation Engineer 说 10 次重复运行，框架内层循环上限 5 轮 | 上限 5 轮优先 |
| P4 任务的 auto-retry：Test Automation Engineer 建议 retry，但框架 P4"绝不自动重试" | 绝不重试优先 |

---

## 4. 深度风险分析

### 4.1 风险 R1：注入材料稀释框架规则

**机制**：不是"覆盖"，是注意力稀释。模型对 prompt 开头和结尾内容记得更牢，如果注入材料被放末尾，recency bias 会让注入优先级高于框架规则。

**后果**：框架角色出现"身份漂移"——开发者更像"Frontend Developer"而不是"框架开发者"。

**缓解**：
1. **结构层防线（不靠长度）**：注入材料**不含 Identity/You are XXX**——提取时丢弃，框架身份语句不出现，无法与框架角色竞争。注入段前有锚定句声明"框架核心指令优先"。工具授权是硬边界（审查者只读、测试工程师不可改业务代码），注入材料描述"改代码"也执行不了。
2. **Context 预算软指导**：注入材料占子代理 task context ≤ 30%（编排者按任务规模裁量）。只防 task 数据被挤占，**与优先级无关**——优先级安全由结构层保障，不是靠"注实体保持多短"。
3. **A/B 对比验证**：注入前后用同一份有缺陷的 diff 测审查者检出率，确保漏报不增加

### 4.2 风险 R2：注入内容过时（upstream drift）

**机制**：agency-agents 是活跃仓库（最近 push: 2026-07-12），upstream 更新后本地快照可能包含陈旧/错误的技术建议。

**后果**：使用过时的 Playwright API / 安全实践，或者 upstream bug 被继承。

**缓解**：
1. **快照声明**：每个注入文件开头标注来源 URL、快照日期、commit hash
2. **MANIFEST.json**：维护注入文件的版本元数据，设 30 天刷新窗口
3. **定期检查**：每 30 天运行 `gh api repos/msitarzewski/agency-agents/commits/main` 对比

### 4.3 风险 R3：注入后效果无法度量

**机制**：注入前后可能有其他变量（代码复杂度、模型版本）影响质量，无法归因到注入。

**缓解**：
1. **保证度预期假设**：每次注入记录"预期提升哪一维"（如：注入 Test Automation Engineer → 预期提升完备性）
2. **首次审查通过率**：追踪注入前后"第一次提交就通过审查"的比例变化
3. **不度量错误指标**：不度量"发现缺陷数"（可能是代码质量差的信号），只度量"审查通过率"和"门禁通过率"

### 4.4 风险 R4：角色边界模糊

**机制**：开发者注入了 Playwright 知识后可能自证自验，绕过框架的验证分离。

**后果**：框架的"producer≠verifier"铁律被腐蚀。

**缓解**：
1. **知识边界声明**：注入材料开头声明"正式验证/安全审计/最终验收由其他角色负责"
2. **信息隔离兜底**：即使开发者知道 Playwright 知识，信息隔离机制让它不知道测试工程师是否存在，编排者仍会独立路由
3. **编排者指令约束**：给开发者派任务时明确"你的产出将由独立角色验证"

### 4.5 风险 R5：多 agent 交叉冲突

**机制**：多个 agent 同时注入同一角色时，prompt 膨胀导致模型注意力分散，遗漏关键建议。

**缓解**：
1. **一次一个**：编排者 dispatch 时按任务类型只加载相关的 1 个 agent
2. **垂直整合**：如果必须同时加载多个，创建按场景分段的综合参考块，而非逐文件粘贴

### 4.6 风险 R6：注入内容的安全隐患

**机制**：agency-agents 的代码示例未被安全审计，可能包含硬编码密码/不安全模式。

**缓解**：
1. **快照安全扫描**：下载后对每个文件 grep 不安全模式（password=、secret_key=、eval(、exec(、rm -rf /）
2. **不信任默认声明**：每个注入文件开头标注代码示例不保证安全性，使用前需审查

---

## 5. 实施步骤

分三步走，每步独立验证：

### Step 1：建立注入基础设施
创建目录结构：
```
references/skills/agency-inject/
├── manifest.md            # 注入映射表 + 注入协议
├── extraction-rules.md    # 提取规则（提取什么/丢弃什么）
├── conflict-rules.md     # 冲突裁决规则
└── snapshots/             # 清洗后的 agent 文件快照
    ├── engineering-frontend-developer.md
    ├── engineering-backend-architect.md
    ├── engineering-code-reviewer.md
    ├── ...
    └── MANIFEST.json      # 版本元数据
```

**不修改任何现有角色文件**，只新建基础设施。

### Step 2：修改角色文件
在 6 个角色文件末尾追加"增强知识来源"章节。每个修改遵循注入协议（分段锚定 + 优先级声明 + 知识边界声明）。

**修改清单**：
- `roles/03-architect.md`
- `roles/04-developer.md`
- `roles/05-test-engineer.md`
- `roles/06-reviewer.md`
- `roles/08-red-team.md`
- `roles/09-debug-specialist.md`
- `roles/10-design.md`

### Step 3：下载+清洗内容快照
- 从 `msitarzewski/agency-agents` 下载 16 个相关文件
- 按提取规则清洗（丢弃 Identity/Memory/Communication Style/Vibe）
- 标注快照日期和 commit hash
- 跑安全扫描

### 验证清单
每步完成后验证：
1. Step 1 验证：manifest 映射表无遗漏/无重复
2. Step 2 验证：修改后角色文件保持原有 DoD/边界/工具授权；跑一次 guard-check 无新增问题
3. Step 3 验证：快照文件内容与原始文件一致（sha256sum 对比提取前后的差异）

---

## 6. 不做的事情（边界）

本设计明确 **不做** 以下事情：

1. **不改框架安全系统**：防幻觉/防失控/异常处理不因注入改变
2. **不改退出门禁**：5 条门禁（含人验收）不变
3. **不改信息隔离协议**：角色间互不知对方存在的原则不变
4. **不改协作流程**：双层循环 + 星型路由 + 规格化阶段不变
5. **不变保证度度量**：完备性×不可绕过×网自验的乘法模型不变
6. **不加新角色**：仍然是 10 角色（8核心+2可选），不新增

**框架不变，只增强。** 注入是扩展层，不是重构层。
