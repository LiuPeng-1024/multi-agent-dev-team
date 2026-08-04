"""review_engine.client — 统一 LLM 模型调用层

从 config 中获取代理地址和 API key，不硬编码。
"""
import time
import requests
from .config import load_config, resolve_key, resolve_url


def call_model(model, prompt, max_tokens=None, temperature=None,
               timeout=None, config=None, retries=2):
    """调用指定模型，返回 (text, error, meta)

    参数:
        model: str — 模型名（如 kimi-k2.7-code）
        prompt: str — 完整 prompt（含 system 指令）
        max_tokens: int — 输出最大 token 数
        temperature: float — 生成温度
        timeout: int — 单次超时秒数
        config: dict — 缺省从 load_config() 读
        retries: int — 失败重试次数（指数退避）

    返回:
        (text: str|None, error: str|None, meta: dict)
    """
    if config is None:
        config = load_config()

    url = resolve_url(config)
    api_key = resolve_key(config)
    defaults = config.get("review_defaults", {})

    if max_tokens is None:
        # 不再兜底 3000；config 没配就让 max_tokens 保持 None，
        # payload 不会包含 max_tokens 字段，模型用自己默认上限（探测稳定 29K+ tokens）
        max_tokens = defaults.get("max_tokens")  # None if not set
    if temperature is None:
        temperature = defaults.get("temperature", 0.1)
    if timeout is None:
        timeout = defaults.get("timeout", 480)

    if not api_key:
        return None, "API key 未配置（检查 ~/.zcode/llm_proxy.yaml key 引用是否正确）", {"ms": -1, "status": "no_key"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    # 只有显式有 max_tokens 才传给 API，让模型用默认上限更稳（避免 reasoning_tokens 吃满配额）
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    last_err = None
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            ms = int((time.time() - t0) * 1000)

            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                return None, last_err, {"ms": ms, "status": r.status_code}

            data = r.json()
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", "?")
            return content, None, {"ms": ms, "status": 200, "tokens": tokens}

        except requests.exceptions.Timeout:
            last_err = f"timeout ({timeout}s)"
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return None, last_err, {"ms": timeout * 1000, "status": "timeout"}

        except requests.exceptions.ConnectionError as e:
            last_err = f"连接失败: {str(e)[:100]}"
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return None, last_err, {"ms": -1, "status": "conn_err"}

        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:150]}"
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return None, last_err, {"ms": -1, "status": "error"}

    return None, last_err, {"ms": -1, "status": "exhausted"}
