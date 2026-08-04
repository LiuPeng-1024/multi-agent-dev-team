"""review_engine — 多模型流水线审查引擎

可被任何项目 import 使用。配置全局共享：
- 代理/模型: ~/.zcode/llm_proxy.yaml
- API Key: 由 LLM 代理配置 YAML 的 key_file + key_jsonpath 指定（不内置任何真实密钥）
- 免疫记忆: ~/.zcode/llm_tools/immune_memory.json

核心入口:
  council_review(code, file_path, code_type, models, ...)  → dict  双模型审+仲裁
  single_review(code, model, code_type, ...)                → dict  单模型快速审
  delta_review(code, file_path, previous_defects, ...)      → dict  修复闭环审
  verify_completion(project_root, test_cmd, ...)            → dict  完成声明验证
  check_health(models)                                       → list  连接性拨测
  load_memory(project)                                       → str   加载免疫记忆
  add_entry(pattern, reason, project, adr)                   → None  追加免疫记忆
"""
from .config import load_config, resolve_key
from .client import call_model
from .parser import parse_review
from .merge import merge_defects, arbitrate
from .report import report_to_md, write_report
from .prompts import RUST_REVIEW, REACT_REVIEW, ARCHITECTURE_REVIEW, ARBITER
from .verify import verify_completion, verify_preset
from .delta import delta_review
from .memory import load_memory, add_entry, list_projects

__all__ = [
    "council_review", "single_review", "delta_review",
    "verify_completion", "verify_preset",
    "check_health", "load_memory", "add_entry", "list_projects",
    "load_config", "resolve_key", "call_model", "parse_review",
    "merge_defects", "arbitrate", "report_to_md", "write_report",
]

__version__ = "0.1.0"


def council_review(code, file_path, code_type="rust", models=None,
                   context="", output_dir="reports", aborter="qwen3.8-max",
                   config=None, immune_memory=""):
    """双模型独立审查 → 合并缺陷 → 分歧大则仲裁 → 写入报告

    参数:
        code: str — 被审代码全文
        file_path: str — 用于报告标注
        code_type: str — rust / react / architecture
        models: tuple[str,str] — (模型A, 模型B)，缺省从配置取
        context: str — 业务上下文说明（ADR/需求等），注入 prompt
        immune_memory: str — 已确认非 bug 清单，前置注入 prompt 防误报
        output_dir: str — 报告写目录（自动建）
        aborter: str — 仲裁模型名
        config: dict — 缺省从 load_config() 读

    返回:
        dict — {merged_defects, model_a_review, model_b_review, report_path, ...}
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path
    from datetime import datetime
    from .prompts import build_prompt

    if config is None:
        config = load_config()
    if models is None:
        # 从配置取 code_reviewer + architecture_reviewer
        models_cfg = config.get("models", {})
        a = models_cfg.get("code_reviewer", {}).get("model", "kimi-k2.7-code")
        b = models_cfg.get("architecture_reviewer", {}).get("model", "deepseek-v4-pro")
        models = (a, b)

    prompt_template = _pick_template(code_type)
    prompt = build_prompt(prompt_template, code, file_path, context, immune_memory)

    results = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(call_model, m, prompt, config=config): m for m in models}
        for f in as_completed(futures):
            m = futures[f]
            text, err, meta = f.result()
            results[m] = (text, err, meta)

    # 解析
    reviews = {}
    for m in models:
        text, err, meta = results[m]
        review = parse_review(text)
        if err:
            review["_error"] = err
        review["_meta"] = meta
        reviews[m] = review

    # 合并
    a_defects = reviews[models[0]].get("defects", [])
    b_defects = reviews[models[1]].get("defects", [])
    merged = merge_defects(a_defects, b_defects)

    # 仲裁
    score_a = reviews[models[0]].get("score", 0)
    score_b = reviews[models[1]].get("score", 0)
    arbiter_result = None
    threshold = config.get("review_defaults", {}).get("arbitration_threshold", 1.5)
    if abs(score_a - score_b) >= threshold:
        arbiter_result = arbitrate(
            code, file_path, context,
            models[0], json.dumps(reviews[models[0]], ensure_ascii=False),
            models[1], json.dumps(reviews[models[1]], ensure_ascii=False),
            arbiter=aborter, config=config,
        )

    # 写入报告
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(output_dir) / f"{now}_{Path(file_path).name}_council.md"
    md = report_to_md(code, file_path, models, reviews, merged,
                      arbiter_result, context, now)
    write_report(md, report_path)

    return {
        "merged_defects": merged,
        "model_a_review": reviews[models[0]],
        "model_b_review": reviews[models[1]],
        "arbiter_result": arbiter_result,
        "report_path": str(report_path),
        "models": list(models),
    }


def single_review(code, file_path="", code_type="rust", model=None,
                  context="", config=None):
    """单模型快速审查（自检用）"""
    if config is None:
        config = load_config()
    if model is None:
        model = config["review_defaults"]["primary_model"]
    prompt_template = _pick_template(code_type)
    prompt = prompt_template.format(code=code, file_path=file_path, context=context)
    text, err, meta = call_model(model, prompt, config=config)
    review = parse_review(text)
    if err:
        review["_error"] = err
    review["_meta"] = meta
    return review


def check_health(models=None, config=None):
    """模型连接性拨测: 每个模型发 PONG → 收响应 """
    if config is None:
        config = load_config()
    if models is None:
        # 从配置的 models 区块提取所有 model 字段值（跳过 primary 日常用模型）
        all_models = []
        for role, info in config.get("models", {}).items():
            if role == "primary":
                continue
            if isinstance(info, dict) and "model" in info:
                all_models.append(info["model"])
        models = all_models if all_models else ["kimi-k2.7-code", "deepseek-v4-pro", "qwen3.8-max"]

    results = []
    for m in models:
        # max_tokens=10 是 PONG 探活用，固定小值即可（非思考任务不会触发 reasoning_tokens 吃满）
        text, err, meta = call_model(m, "只回复 PONG 一个词",
                                     max_tokens=10, config=config)
        results.append({
            "model": m,
            "ok": text is not None,
            "ms": meta.get("ms", -1),
            "status": meta.get("status", "error"),
            "error": err[:80] if err else None,
        })
    return results


# ─── 内部辅助 ───

import json

def _pick_template(code_type):
    if code_type == "rust":
        return RUST_REVIEW
    elif code_type == "react":
        return REACT_REVIEW
    elif code_type == "architecture":
        return ARCHITECTURE_REVIEW
    else:
        raise ValueError(f"未知 code_type: {code_type}")
