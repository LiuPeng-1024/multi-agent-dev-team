"""review_engine.report — 审查报告生成与归档

把审查结果格式化为 markdown，写入指定目录。
"""
import json
from pathlib import Path
from datetime import datetime


def report_to_md(code, file_path, models, reviews, merged_defects,
                 arbiter_result, context, timestamp):
    """把一轮 council_review 的结果格式化为 markdown 报告。

    参数:
        code: str — 被审代码（只用于报告头部摘要，不全文写入）
        file_path: str
        models: tuple/list[str] — 参与的模型名
        reviews: dict[str, dict] — 每个模型的审查结果
        merged_defects: list[dict]
        arbiter_result: dict|None
        context: str
        timestamp: str — 报告时间戳

    返回:
        str — markdown 文本
    """
    lines = []
    lines.append(f"# 多模型审查报告")
    lines.append("")
    lines.append(f"**日期**: {timestamp}")
    lines.append(f"**文件**: `{file_path}`")
    lines.append(f"**模型**: {', '.join(models)}")
    lines.append(f"**上下文摘要**: {context[:200] if context else '(无)'}")
    lines.append("")

    # 各模型审查结果
    for model in models:
        review = reviews.get(model, {})
        score = review.get("score", "?")
        critique = review.get("critique", "(无)")
        defects = review.get("defects", [])
        meta = review.get("_meta", {})
        err = review.get("_error", "")

        lines.append(f"## {model}")
        lines.append(f"- 评分: {score}/10")
        lines.append(f"- 耗时: {meta.get('ms', '?')}ms")
        if err:
            lines.append(f"- ❌ 错误: {err[:150]}")
        lines.append(f"- 评价: {critique}")
        lines.append(f"- 缺陷数: {len(defects)}")
        lines.append("")
        if defects:
            for d in defects:
                sev = d.get("severity", "?")
                line = d.get("line", "?")
                issue = d.get("issue", "")
                lines.append(f"  - **[{sev}]** L{line} {issue}")
            lines.append("")

    # 合并缺陷
    lines.append(f"## 合并缺陷 ({len(merged_defects)} 条)")
    lines.append("")
    sev_count = {}
    for d in merged_defects:
        s = d.get("severity", "warning")
        sev_count[s] = sev_count.get(s, 0) + 1
    if sev_count:
        lines.append(f"严重度分布: {sev_count}")
        lines.append("")

    for i, d in enumerate(merged_defects, 1):
        sev = d.get("severity", "?")
        cat = d.get("category", "?")
        line = d.get("line", "?")
        issue = d.get("issue", "")
        fix = d.get("fix", "")
        biz = d.get("business_check", "pending")
        biz_ref = d.get("business_ref", "")
        sources = d.get("_sources", [])

        lines.append(f"### {i}. **[{sev}]** {cat} L{line}")
        lines.append(f"- **问题**: {issue}")
        if fix:
            lines.append(f"- **修复方向**: {fix}")
        lines.append(f"- **业务验证**: {biz}")
        if biz_ref:
            lines.append(f"- **业务参考**: {biz_ref}")
        if sources:
            lines.append(f"- **来源**: {', '.join(sources)}")
        lines.append("")

    # 仲裁结果
    if arbiter_result:
        lines.append("## 仲裁结果")
        lines.append("")
        if arbiter_result.get("error"):
            lines.append(f"❌ 仲裁失败: {arbiter_result['error'][:150]}")
        else:
            lines.append(f"- 最终评分: {arbiter_result.get('final_score', '?')}/10")
            lines.append(f"- 裁决: {arbiter_result.get('verdict', '?')}")
            blockers = arbiter_result.get("blockers", [])
            if blockers:
                lines.append(f"- Blockers ({len(blockers)}):")
                for b in blockers:
                    lines.append(f"  - {b}")
        lines.append("")

    # 业务需求验证待办
    lines.append("## 业务需求验证待办")
    lines.append("")
    pending = [d for d in merged_defects
               if d.get("severity") in ("blocker", "critical")
               and d.get("business_check") in ("pending", "")]
    if pending:
        lines.append("以下 blocker/critical 缺陷在修改前需对照 SSOT 核实：")
        lines.append("")
        for d in pending:
            lines.append(f"- [ ] L{d.get('line','?')} {d.get('issue','')[:80]}")
    else:
        lines.append("✅ 所有 blocker/critical 缺陷已标 business_check。")
    lines.append("")

    # 审查结论
    lines.append("## 审查结论")
    lines.append("")
    lines.append(f"合并缺陷 {len(merged_defects)} 条。")
    lines.append("所有 blocker/critical 缺陷必须经业务需求验证后方可修改。")
    lines.append("")

    return "\n".join(lines)


def write_report(markdown_text, report_path):
    """把 markdown 报告写入文件（自动建父目录）。

    参数:
        markdown_text: str
        report_path: str|Path
    """
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_text, encoding="utf-8")
    return str(path)
