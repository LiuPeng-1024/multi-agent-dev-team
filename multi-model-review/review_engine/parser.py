"""review_engine.parser — 模型回复解析

多 fallback JSON 解析：
1. 直接 json.loads
2. markdown ```json ... ``` 代码块提取
3. markdown ``` ... ``` 代码块提取
4. 正则找含 score 的 JSON 对象
5. 截断补救（追加闭合符）
"""
import json
import re


def parse_review(raw):
    """从模型回复解析 JSON 审查报告。

    返回:
        dict — {score, passed, critique, defects: []}
        失败时返回 {score:0, passed:False, critique:"...", defects:[], _raw:...}
    """
    if not raw:
        return {"score": 0, "passed": False, "critique": "空回复", "defects": []}

    # 1. 直接解析
    try:
        return _normalize(json.loads(raw))
    except json.JSONDecodeError:
        pass

    # 2. markdown json 代码块
    for pat in [r'```json\s*\n(.*?)\n\s*```', r'```\s*\n(.*?)\n\s*```']:
        m = re.search(pat, raw, re.DOTALL)
        if m:
            try:
                return _normalize(json.loads(m.group(1)))
            except json.JSONDecodeError:
                pass

    # 3. 含 "score" 的 JSON 对象（两种字段顺序）
    for pat in [
        r'\{[^{}]*"score"\s*:\s*\d+[^{}]*"passed"\s*:\s*(?:true|false)[^{}]*\}',
        r'\{[^{}]*"passed"\s*:\s*(?:true|false)[^{}]*"score"\s*:\s*\d+[^{}]*\}',
    ]:
        m = re.search(pat, raw, re.DOTALL)
        if m:
            try:
                return _normalize(json.loads(m.group(0)))
            except json.JSONDecodeError:
                pass

    # 4. 截断补救：起始 { 但没闭合
    salvage = raw.strip()
    if salvage.startswith("{") and not salvage.endswith("}"):
        for close in ['"}]}', '"]}', '"}', "}"]:
            try:
                return _normalize(json.loads(salvage + close))
            except json.JSONDecodeError:
                continue

    return {
        "score": 0, "passed": False,
        "critique": "解析失败", "defects": [],
        "_raw": raw[:300],
    }


def _normalize(data):
    """标准化解析后的 dict，确保关键字段存在"""
    if not isinstance(data, dict):
        return {"score": 0, "passed": False, "critique": "非对象", "defects": []}

    # 兼容字段名 issues ↔ defects
    defects = data.get("defects") or data.get("issues") or []
    if not isinstance(defects, list):
        defects = []

    # 标准化每条 defect 的字段
    normalized = []
    for d in defects:
        if not isinstance(d, dict):
            continue
        # 兼容字段名
        item = {
            "severity": d.get("severity", "warning"),
            "category": d.get("category", "uncategorized"),
            "line": str(d.get("line", d.get("location", ""))),
            "issue": d.get("issue", d.get("description", "")),
            "fix": d.get("fix", d.get("suggestion", "")),
            "business_check": d.get("business_check", "pending"),
            "business_ref": d.get("business_ref", ""),
        }
        normalized.append(item)

    return {
        "score": data.get("score", 0),
        "passed": data.get("passed", False),
        "critique": data.get("critique", data.get("summary", "")),
        "defects": normalized,
    }
