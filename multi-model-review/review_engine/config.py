"""review_engine.config — 全局配置读取

读取链路：config() → 读 LLM 代理配置 YAML（默认 ~/.zcode/llm_proxy.yaml，可用环境变量 LLM_PROXY_CONFIG 覆盖）→ 读 key_file + key_jsonpath → 取 api_key。
所有端点/密钥均不内置真实值，需自行配置。
"""
import os
import json
from pathlib import Path

# 默认全局配置路径（均可用环境变量覆盖）
DEFAULT_PROXY_CONFIG = Path(os.environ.get("LLM_PROXY_CONFIG", str(Path.home() / ".zcode" / "llm_proxy.yaml")))
DEFAULT_KEY_FILE = Path(os.environ.get("LLM_KEY_FILE", str(Path.home() / ".llm_proxy_keys.json")))
# 代理端点兜底值（YAML 未配 url 时用）——示例地址，请改成你自己的 OpenAI 兼容代理
DEFAULT_PROXY_URL = os.environ.get("LLM_PROXY_URL", "http://localhost:8000/v1")


def load_config(proxy_path=None):
    """读取全局 LLM 代理配置（YAML）+ 解析 key 引用。返回完整配置 dict。"""
    path = Path(proxy_path or DEFAULT_PROXY_CONFIG)

    if not path.exists():
        return _default_config()

    raw = path.read_text(encoding="utf-8")
    cfg = _parse_yaml_like(raw)

    # 解析 key 引用
    proxy = cfg.get("proxy", {})
    key_file = proxy.get("key_file", str(DEFAULT_KEY_FILE))
    key_jsonpath = proxy.get("key_jsonpath", "glm.api_key")

    api_key = _resolve_key(key_file, key_jsonpath)
    cfg["_resolved_api_key"] = api_key
    cfg["_resolved_api_url"] = proxy.get("url", DEFAULT_PROXY_URL) + "/chat/completions"

    # 展开 review_defaults 缺省值
    defaults = cfg.setdefault("review_defaults", {})
    # max_tokens 默认 None：让 client.py 不向 payload 传该字段，
    # 模型用自己默认上限（探测：kimi 29064 / deepseek-pro 29035 / flash 29422 tokens 稳定输出）
    defaults.setdefault("max_tokens", None)
    defaults.setdefault("temperature", 0.1)
    defaults.setdefault("timeout", 480)
    defaults.setdefault("score_threshold", 8.5)
    defaults.setdefault("arbitration_threshold", 1.5)

    return cfg


def resolve_key(config=None):
    """从配置中取出解析后的 api_key（方便调用方直接使用）"""
    if config is None:
        config = load_config()
    return config.get("_resolved_api_key", "")


def resolve_url(config=None):
    """从配置中取出完整 chat/completions URL"""
    if config is None:
        config = load_config()
    return config.get("_resolved_api_url", "")


# ─── 内部辅助 ───


def _parse_yaml_like(text):
    """解析 YAML 配置。

    2026-07-21 修复：原简易解析器不处理缩进回退，嵌套结构（models.code_reviewer.max_tokens）
    会把同级键错塞进上一级 dict，导致 review_defaults 取不到正确值（返回 None 走兜底 3000）。
    改用 PyYAML（已装 6.0.3），保留原函数名避免破坏调用方。
    """
    try:
        import yaml
        parsed = yaml.safe_load(text)
        return parsed if isinstance(parsed, dict) else {}
    except ImportError:
        # PyYAML 不可用时回退到原简易解析（保留兜底）
        return _parse_yaml_like_legacy(text)


def _parse_yaml_like_legacy(text):
    """原简易 YAML 解析（已知 bug：不处理缩进回退，嵌套结构会错乱）。仅作 PyYAML 不可用时的兜底。"""
    result = {}
    current_section = result
    section_path = []

    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue

        # 缩进判定
        indent = len(line) - len(line.lstrip())
        key_val = stripped.split(":", 1)

        if len(key_val) == 2 and key_val[1].strip():
            # 有值的键
            key = key_val[0].strip()
            val = key_val[1].strip()
            # 去除引号
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                val = val[1:-1]

            # 数字转换
            try:
                if "." in val:
                    val = float(val)
                else:
                    val = int(val)
            except ValueError:
                pass

            current_section[key] = val
        elif len(key_val) == 2:
            # 无值=子节点头
            key = key_val[0].strip()
            new_section = {}
            current_section[key] = new_section
            current_section = new_section

    return result


def _resolve_key(key_file, key_jsonpath):
    """从 JSON 文件的指定路径读取 key"""
    path = Path(key_file).expanduser()
    if not path.exists():
        return ""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""

    # 按点分隔路径查找
    parts = key_jsonpath.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return ""
    return str(current) if current else ""


def _default_config():
    """兜底配置（无配置文件时）"""
    return {
        "proxy": {
            "url": DEFAULT_PROXY_URL,
            "key_file": str(DEFAULT_KEY_FILE),
            "key_jsonpath": "glm.api_key",
        },
        "_resolved_api_url": DEFAULT_PROXY_URL + "/chat/completions",
        "_resolved_api_key": "",
        "review_defaults": {
            "max_tokens": None,
            "temperature": 0.1,
            "timeout": 480,
            "score_threshold": 8.5,
            "arbitration_threshold": 1.5,
        },
        "models": {},
    }
