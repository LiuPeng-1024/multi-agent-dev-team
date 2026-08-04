"""review_engine.memory — 结构化免疫记忆

替代纯文本 immune_memory.md，用 JSON 结构化存储：
- global: 跨项目通用"已确认非 bug"模式
- <project_name>: 项目特定 ADR / 业务设计

支持按项目加载、追加、查询。注入 prompt 时格式化为文本。
"""
import json
import os
from pathlib import Path

# 存储路径可用环境变量 IMMUNE_MEMORY_FILE 覆盖
MEMORY_FILE = Path(os.environ.get("IMMUNE_MEMORY_FILE", str(Path.home() / ".llm_review" / "immune_memory.json")))


def load_memory(project=None):
    """加载免疫记忆，返回格式化为文本的字符串（注入 prompt 用）。

    参数:
        project: str|None — 项目名。传则返回 global + 该项目；
                 不传则只返回 global。

    返回:
        str — 格式化文本，直接拼到 prompt 的 immune_memory 位置
    """
    data = _read_file()
    if not data:
        return ""

    lines = []

    # 全局通用
    global_items = data.get("global", [])
    if global_items:
        lines.append("【跨项目通用——已确认非 bug】")
        for item in global_items:
            lines.append(f"- {item.get('pattern', '?')}: {item.get('reason', '?')}")

    # 项目特定
    if project and project in data:
        proj_items = data[project]
        if proj_items:
            lines.append(f"\n【{project} 项目特定——已确认非 bug】")
            for item in proj_items:
                adr = item.get("adr", "")
                adr_str = f" [{adr}]" if adr else ""
                lines.append(f"- {item.get('pattern', '?')}: {item.get('reason', '?')}{adr_str}")

    return "\n".join(lines) if lines else ""


def add_entry(pattern, reason, project=None, adr=""):
    """追加一条免疫记忆。

    参数:
        pattern: str — 误导信号（模型容易误判为 bug 的模式）
        reason: str — 真实原因（为什么不是 bug）
        project: str|None — 项目名。None=全局通用
        adr: str — 关联 ADR 编号（如 "ADR-003"）
    """
    data = _read_file()

    entry = {"pattern": pattern, "reason": reason}
    if adr:
        entry["adr"] = adr

    if project is None:
        data.setdefault("global", []).append(entry)
    else:
        data.setdefault(project, []).append(entry)

    _write_file(data)


def list_projects():
    """列出所有有项目特定记忆的项目名"""
    data = _read_file()
    return [k for k in data.keys() if k != "global"]


def _read_file():
    """读 JSON 文件"""
    if not MEMORY_FILE.exists():
        return _default_memory()
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _default_memory()


def _write_file(data):
    """写 JSON 文件"""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _default_memory():
    """初始化默认记忆（从 immune_memory.md 迁移的内容）"""
    return {
        "global": [
            {
                "pattern": "NaN 不显式处理",
                "reason": "Rust 中 NaN 比较返回 false 是标准行为；业务接受 NaN=不通过",
            },
            {
                "pattern": ".unwrap_or_default() 静默吞错",
                "reason": "业务允许：解析失败==无数据，下游已处理空值",
            },
            {
                "pattern": "字符串做枚举键",
                "reason": "一人维护项目，依赖最小化，枚举增加复杂度不值得",
            },
            {
                "pattern": "失败不自动重试",
                "reason": "防双写/防重复发文——自动重试会导致重复创建",
            },
            {
                "pattern": "Mutex::lock().unwrap() 不处理中毒",
                "reason": "业务可接受：Mutex 中毒=线程 panic，进程就该挂",
            },
            {
                "pattern": "测试硬编码绝对路径",
                "reason": "一人开发机，CI 不存在；是技术债不是 bug",
            },
            {
                "pattern": "幂等性优先",
                "reason": "纯函数+同输入同输出是设计目标，不是巧合正确",
            },
            {
                "pattern": "门禁由离线验证兜底",
                "reason": "模型说通过不算数，cargo test/vite build 真跑过才算",
            },
        ],
        # 示例：项目特定记忆按项目名分桶（替换成你的项目与条目）
        "your-project": [
            {
                "pattern": "<模型容易误判为 bug 的写法>",
                "reason": "<为什么这是业务需求/有意设计>",
                "adr": "ADR-001",
            },
        ],
    }
