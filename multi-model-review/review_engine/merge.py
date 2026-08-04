"""review_engine.merge — 缺陷合并 + 仲裁

- merge_defects: 并集去重（按 severity + category + issue 摘要），追踪来源
- arbitrate: 分歧大时调第三模型仲裁
"""
import json
import hashlib

from .client import call_model
from .parser import parse_review
from .prompts import ARBITER, build_prompt


def merge_defects(a, b, model_a_label="", model_b_label=""):
    """合并两份缺陷列表，按 (severity, category, issue 摘要) 去重，追踪来源。

    返回:
        list[dict] — 按 severity 排序（blocker < critical < warning）
        每条多一个 _sources 字段记录来自哪个模型
    """
    seen = {}
    rank = {"blocker": 0, "critical": 1, "warning": 2}

    for d in list(a) + list(b):
        if not isinstance(d, dict):
            continue
        key = (
            d.get("severity", "warning"),
            d.get("category", "uncategorized"),
            hashlib.md5(str(d.get("issue", "")).encode("utf-8")).hexdigest()[:8],
        )
        if key not in seen:
            # 复制并初始化 _sources
            d_copy = dict(d)
            d_copy["_sources"] = []
            seen[key] = d_copy
        # 记录来源（通过 issue 文本匹配回原列表判断）
        issue_text = str(d.get("issue", ""))
        if issue_text in [str(x.get("issue", "")) for x in a]:
            if model_a_label and model_a_label not in seen[key]["_sources"]:
                seen[key]["_sources"].append(model_a_label)
        if issue_text in [str(x.get("issue", "")) for x in b]:
            if model_b_label and model_b_label not in seen[key]["_sources"]:
                seen[key]["_sources"].append(model_b_label)

    merged = list(seen.values())
    merged.sort(key=lambda x: rank.get(x.get("severity", "warning"), 9))
    return merged


def arbitrate(code, file_path, context,
              model_a, review_a_json, model_b, review_b_json,
              arbiter="qwen3.8-max", config=None, immune_memory=""):
    """调第三模型仲裁两份审查报告。

    参数:
        code: str — 代码全文（仲裁者需要看）
        file_path: str
        context: str — 业务上下文/ADR
        model_a/review_a_json: 模型 A 名称和 JSON 报告
        model_b/review_b_json: 模型 B 名称和 JSON 报告
        arbiter: str — 仲裁模型名
        config: dict — 缺省从 load_config()
        immune_memory: str — 已确认非 bug 清单

    返回:
        dict — 仲裁结果，含 final_score/verdict/merged_defects/blockers
    """
    full_context = context
    if immune_memory:
        full_context = f"【已确认非 bug 清单】\n{immune_memory}\n\n{context}"

    prompt = ARBITER.format(
        context=full_context,
        file_path=file_path,
        model_a=model_a,
        review_a=review_a_json,
        model_b=model_b,
        review_b=review_b_json,
    )

    # 仲裁 max_tokens 策略：从 config 读，未配时为 None，client.py 不会向 payload 传该字段
    # 让模型用自己默认上限（探测证据在 qwen3.7-max：不设时稳定输出，设小则 reasoning_tokens 吃满空回复；
    # qwen3.8-max 沿用该策略，待复测确认）
    # 2026-07-21 修复：原写死 max_tokens=3000，思考型模型(qwen)的
    # reasoning_tokens 会吃满 3000 导致正文空回复。改为读 config 全局配置。
    arbiter_max = config.get("review_defaults", {}).get("max_tokens")
    text, err, meta = call_model(arbiter, prompt, max_tokens=arbiter_max, config=config)
    if err:
        return {"error": err, "_meta": meta}

    result = parse_review(text)
    # 仲裁可能有额外字段
    try:
        full = json.loads(text)
        if isinstance(full, dict):
            result.update({
                "final_score": full.get("final_score"),
                "verdict": full.get("verdict"),
                "blockers": full.get("blockers", []),
                "consensus_defects": full.get("consensus_defects", []),
                "divergent_defects": full.get("divergent_defects", []),
            })
    except json.JSONDecodeError:
        pass

    result["_meta"] = meta
    return result
