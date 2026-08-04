# multi-model-review — 多模型审查子系统

框架的"第 06 审查者"强制走多模型审查：**任何代码审查都不允许单模型应付**。本子目录是该机制的完整实现。

## 组成

| 文件 | 作用 |
|------|------|
| `council-review-SKILL.md` | 双模型独立审 + 分歧仲裁引擎（skill 形态，给 06 审查者读） |
| `council-orchestrate-SKILL.md` | Onklaud 5 五层流水线：认知守护（免疫记忆+ADR注入）→ 认知多样（双模型审+仲裁）→ 执行守护（guard-check 真测试）→ 学习守护（失败回喂）→ 流程守护（阶段门禁） |
| `review_engine/` | Python 实现：`client.py`(调用层) `config.py`(配置) `merge.py`(缺陷合并+仲裁) `delta.py`(修复闭环 delta 审) `memory.py`(结构化免疫记忆) `verify.py`(guard 真跑) 等 |
| `examples/` | `llm_proxy.example.yaml`（模型席位配置示例）+ `immune_memory.example.md`（免疫记忆示例） |

## 核心思想

**把 LLM 当不可信执行器**：模型说"通过"不算数——

- **双模型异架构交叉审**：不同模型拿不同目标函数（代码审查者逐行找 bug / 架构审查者找设计层问题），冲突是故意的。
- **分歧仲裁**：两份报告分差 ≥ 阈值（默认 1.5）触发第三模型仲裁。
- **免疫记忆注入**：已确认"非 bug"的业务设计前置注入 prompt，防重复误报，越审越准。
- **delta 回喂**：修复后不是从零重审，而是带着上轮 defect list + 业务验收标准做增量审——确认①旧缺陷消失 ②没引入新缺陷 ③业务验收标准仍满足。
- **执行守护**：`guard-check --execute` 用真实退出码裁决，测试全绿必须是本轮新鲜复现。

## 接入（3 步）

1. **配置模型席位**：复制 `examples/llm_proxy.example.yaml` 到 `~/.zcode/llm_proxy.yaml`（或设环境变量 `LLM_PROXY_CONFIG` 指向你的路径），填你的 OpenAI 兼容代理端点与三个席位模型（代码审查者/架构审查者/仲裁者，建议异架构）。密钥放 `key_file` 指向的 JSON，不进版本库。
2. **安装引擎**：把 `review_engine/` 放到任意目录，调用方 `sys.path.insert` 指向它（文档中的 `~/.zcode/llm_tools` 只是一种放置约定）。
3. **建立免疫记忆**：参考 `examples/immune_memory.example.md` 建你的全局免疫记忆文件（`memory.py` 的存储路径可用环境变量 `IMMUNE_MEMORY_FILE` 覆盖）。每轮审查发现的"模型误判为 bug 但实际是业务需求"，追加进去。

```python
from review_engine import council_review

report = council_review(
    code=open("src/foo.rs").read(),
    file_path="src/foo.rs",
    code_type="rust",               # rust | react | architecture
    context="ADR-002: ...",          # 业务上下文
    immune_memory=open("immune_memory.md").read(),
    output_dir="reports/",
)
print(report["merged_defects"])      # 合并后的缺陷清单（含严重级）
```

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `LLM_PROXY_CONFIG` | `~/.zcode/llm_proxy.yaml` | 席位配置文件路径 |
| `LLM_PROXY_URL` | `http://localhost:8000/v1` | 代理端点兜底值（YAML 未配 url 时） |
| `LLM_KEY_FILE` | `~/.llm_proxy_keys.json` | 密钥 JSON 兜底路径 |
| `IMMUNE_MEMORY_FILE` | `~/.llm_review/immune_memory.json` | 结构化免疫记忆存储 |

## 已踩过的坑（直接用结论）

- **不要设 max_tokens**：思考型模型的 reasoning_tokens 会先吃配额——设小值导致正文空回复，设过大反而崩；不设让模型用默认上限最稳（探测证据见 immune_memory 示例 §5.3）。
- **仲裁模型要复测**：模型升级后，旧探测数据（输出上限/耗时行为）不能直接沿用。
