---
name: multi-agent-dev-team
description: >-
  用专业化、可协作的多智能体团队来开发软件。Use whenever the user wants to build software
  with multiple cooperating AI agents, divide work among specialized roles, set up a dev team,
  do role-based collaboration (产品/架构/开发/测试/审查), handle both front-end and back-end
  with specialized agents, or establish a project's long-term multi-agent collaboration structure.
  在用户提到"多智能体""多角色""团队协作开发""分工开发""组建开发团队""前端后端分别用智能体""代码量持续增长/需要长期协作的项目"时也务必触发,即使用户没明说"多智能体"。
  不要用于单文件修改、加小功能、修 bug、一次性单点任务——那些用 superpowers 生态的单点 skill(brainstorming/TDD/writing-plans 等)或直接做即可。拿不准时默认用单点能力,撞墙(一人搞不定、要测试审查把关、要交付闭环)再升级到本团队。
---

# Multi-Agent Dev Team

把软件项目当作一支**专业化团队**来推进:产品、架构、开发、测试、审查、知识管理各司其职,围绕一份"事实来源文档"协作。本 skill 提供团队结构、每个角色的完整配置(含内化子技能)、协作流程、文档模板,让你在任何项目上落地多智能体协作。

## 何时用本 skill(vs 用 superpowers)

本 skill 是 superpowers 生态的**上层编排层**,不是替代。关系:
- **superpowers** = 工具箱 + 单点能力(brainstorming/TDD/writing-plans…)——日常 always-on,做单个任务
- **本 skill** = 把多专长智能体编排成一支有交付闭环的团队——只在大工程套上(内部仍会调用 superpowers 的 skill)

### 该用本 skill(团队 / 交付闭环)
- 从零开发多模块产品(如"开发XX系统,前端后端都要,要稳定上线")
- 代码量大、逻辑复杂、需要持续迭代 + 长期记忆
- 需要"产品交付":有退出条件 + 人验收,不是改改就完
- 需要对抗性验证(测试+审查+红队)

### 该用 superpowers(单点 / 直接做)
- 一个会话内自己能做完的任务
- 改 bug / 加小功能 / 改样式 / 加单元测试 / 审查一段代码 / 重构一个函数
- 例:加按钮→直接做;想探索设计→brainstorming;修bug→TDD;重构→gitnexus-refactoring

### 快速自测(三问)
1. 一个会话内自己直接做能做完吗?能→superpowers/直接做
2. 需要多角色分工 + 对抗性验证吗?不需要→superpowers
3. 需要交付闭环(退出条件 + 人验收)?不需要→superpowers;**需要→本 skill**

**拿不准时默认 superpowers(轻)**,撞到墙("一个人搞不定,要测试审查把关")再升级到本 skill。

> 口诀:**一个会话能做完 → superpowers;需要团队、要交付、有验收闭环 → multi-agent-dev-team。**

## 核心设计原则(单模型约束下)

当所有角色共用同一个模型时(常见情况),角色差异**不来自模型能力**,而来自四层结构:

1. **目标函数不同**——开发者追"完成",测试追"证明它不行",审查追"找缺陷"
2. **工具授权不同**——只读 vs 可写,强制角色分离
3. **上下文范围不同**——看 diff vs 看全局
4. **行为指令不同**——对同一模型下不同的思考指令

> 这四条是单模型下质量保证的全部来源。少一条,质量塌一截。

## 角色速查(8 核心 + 2 可选)

| # | 角色 | 目标函数 | 工具授权 | 内化的子技能 |
|---|------|---------|---------|------------|
| 1 | 需求分析师 | 消除歧义 | Read+提问 | 需求结构化、验收标准、**问题空间(假设/成功指标)、非功能可度量预检** |
| 2 | 编排者 | 高效调度 | 全调度(不写业务代码) | 任务分解、依赖管理、**门禁收集不自动宣布** |
| 3 | 架构师 | 结构健康 | 只读代码+写决策 | 系统设计、技术债治理、**非功能架构、交互规约§3** |
| 4 | 开发者 | 完成需求 | Edit/Write/Bash | **前端+后端+测试编写(UI设计已剥离给 design)、可靠性5维(性能/容错/安全/可观测/并发)** |
| 5 | 测试工程师 | 证明它不行 | Bash(不可改实现) | 测试策略、**属性/模糊测试**、边界覆盖、**性能/安全测试** |
| 6 | 审查者 | 找出缺陷 | 只读 | 对抗性审查、盲点捕捉、**第10条可靠性审(性能/安全/可观测)** |
| 7 | 知识管理者 | 记忆完整 | 全文档读写 | 文档维护、上下文持久化、**文档版本化** |
| 8 | 设计师 | 提议审美 | Read+WebSearch+提问(不写业务代码) | **memorable-thing 锚点、DESIGN.md、Research三层+Eureka、0.0d设计疑问、taste-profile** |
| **9** | **红队(可选)** | **攻破系统** | Bash+只读+攻击脚本 | **威胁场景、恶意输入、并发/安全** |
| **10** | **调试专家(可选)** | **找根因** | 只读+Bash诊断 | **根因分析、不盲改** |

每个角色的**完整配置**(身份/职责/边界/prompt/内化子技能)在 `references/roles/` 下,按需加载。

> 角色间协作靠"目标对立"制造多样性:开发者=完成,测试=让它失败,审查=找缺陷,**红队=试图攻破,调试专家=找根因不盲改**。同一模型,目标对立,行为就分化。

## 如何落地(从最小团队起步)

> 组建多智能体团队像组建创业公司:用最小团队跑通业务,让真实反馈告诉你该招下一个人。架构图是结果,不是起点。

```
阶段0  人+单智能体,跑通核心管道,沉淀第一版事实来源文档
阶段1  +测试工程师 + 审查者      ← 逻辑复杂时最先加,建立客观验证回路
阶段2  +架构师 + 设计师 + 知识管理者  ← 代码量增长/有 UI 时加,上治理·设计·记忆(design 规格化阶段产 DESIGN.md)
阶段3  +编排者 + 需求分析师      ← 任务变多需要调度时加,全8核心角色到位
阶段4  按需加 安全审查/调试专家/DevOps
```

每个阶段问同一个问题:**当前最大瓶颈或最近失败,是不是因为缺某个角色?** 是→加;不是→别加。

详细落地步骤见 `references/collaboration-flow.md`。

## 交付闭环:双层循环 + 退出门禁

交付稳定产品靠**两层循环**,不是单向流水线(详见 `references/collaboration-flow.md`):

- **内层循环**(单次改动):开发 → 测试 → 审查,失败/打回就回开发者,直到"测试全绿 + 审查放行"
- **外层循环**(产品级):遍历所有需求跑内层循环,全部处理完进入退出门禁

**退出门禁(5条,定义"什么时候算交付")**:前4条客观(测试全绿/质量门禁全绿/无高优先级审查问题/无高优先级技术债),**第5条必须人验收**。门禁全绿时编排者**不自动宣布交付**,而是向人发起最终验收请求,由人拍板。

> ⚠️ **不能纯靠"验证代理觉得满足/无逻辑错误"**:AI会幻觉,"没发现错误"≠"没有错误";"无逻辑错误"不可绝对保证(停机问题)。只能保证"已知验证手段下未发现"。所以需要回归基线+审查+人验收的多重把关。**交付权最终在人。**

## 幻觉发现与纠正(可靠交付的关键)

防幻觉不能只靠"审查者读 diff"单视角(审查者也会幻觉)。本 skill 有完整的**发现→纠正→防复发**闭环(详见 `references/cross-verification.md`):

1. **全量交叉核对**:每个"完成/通过/正确"声明,由**非作者角色独立复现证据**(不信声明,只信复现)。复现失败=幻觉被抓。
2. **幻觉日志**(事实来源文档区块11):每次幻觉记 声明/真相/怎么发现/规律标签。
3. **质疑前移**:审查者/红队**默认不信任任何声明**,对"完成/通过/符合"追问"证据/复现/来源"三连。开发阶段就攻,不只验收时。
4. **可执行守卫断言**:编排者每轮必填 checklist(完成声明都有非作者复现证据?测试是本轮新鲜跑的?)。**幻觉日志的规律标签回流为永久必查项**。
5. **子代理输出结构化契约**:测试/审查/红队的输出必须"过程与结论分离 + 结论按固定schema"(放行/打回+缺陷列表),不输出自由散文。实测发现审查子代理输出126KB散文超阈值且格式不可解析——和需求不结构化是同源问题(源头不结构化,下游混乱)。详见 `references/cross-verification.md` 机制5。

> **闭环价值**:幻觉一旦被发现,它的类型永久进入必查清单。系统越来越难犯同类幻觉——不是靠人盯,是系统自我加固。代价:全量交叉核对增加协调成本,适合高可靠交付项目。

## 信息隔离(角色互不知对方存在)

本框架基于 **ZCode 子代理(subagent)机制**实现,子代理天然隔离(独立 context,不继承主会话,只看到传给它的指令)。详见 `references/isolation-protocol.md`。

**全隔离原则**:角色之间**互不知道对方存在**——不直接通信、看不到对方对话/声明/身份。编排者是**唯一路由器**,所有角色只对接编排者:
- 编排者给每个角色的输入**脱敏**(剥离"谁产生的/谁声称了什么")
- 测试工程师收到的不是"开发者说测试通过了",而是"这是 diff 和验收标准,跑验证"——它根本不知道有声明存在,所以它的复现是真独立
- 隔离让交叉核对的"非作者复现"才真正成立(不被声明带偏)

> ⚠️ **不要用"单会话内扮演多角色"**——同 context 无法隔离,所有"角色"其实看到全部历史,交叉核对失效。必须用子代理。

## 文件结构(progressive disclosure)

本 skill 分三层加载,**不要一次性全读**:

1. **本 SKILL.md**——已加载。够你判断"是否要用本 skill"和"整体框架"
2. **按需读 references/**:
   - 要一页看懂整体架构(全框架如何交付稳定产品) → 读 `references/ARCHITECTURE.md`
   - 要建事实来源文档 → 读 `references/project-context-template.md`
   - 要跑协作流程/调度 → 读 `references/collaboration-flow.md`
   - 要按场景定限制/失败handler(超时/循环/重试按任务画像分流) → 读 `references/exception-handling.md`
   - 要扮演/配置某角色 → 读 `references/roles/<对应角色>.md`
   - 要给某角色注入 agency-agents 技术参考 → 读 `references/skills/agency-inject/injection-protocol.md`(协议) + `manifest.md`(任务→agent 映射) + `snapshots/cleaned/<agent>.md`(已清洗快照)

```
multi-agent-dev-team/
├── SKILL.md
└── references/
    ├── ARCHITECTURE.md                 整体架构梳理(一页看懂全框架如何交付稳定产品,顶层综合视图)
    ├── prd-template.md                 PRD 模板(产品级规约,01 生产,8 节结构)
    ├── interaction-spec-template.md    界面交互规约模板(01+03 co-author,6 区块,§6 喂 V-UI-STRUCT)
    ├── project-context-template.md     事实来源文档模板(团队大脑)
    ├── collaboration-flow.md           协作流程 + 双层循环(含交叉核对) + 退出门禁
    ├── anti-hallucination.md           防幻觉7约束 + 发现与纠正机制
    ├── cross-verification.md           交叉核对+幻觉日志+质疑前移+可执行断言
    ├── change-impact-analysis.md       变更影响分析(改已交付的先评估影响,持续交付命脉)
    ├── isolation-protocol.md           全隔离协议(角色互不知对方存在,编排者星型路由,含子代理能力探测+落盘折扣)
    ├── guardrails.md                   失控护栏(循环上限/升级阶梯/预算守护/子代理超时降级,P2基线被画像覆盖)
    ├── exception-handling.md           异常处理+任务画像驱动限制(按场景分流handler,含副作用门禁/熔断/并发上限)
    ├── scripts/
    │   └── guard-check.py              可执行守卫断言(核完成声明证据+幻觉标签回流必查项)
    ├── roles/                          10 个角色(8核心+2可选:红队/调试专家;表格序号=逻辑序,文件名=稳定标识)
        │   ├── 01-requirements-analyst.md
        │   ├── 02-orchestrator.md
        │   ├── 03-architect.md
        │   ├── 04-developer.md              ← 内化前端/后端/测试(UI设计已剥离给 design)
        │   ├── 05-test-engineer.md          ← 内化属性/模糊测试(L1)
        │   ├── 06-reviewer.md
        │   ├── 07-knowledge-manager.md
        │   ├── 10-design.md                 ← 核心,提议审美/DESIGN.md/memorable-thing(规格化阶段)
        │   ├── 08-red-team.md              ← 可选,攻破系统
        │   └── 09-debug-specialist.md      ← 可选,根因分析(深bug)
    └── skills/                         团队内部前端UI skill(不独立触发,按需加载,归 design 角色)
        ├── agency-inject/             ⚠ 跨角色注入层(agency-agents 快照,增强 7 个角色的技术知识)
        │   ├── MANIFEST.json           快照版本元数据 + 30天刷新窗口
        │   ├── manifest.md             角色→agent 映射 + 任务画像→加载 agent 表
        │   ├── injection-protocol.md   注入协议(提取规则/加载规则/冲突裁决)
        │   └── snapshots/
        │       ├── (19 个 raw .md)    原始快照(供 30 天 refresh 比对)
        │       └── cleaned/           按协议清洗后的注入源(去 Identity/Memory/Style/Vibe,只留 CR/TD/WF/SM)
        ├── ui-ux-pro-max/              设计系统生成器(Python工具,搜配色/字体/风格)
        ├── imagegen-frontend-web/      Web 设计图生成
        ├── imagegen-frontend-mobile/   移动端设计图生成
        ├── image-to-code-skill/        图转码
        ├── taste-skill/                反模板前端
        ├── redesign-skill/             升级现有项目
        └── {brandkit,minimalist-skill,soft-skill,...}  设计风格变体
```

> **agency-inject 是什么**:框架角色(03/04/05/06/08/09/10)的**技术交付物参考增强层**,来自 `msitarzewski/agency-agents` 的精选 agent。每个角色文件末尾有"增强知识来源"章节,编排者 dispatch 时按任务画像从 `snapshots/cleaned/` 加载对应 agent(每轮≤1 个),context 预算软指导 ≤30%。注入材料**不含身份语句**(提取时丢弃 Identity/Memory/Communication/Vibe),优先级安全靠结构层(提取丢弃 + 锚定句 + 工具授权墙),不靠行数硬限。冲突时框架规则优先。详见 `references/skills/agency-inject/injection-protocol.md`。

## 借力的已有 skill(方法论层)

本 skill 的角色用**混合方式**承载能力:核心技能硬编码进角色文档,方法论层引用已有 skill。

**A. 根目录独立触发**(用户级 skill,直接调用):

| 角色 | 借力的已有 skill | 用途 |
|------|-----------------|------|
| 需求分析师 | `brainstorming` | 需求/设计前探索意图 |
| 编排者 | `writing-plans`、`executing-plans`、`subagent-driven-development`、`dispatching-parallel-agents`、`verification-before-completion` | 计划、执行、子代理调度、并行派发、集成产出独立验证 |
| 架构师 | `gitnexus-exploring`、`gitnexus-impact-analysis`、`gitnexus-refactoring` | 理解代码库、影响分析、安全重构 |
| 开发者 | `test-driven-development`、`brainstorming`、`using-git-worktrees`、`receiving-code-review`、`systematic-debugging` | TDD、设计前探索、隔离工作区、处理审查反馈、根因调试 |
| 测试工程师 | `test-driven-development`、`verification-before-completion` | 测试方法论、完成前验证 |
| 审查者 | `council-orchestrate`、`council-review`、`requesting-code-review`、`gitnexus-pr-review`、`verification-before-completion` | **★强制多模型审查**（Onklaud 5 五层流水线）、双模型审+仲裁、审查方法、完成前验证 |
| 知识管理者 | `headroom`、`writing-skills` | 上下文持久化、技能维护 |
| 设计师 | `brainstorming`、`impeccable`、`design-taste-frontend` | 设计前探索意图、设计规范/反 AI slop、落地页三旋钮 |
| 红队(可选) | `gitnexus-pr-review`、`gitnexus-taint-analysis`⚠(未验证可用) | 风险评估、数据流分析 |
| 调试专家(可选) | `systematic-debugging` | 先找根因再修 |

**B. 平台前端 skill**(插件缓存提供,直接调用):
- 开发者:`android-dev`、`ios-dev`(移动端 UI 构建 + screenshot 截图验证渲染)

**C. 团队内部前端 UI skill**(`references/skills/` 下,**不独立触发**,design 角色按需读其 SKILL.md):
- `ui-ux-pro-max`(调 Python 搜配色/字体/风格,生成设计系统)
- `imagegen-frontend-web`、`imagegen-frontend-mobile`(生成设计参考图)
- `image-to-code-skill`(图转码)
- `taste-skill`(反模板前端)、`redesign-skill`(升级现有)
- `brandkit`/`minimalist-skill`/`soft-skill`/`brutalist-skill`/`stitch-skill`/`output-skill`(风格变体)

> 这些是增强项。若某 skill 未安装,角色核心能力(硬编码部分)仍可用。
> **防幻觉与失控防护**额外依赖:`verification-before-completion`(evidence before claims)、`systematic-debugging`(no fix without root cause)。
>
> **为什么前端 UI skill 放 references 而非根目录**:避免根目录臃肿(44→29),减少常驻 context。前端 UI 能力通过团队按需加载即可,不需要每个都独立触发。详见开发者角色的"UI 闭环"。

## 已落地实例参考

框架已在多个真实项目全程落地(回合制 web 游戏、Tauri 桌面工具、SEO 数据管线等),区块 0-13 全量运转。填写范例直接看 `references/project-context-template.md` 的逐区块注释;欢迎通过 PR 贡献你的脱敏实战范例到 `examples/`。

## 铁律(六条)

1. **先读后做**——任何角色动手前先读事实来源文档对应区块
2. **验证而非信任**——AI 会自信地产生幻觉,任何"完成了"必须有客观信号(测试/类型/编译)证明
3. **更新才算交付**——产出后必须更新事实来源文档对应区块,不更新的产出等于未交付
4. **需求结构化(按优先级分层)**——P0 需求必须全结构化(ID/输入/处理/输出/异常/验收标准/优先级/状态全填),缺字段不准进下游;P1/P2 可简化。**UI 触及的 P0 还须标 `界面交互:是` 并填 `交互规约章节`(对应 `docs/INTERACTION_SPEC.md`),guard-check 检查7 弱 oracle 卡空值;每条 P0 须列假设(带 已验证/未验证),检查8 卡;问题陈述+成功指标经多角色评审(04/05/design 提疑问)+06综合审+早期人 gate 确认才准规格化(治"解决错问题")**。模糊从源头进下游成本放大10倍,结构化是防幻觉的第一道闸。
5. **任何变更:改前评估影响 + 改后查逻辑错误**(两步缺一不可)——动之前先评估影响哪些已交付的需求/模块,定回归验证范围,得许可才准改(区块12);**改完之后必须复查本轮改动的逻辑错误**(边界/null/竞态/与既有逻辑矛盾),不只靠测试绿(测试有盲区,绿≠无逻辑错)。改已交付的不评估=定时炸弹;改完不复查=把盲区留到运行时。详见 `references/change-impact-analysis.md` + `references/anti-hallucination.md`。
6. **可靠性维度(稳定可靠的硬维度)**——代码不只功能对,须过 性能/容错/安全/可观测/并发 5 维(04 写·03 架构·05 测·06 第10条审);PRD §5 非功能须可度量(01 预检⑥),否则 05 测不了。缺一即脆——这是"稳定可靠"从口号变可执行的关键。

## 鲁棒性保障(防幻觉 + 防失控 + 异常处理)

交付稳定产品,光靠角色分工不够,必须有系统化的**防幻觉约束**、**失控护栏**和**按场景的异常处理**。这三个是框架的"安全系统",不是可选增强:

- **防幻觉** (`references/anti-hallucination.md`):工具锚定、事实/推测分离、可证伪声明、关键决策双重确认、不确定就说不确定、小步快验等7条约束 + 发现与纠正机制 + **完成时自检+未知日志(区块14)+落地后深审**(补注3:尤其 04/03 完成时回扫不确定项,诚实记入不卡交付,落地后深审消费)。所有角色必读。
- **失控护栏** (`references/guardrails.md`):内层循环上限、失败升级阶梯(重试→换角度→换角色→重新分解→**叫人**)、无进展检测、活锁检测、预算守护、**子代理任务粒度上限+超时降级**(实测补强)。编排者持此,防止死循环和预算爆炸。
- **可执行守卫断言** (`references/scripts/guard-check.py`):每轮必跑的闸门脚本——核"完成声明有无非作者复现证据",并把**幻觉日志的规律标签自动回流为本轮必查项**(实测补强,把文字checklist变成脚本卡住不让过)。
- **信息隔离** (`references/isolation-protocol.md`):角色互不知对方存在,编排者星型路由脱敏输入。含**子代理能力探测+主会话落盘折扣**。**编排者做集成是本职不是折扣**(集成型代码——需看多模块实际接口的,如core/index/适配层——归编排者,独立模块仍派子代理;集成产出仍交独立子代理验证)。
- **异常处理+任务画像** (`references/exception-handling.md`):**防失控的应用层补充**——guardrails 管流程控制(循环/预算一律撞墙→叫人),本文件管**按场景的失败 handler**(同一触发,不同任务画像走不同恢复)。任务画像(P1查证/P2生成/P3集成/**P4副作用**/P5探索)驱动限制与 handler 分流;补 6 类原缺 handler(**副作用门禁**/工具失败分流/非超时崩溃/context溢出/幂等重试/并发上限/熔断)。编排者派任务前先按 4 问决策树定画像;开发者遇副作用硬停。**P4 副作用型绝不自动重试**(防双写)。

> **核心原则:系统永远要有出路,且最高出路是"停下来叫人",不是"无限跑下去"。** 撞墙不是失败,撞墙不升级才是失败。

## 减少人参与的验证强度阶梯

若要尽量减少人参与(代价:自动化投入大、风险后移到运行时),用分层防御:

| 级别 | 手段 | 状态 |
|------|------|------|
| L0 | 单元/集成测试 + 审查 | 基线(测试工程师+审查者) |
| **L1** | **属性测试/模糊测试**(自动发现边界) | **已默认启用**(内化进测试工程师) |
| L2 | 变异测试(自动验证测试质量) | 按需加 |
| **L3** | **红队智能体(专攻破)+ E2E用户场景** | **可选第8角色**(见 roles/08) |
| L4 | 形式化验证关键逻辑 + 影子环境灰度 | 仅核心算法/高风险 |

> **当前默认 L0+L1,可选加 L3(红队)**。L1 几乎无成本却显著减少边界 bug;L3 红队在人最终验收前挡一道缓冲,最能减少人验收负担。不要追求"消灭人参与"——把人移到最高价值的两点(需求+最终验收),中间用叠层把关。即使 L4 也有盲区。

## 可靠性度量:保证度三因子(乘法模型)

L0-L4 是"怎么加验证强度"(**手段**)。**怎么量可靠性本身**?用三因子乘法:

> **保证度 = 完备性 × 不可绕过 × 网自验**(任一为 0 则全盘 0)

| 因子 | 含义 | 怎么提 |
|------|------|--------|
| 完备性 | 验证覆盖全不全(所有需求/分支/边界有测试?) | L0-L4 阶梯提;补变异盲区;清非★债 |
| 不可绕过 | 验证能不能被跳过(本地 hook 可 `--no-verify`?) | 本地 hook(可绕)→ 远端 CI(绕不过)→ 分支保护阻断门(进不了主干) |
| 网自验 | 验证是非伪造 oracle(退出码/文件 stat/sim 实测,不信模型声称) | 可执行 guard-check 路由;反幻觉 claim→verify;变异(测测试本身) |

**为什么乘法不是加法**:完备性 0.9 但不可绕过 0(本地 hook 全绕)→ 实际 0(被绕过的验证等于没验证)。三因子任一短板直接归零,不能互相补偿——所以"测试很全"救不了"门可绕"。

**和 L0-L4 的关系**:L0-L4 是**手段**(加哪层提哪个因子:L1 属性测试提完备性、L2 变异提网自验、远端 CI+分支保护提不可绕过);保证度三因子是**度量**(算出几分、定位短板)。**先算三因子定位最弱因子,再用 L0-L4 针对性补**——不是无脑加测试。

> 实测(案例A（某回合制 web 游戏）):完备性 0.82 × 不可绕过 0.85(远端 CI 无阻断门)× 网自验 0.85 ≈ **0.59**。**完备性 0.82 是最低因子(短板)**——补前端测试+清非★债提完备性,对乘积提升最大(0.82→0.92 给 +0.072,边际略高于补不可绕过到 0.95 的 +0.070);不可绕过 0.85 次之(补阻断门)。乘法模型直接指出:先补最低因子,不是无脑加任意测试。
