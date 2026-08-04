"""review_engine.delta — 修复闭环审查（第③层：学习守护）

防"修了引入新缺陷 + 修了破坏业务需求"：
04 修完后，不是从零重审，是带着上一轮 defect list 做 delta 审。
确认三件事：①旧缺陷消失 ②没引入新缺陷 ③业务验收标准仍然满足。任一不过→再回喂（最多 2 轮）。
"""
import json
from pathlib import Path
from datetime import datetime

from .client import call_model
from .parser import parse_review
from .config import load_config


DELTA_REVIEW_PROMPT = """你是高级代码审查专家。请做**修复闭环审查（Delta Review）**——不是从零重审，是确认三件事：①上一轮缺陷已修复 ②没引入新缺陷 ③业务验收标准仍然满足。

【上一轮发现的缺陷】（编号 + 严重度 + 问题）
{previous_defects}

【业务上下文】
{context}

【业务验收标准】（修复后必须仍然满足，不能因为修 bug 破坏业务需求）
{acceptance_criteria}

【已确认非 bug 清单】（不要报为缺陷）
{immune_memory}

【修复后的代码】
路径：{file_path}
```rust
{code}
```

【你的任务】
1. 逐条核对上一轮每条缺陷：修复了吗？修复正确吗？
2. 检查修复是否引入了新缺陷（改 A 坏 B）
3. **逐条核对业务验收标准**：修复后这些标准仍然满足吗？有没有因为修 bug 导致某个业务场景的行为变了？
   - 特别注意：改了底层函数（如分类逻辑/排序逻辑/过滤逻辑）后，上层依赖这些函数的所有场景是否仍然行为正确
   - 如果某个验收标准可能不再满足，标记为 business_regression（严重度=blocker）

输出严格 JSON（无 markdown 包裹）：
{{"verdict": "all_fixed|partially_fixed|new_defects_introduced|business_regression",
  "fixed": [{{"defect_id": 1, "status": "fixed|still_present|partially_fixed", "note": "说明"}}],
  "new_defects": [{{"severity": "blocker|critical|warning", "category": "...", "line": "...", "issue": "...", "fix": "..."}}],
  "business_regression": [{{"criterion": "对应的验收标准", "status": "still_met|regressed|uncertain", "explanation": "为什么认为满足/不满足"}}],
  "summary": "一段总体评价"
}}

判定规则：
- all_fixed = 所有缺陷已修复 + 无新缺陷 + 业务验收标准全部仍然满足 → 可以放行
- partially_fixed = 部分缺陷还在（无新缺陷，业务未回归）→ 继续修残留
- new_defects_introduced = 引入了新缺陷 → 必须修新缺陷 + 继续修残留
- business_regression = 业务验收标准不再满足 → **最高优先级**，必须回滚或重新设计修复方案
"""


def delta_review(code, file_path, previous_defects, code_type="rust",
                 context="", immune_memory="", acceptance_criteria="",
                 model="deepseek-v4-flash-0731",
                 config=None, output_dir="reports"):
    """修复闭环审查——带着上一轮 defect list 确认三件事：
    ①旧缺陷消失 ②没引入新缺陷 ③业务验收标准仍然满足。

    参数:
        code: str — 修复后的代码全文
        file_path: str
        previous_defects: list[dict] — 上一轮 council_review 的 merged_defects
        code_type: str — rust|react|architecture（仅用于报告标注）
        context: str — 业务上下文/ADR
        immune_memory: str — 已确认非 bug 清单
        acceptance_criteria: str — 业务验收标准（从 PROJECT_CONTEXT §3 / PRD 提取）
                             ★关键：修复后必须仍然满足这些标准
        model: str — 用哪个模型做 delta 审（单模型够用，不需要双审）
        config: dict — 缺省从 load_config()
        output_dir: str — 报告写目录

    返回:
        dict — {
            verdict: all_fixed|partially_fixed|new_defects_introduced|business_regression,
            fixed: [...],
            new_defects: [...],
            business_regression: [...],
            report_path: str,
            can_release: bool,  # all_fixed + 无新缺陷 + 无业务回归
        }
    """
    if config is None:
        config = load_config()

    # 格式化上一轮缺陷
    defects_text = _format_previous_defects(previous_defects)
    if not immune_memory:
        immune_memory = "（无）"
    if not context:
        context = "（无）"
    if not acceptance_criteria:
        acceptance_criteria = "（未提供验收标准——跳过业务回归检查，但建议提供以防止修复破坏业务需求）"

    prompt = DELTA_REVIEW_PROMPT.format(
        previous_defects=defects_text,
        context=context,
        acceptance_criteria=acceptance_criteria,
        immune_memory=immune_memory,
        file_path=file_path,
        code=code,
    )

    # 2026-07-21 修复：原写死 max_tokens=2500，思考型模型(kimi-k2.7-code)的
    # reasoning_tokens 会吃满导致正文空回复。改为读 config 全局配置。
    # 策略：config 未配 max_tokens 时返回 None，client.py 不向 payload 传该字段，
    # 模型用自己默认上限（探测：kimi 29064 / deepseek-pro 29035 / flash 29422 tokens 稳定输出）
    delta_max = config.get("review_defaults", {}).get("max_tokens")
    text, err, meta = call_model(model, prompt, max_tokens=delta_max, config=config)

    if err:
        return {
            "verdict": "error",
            "fixed": [],
            "new_defects": [],
            "business_regression": [],
            "report_path": None,
            "can_release": False,
            "error": err,
            "_meta": meta,
        }

    result = _parse_delta_result(text)
    result["_meta"] = meta

    # 判定能否放行：缺陷全修 + 无新缺陷 + 无业务回归
    biz_regression = result.get("business_regression", [])
    has_regression = any(
        isinstance(r, dict) and r.get("status") in ("regressed", "uncertain")
        for r in biz_regression
    )
    result["can_release"] = (
        result.get("verdict") == "all_fixed"
        and len(result.get("new_defects", [])) == 0
        and not has_regression
    )

    # 写报告
    report_path = _write_delta_report(
        result, file_path, previous_defects, model, meta, output_dir
    )
    result["report_path"] = report_path

    return result


def _format_previous_defects(defects):
    """格式化上一轮缺陷为文本"""
    if not defects:
        return "（上一轮无缺陷——这是首次审查后的修复确认）"

    lines = []
    for i, d in enumerate(defects, 1):
        sev = d.get("severity", "?")
        issue = d.get("issue", "")
        line = d.get("line", "?")
        biz = d.get("business_check", "pending")
        # 跳过已确认为业务需求的（不需要修）
        if biz == "confirmed_requirement":
            continue
        lines.append(f"  #{i} [{sev}] L{line} {issue}")
    return "\n".join(lines) if lines else "（上一轮缺陷均已确认为业务需求，无需修复）"


def _parse_delta_result(raw):
    """解析 delta 审查结果。

    2026-07-21 修复：kimi/deepseek 思考型模型 reasoning_tokens 可能吃满 max_tokens
    导致正文被截断（JSON 不完整）。原逻辑直接 json.loads 截断的 JSON 会抛
    JSONDecodeError 走兜底 parse_failed，丢失已输出的 verdict/fixed 等字段。
    新增容错解析：截断时用正则提取已输出的字段。
    """
    if not raw:
        return {"verdict": "error", "fixed": [], "new_defects": [], "business_regression": [], "summary": "空回复"}

    # 先试直接 parse（完整 JSON 的快路径）
    parsed = parse_review(raw)

    import re

    # delta 结果有自己的 schema，尝试提取完整字段
    try:
        full = json.loads(raw)
        return {
            "verdict": full.get("verdict", "unknown"),
            "fixed": full.get("fixed", []),
            "new_defects": full.get("new_defects", []),
            "business_regression": full.get("business_regression", []),
            "summary": full.get("summary", parsed.get("critique", "")),
        }
    except json.JSONDecodeError:
        pass

    # 从 markdown 代码块提取
    for pat in [r'```json\s*\n(.*?)\n\s*```', r'```\s*\n(.*?)\n\s*```']:
        m = re.search(pat, raw, re.DOTALL)
        if m:
            try:
                full = json.loads(m.group(1))
                return {
                    "verdict": full.get("verdict", "unknown"),
                    "fixed": full.get("fixed", []),
                    "new_defects": full.get("new_defects", []),
                    "business_regression": full.get("business_regression", []),
                    "summary": full.get("summary", ""),
                }
            except json.JSONDecodeError:
                pass

    # 2026-07-21 新增：容错解析截断的 JSON
    # 思考型模型可能因 max_tokens 不够导致 JSON 输出到一半被截断，
    # 用正则提取已输出的顶层字段，至少能拿到 verdict 和已输出的 fixed 列表
    truncated_fields = _extract_truncated_delta_fields(raw)
    if truncated_fields.get("verdict"):
        truncated_fields["summary"] = truncated_fields.get("summary", "") or f"⚠️ 回复被截断（{len(raw)} chars），以下为部分提取结果"
        truncated_fields["_truncated"] = True
        truncated_fields["_raw_len"] = len(raw)
        return truncated_fields

    # 兜底
    return {
        "verdict": "parse_failed",
        "fixed": [],
        "new_defects": parsed.get("defects", []),
        "business_regression": [],
        "summary": parsed.get("critique", ""),
        "_raw": raw[:300],
    }


def _extract_truncated_delta_fields(raw):
    """从容可能被截断的 delta JSON 文本里提取已输出的顶层字段。

    策略：逐字段用正则定位 "key": value 的起始，提取到下一个同级 key 或字符串末尾。
    对于数组字段（fixed/new_defects/business_regression），提取已输出的部分元素
    （即使数组没闭合，也能拿到前几个元素）。
    """
    import re

    result = {"verdict": "", "fixed": [], "new_defects": [], "business_regression": [], "summary": ""}

    # verdict: "all_fixed" / "partially_fixed" / "new_defects_introduced" / "business_regression" / "needs_revision"
    m = re.search(r'"verdict"\s*:\s*"([^"]+)"', raw)
    if m:
        result["verdict"] = m.group(1)

    # summary: "..."
    m = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
    if m:
        result["summary"] = m.group(1)

    # 提取数组字段（fixed/new_defects/business_regression）已输出的元素
    for field in ["fixed", "new_defects", "business_regression"]:
        # 定位数组开始位置
        arr_start = raw.find(f'"{field}"')
        if arr_start == -1:
            continue
        bracket_start = raw.find('[', arr_start)
        if bracket_start == -1:
            continue
        # 从 bracket_start+1 开始，逐个提取 {...} 对象
        pos = bracket_start + 1
        elements = []
        while pos < len(raw):
            # 找下一个 {
            obj_start = raw.find('{', pos)
            if obj_start == -1:
                break
            # 找配对的 }（简单版：找下一个 }，不支持嵌套）
            obj_end = raw.find('}', obj_start)
            if obj_end == -1:
                # 最后一个对象被截断，尝试提取已输出的字段
                fragment = raw[obj_start:]
                elem = _extract_partial_object_fields(fragment)
                if elem:
                    elements.append(elem)
                break
            fragment = raw[obj_start:obj_end + 1]
            try:
                elem = json.loads(fragment)
                elements.append(elem)
            except json.JSONDecodeError:
                # 单个对象解析失败，尝试部分提取
                elem = _extract_partial_object_fields(fragment)
                if elem:
                    elements.append(elem)
            pos = obj_end + 1
            # 检查是否到数组末尾
            next_char = raw[pos:pos + 1].strip()
            if next_char == ']':
                break
        result[field] = elements

    return result


def _extract_partial_object_fields(fragment):
    """从可能不完整的 {...} 片段里提取已输出的字符串字段。"""
    import re
    elem = {}
    # 提取 "key": "value" 形式的字段
    for m in re.finditer(r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"', fragment):
        elem[m.group(1)] = m.group(2)
    # 提取 "key": number 形式
    for m in re.finditer(r'"(\w+)"\s*:\s*(\d+(?:\.\d+)?)', fragment):
        try:
            elem[m.group(1)] = int(m.group(2))
        except ValueError:
            elem[m.group(1)] = float(m.group(2))
    return elem if elem else None


def _write_delta_report(result, file_path, previous_defects, model, meta, output_dir):
    """写 delta 审查报告"""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{now}_{Path(file_path).name}_delta.md"
    path = Path(output_dir) / fname
    path.parent.mkdir(parents=True, exist_ok=True)

    verdict_icon = {
        "all_fixed": "✅ 全部修复",
        "partially_fixed": "⚠️ 部分修复",
        "new_defects_introduced": "🚨 引入新缺陷",
        "business_regression": "🔴 业务回归",
        "error": "❌ 审查失败",
        "parse_failed": "❌ 解析失败",
    }.get(result.get("verdict", ""), "?")

    md = f"""# Delta 审查报告（修复闭环）

**日期**: {now}
**文件**: `{file_path}`
**模型**: {model}
**耗时**: {meta.get('ms', '?')}ms

## 裁决: {verdict_icon}

{result.get('summary', '')}

## 上一轮缺陷修复状态 ({len(result.get('fixed', []))} 条)
"""
    for f in result.get("fixed", []):
        if not isinstance(f, dict):
            continue
        did = f.get("defect_id", "?")
        status = f.get("status", "?")
        note = f.get("note", "")
        icon = {"fixed": "✅", "still_present": "❌", "partially_fixed": "⚠️"}.get(status, "?")
        md += f"- {icon} #{did} {status}: {note}\n"

    new = result.get("new_defects", [])
    md += f"\n## 新引入缺陷 ({len(new)} 条)\n"
    if not new:
        md += "✅ 无新引入缺陷\n"
    else:
        for d in new:
            if not isinstance(d, dict):
                continue
            md += f"- **[{d.get('severity','?')}]** L{d.get('line','?')} {d.get('issue','')}\n"

    # 业务回归检查 ★关键
    biz_reg = result.get("business_regression", [])
    md += f"\n## 业务验收标准回归检查 ({len(biz_reg)} 条)\n"
    if not biz_reg:
        md += "（未提供验收标准，跳过业务回归检查）\n"
    else:
        for r in biz_reg:
            if not isinstance(r, dict):
                continue
            crit = r.get("criterion", "?")
            status = r.get("status", "?")
            explain = r.get("explanation", "")
            icon = {"still_met": "✅", "regressed": "🔴", "uncertain": "⚠️"}.get(status, "?")
            md += f"- {icon} {crit}: {status}\n"
            if explain:
                md += f"  - {explain}\n"

    md += f"\n## 能否放行: {'✅ 可以' if result.get('can_release') else '❌ 不可以'}\n"

    if result.get("can_release"):
        md += "所有缺陷已修复，无新引入缺陷，业务验收标准全部仍然满足。可以进入下一阶段。\n"
    else:
        verdict = result.get("verdict", "")
        if verdict == "business_regression":
            md += "🔴 **业务回归**：修复破坏了业务验收标准。必须回滚或重新设计修复方案。\n"
        elif verdict == "new_defects_introduced":
            md += "🚨 引入了新缺陷。需修新缺陷 + 继续修残留→再 delta 审（最多 2 轮）。\n"
        elif verdict == "partially_fixed":
            md += "⚠️ 部分缺陷还在。需继续修→再 delta 审（最多 2 轮）。\n"
        else:
            md += "还有未修复缺陷或引入了新缺陷。需继续修→再 delta 审（最多 2 轮）。\n"

    path.write_text(md, encoding="utf-8")
    return str(path)
