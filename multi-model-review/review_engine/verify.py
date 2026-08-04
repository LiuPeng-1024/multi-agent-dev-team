"""review_engine.verify — 完成声明验证（第①层：执行守护）

防"说完成≠真完成"：模型/04开发者说"完成"时，自动真跑测试+构建。
测试不过=没完成=打回，不信任何口头声明。
"""
import subprocess
import time
from pathlib import Path


def verify_completion(project_root, test_cmd, build_cmd=None,
                      test_timeout=300, build_timeout=120):
    """04 说"完成"时调用——真跑测试和构建，不信模型声明。

    参数:
        project_root: str — 项目根目录（命令在此执行）
        test_cmd: str|list — 测试命令（如 "npm test" / "cargo test" / "pytest"）
        build_cmd: str|list|None — 构建命令（如 "npx vite build"），可选
        test_timeout: int — 测试超时秒数
        build_timeout: int — 构建超时秒数

    返回:
        dict — {
            passed: bool,           # 全部通过=True
            test: {passed, ms, output_tail},
            build: {passed, ms, output_tail}|None,
            reason: str,            # 失败原因
        }
    """
    root = Path(project_root).resolve()
    result = {
        "passed": False,
        "test": None,
        "build": None,
        "reason": "",
    }

    # 1. 跑测试
    test_result = _run_cmd(test_cmd, root, test_timeout)
    result["test"] = test_result

    if not test_result["passed"]:
        result["reason"] = f"测试未通过（退出码 {test_result['returncode']}）"
        return result

    # 2. 跑构建（如有）
    if build_cmd:
        build_result = _run_cmd(build_cmd, root, build_timeout)
        result["build"] = build_result

        if not build_result["passed"]:
            result["reason"] = f"构建未通过（退出码 {build_result['returncode']}）"
            return result

    result["passed"] = True
    result["reason"] = "测试+构建均通过"
    return result


def _run_cmd(cmd, cwd, timeout):
    """执行命令，返回结果 dict"""
    if isinstance(cmd, str):
        # 字符串命令用 shell=True
        shell = True
    else:
        shell = False

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), shell=shell,
            capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        ms = int((time.time() - t0) * 1000)
        output = (proc.stdout or "") + (proc.stderr or "")
        return {
            "passed": proc.returncode == 0,
            "returncode": proc.returncode,
            "ms": ms,
            "output_tail": output[-500:] if len(output) > 500 else output,
        }
    except subprocess.TimeoutExpired:
        ms = int((time.time() - t0) * 1000)
        return {
            "passed": False,
            "returncode": -1,
            "ms": ms,
            "output_tail": f"超时（{timeout}s）",
        }
    except Exception as e:
        return {
            "passed": False,
            "returncode": -1,
            "ms": -1,
            "output_tail": f"{type(e).__name__}: {str(e)[:200]}",
        }


# ============================================================
# 预设：常见技术栈的验证命令
# ============================================================
PRESETS = {
    "rust": {
        "test_cmd": "cargo test",
        "build_cmd": "cargo check",
    },
    "node": {
        "test_cmd": "npm test",
        "build_cmd": "npx vite build",
    },
    "python": {
        "test_cmd": "pytest",
        "build_cmd": None,
    },
    "tauri": {
        "test_cmd": "cd src-tauri && cargo test",
        "build_cmd": "npx vite build",
    },
}


def verify_preset(project_root, preset_name):
    """用预设命令验证（rust/node/python/tauri）"""
    if preset_name not in PRESETS:
        return {"passed": False, "reason": f"未知 preset: {preset_name}"}
    p = PRESETS[preset_name]
    return verify_completion(
        project_root=project_root,
        test_cmd=p["test_cmd"],
        build_cmd=p["build_cmd"],
    )
