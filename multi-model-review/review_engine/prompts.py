"""review_engine.prompts — 审查 prompt 模板

四套模板：Rust / React / Architecture / Arbiter
所有模板含占位符 {context}{file_path}{code}
项目上下文通过 {context} 注入（ADR / 业务需求 / immune_memory 等）
"""
import json

# ============================================================
# 通用审查维度定义
# ============================================================
COMMON_DIMENSIONS = """审查维度（全覆盖）：
- panic_path: unwrap/expect/索引/除零/任何 panic 边缘
- type_safety: Option/Result/NaN/f64==0 精确比较
- edge_case: 空/NaN/None/边界 防护是否到位
- error_handling: 错误传播路径是否完整
- performance: clone/堆分配/重复编译/不必要复制场景
- api_design: 接口签名/类型建模/是否使用枚举而非字符串
- clarity: 命名/注释/可读性/技术债
- concurrency: Mutex/Async 使用场景"""

OUTPUT_FORMAT = """输出严格 JSON（无 markdown 包裹）：
{{"score":1-10,"passed":true|false,"critique":"总体评价","defects":[{{"severity":"blocker|critical|warning","category":"panic_path|type_safety|edge_case|error_handling|performance|api_design|clarity|concurrency","line":"行号或范围","issue":"具体问题","fix":"修复方向","business_check":"pending|confirmed_bug|confirmed_requirement","business_ref":"对应 PROJECT_CONTEXT/ADR 编号"}}]}}"""


# ============================================================
# Rust 代码审查模板
# ============================================================
RUST_REVIEW = """你是高级 Rust 代码审查专家。审查以下代码，只输出严格 JSON（无markdown包裹）：

{output_format}

{common_dimensions}

模块上下文（必须先验证是否为业务需求，避免把故意设计误判为 bug）：
{context}

路径：{file_path}

代码：
```rust
{code}
```
"""


# ============================================================
# React 代码审查模板
# ============================================================
REACT_REVIEW = """你是高级 React/前端工程师，独立审查以下 React 代码。
{output_format}

审查维度：
- state_machine: 状态机是否完整、转换是否覆盖所有边界
- side_effect: useEffect 依赖、cleanup、cancelled flag、内存泄漏
- race_condition: 并发请求竞态、旧响应覆盖新
- performance: 不必要 re-render、内联函数、未 memo、O(n²)
- a11y: 语义 HTML、tabindex、aria-live、键盘可达
- gsap_lifecycle: 动画守卫、stagger 重放、display:none 下动画触发（如适用）
- api_contract: invoke 错误处理、loading 状态、空数据处理
- clarity: 命名、组件拆分、可读性

模块上下文（必须先验证是否为业务需求）：
{context}

路径：{file_path}

代码：
```jsx
{code}
```
"""


# ============================================================
# 架构审查模板
# ============================================================
ARCHITECTURE_REVIEW = """你是高级系统架构师，独立审查以下模块设计。
{output_format}

审查维度：
- consistency: 所有 command/接口的错误处理是否一致、参数命名是否统一
- async_propagation: async/spawn_blocking 是否正确传播、错误是否在边界丢失
- error_propagation: Result 链路是否完整、错误是否吞没
- transaction_boundary: 事务边界、锁/资源持有时间
- coupling: 模块耦合度、单文件复杂度、是否需要拆分
- observability: 错误可观测性、日志完备度
- testability: 是否可独立单测、有没有硬依赖
- maintainability: 一人维护成本、未来扩展难度

模块上下文（必须先验证是否为业务需求）：
{context}

路径：{file_path}

代码：
```
{code}
```
"""


# ============================================================
# 仲裁模板
# ============================================================
ARBITER = """你是最终仲裁者。综合两份独立审查报告，给出最终结论。
输出严格 JSON：
{{"final_score":1-10,"verdict":"pass|fail|needs_revision","consensus_defects":[两审查者都同意的缺陷],"divergent_defects":[仅一方提出的缺陷，附是否采纳理由],"merged_defects":[最终采纳并合并的缺陷，按 severity 排序],"blockers":[必须修复才能放行的缺陷],"recommendations":[非阻断但建议修复]}}

原始请求/上下文（业务需求/ADR 约束）：
{context}

模块：{file_path}

审查者 A（{model_a}）报告：
{review_a}

审查者 B（{model_b}）报告：
{review_b}
"""


# ============================================================
# immune_memory 注入片段（可拼到任意模板的 context 前）
# ============================================================
IMMUNE_MEMORY_PREAMBLE = """【已确认非 bug 清单】以下行为经业务确认是故意的，**不要报为缺陷**：
{immune_memory}

"""


# ============================================================
# 组装辅助
# ============================================================
def build_prompt(template, code, file_path, context,
                 immune_memory=""):
    """组装完整 prompt，前置注入 immune_memory"""
    full_context = ""
    if immune_memory:
        full_context += IMMUNE_MEMORY_PREAMBLE.format(immune_memory=immune_memory)
    full_context += context
    return template.format(
        code=code, file_path=file_path, context=full_context,
        common_dimensions=COMMON_DIMENSIONS, output_format=OUTPUT_FORMAT,
    )
