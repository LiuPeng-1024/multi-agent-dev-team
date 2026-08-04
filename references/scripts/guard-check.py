#!/usr/bin/env python3
"""可执行守卫断言:读事实来源文档,核本轮完成声明有无非作者复现证据,
并把幻觉日志的规律标签回流为本轮必查项。

加 --execute: 独立执行区块8.3的"可执行验证规则",用真实退出码/文件存在性
作为非伪造oracle(覆盖回归/覆盖率/类型/lint/工件落盘/可复现缺陷)。
默认不执行(--execute opt-in),只做文档检查。

用法:
  python guard-check.py <PROJECT_CONTEXT.md> [--execute] [--project-dir DIR] [--timeout N]

输出: GUARD PASS 或 GUARD FAIL: <哪条不过>
退出码: 0=PASS, 1=FAIL
"""
import re, sys, os, subprocess, shlex, shutil
from pathlib import Path

WHITELIST_RUNNERS = {"node", "python", "python3", "py", "npm", "npx",
                     "pytest", "jest", "mocha", "tsc"}
FORBIDDEN_METACHARS = set(";&|$`>*<%^")  # 出现任一即拒(防shell链式/重定向/环境变量展开/转义)
FORBIDDEN_FLAGS = {"-e", "--eval", "-c", "-C", "--command"}
DEFAULT_TIMEOUT = 60


def parse_sections(text):
    """按 ## 标题切块,返回 {标题: 内容}。
    同名标题(文档可能有重复)合并内容,不覆盖——取所有同名块拼接。"""
    parts = re.split(r"^##\s+", text, flags=re.M)
    sections = {}
    for p in parts[1:]:
        nl = p.find("\n")
        title = p[:nl].strip()
        body = p[nl + 1:]
        key = re.sub(r"^\d+\.\s*", "", title)
        sections.setdefault(key, []).append(body)
    return {k: "\n".join(v) for k, v in sections.items()}


def check_decl_has_evidence(block4):
    """区块4 任务状态里,标'完成'的任务,有无对应的验证/审查记录。"""
    issues = []
    for line in block4.splitlines():
        if "完成" in line and ("放行" in line or "PASS" in line or "通过" in line or "复现" in line or "✓" in line or "复核" in line):
            continue
        if "完成" in line and "|" in line:
            issues.append("完成任务缺非作者复现证据词: " + line.strip()[:80])
    return issues


def extract_hallucination_tags(block11):
    """从幻觉日志(区块11)提取规律标签。
    定位表头"规律标签"列下标;回退到倒数第二列(关联角色/任务通常在最后)。
    注:旧实现取 cells[-1] 抓的是"关联角色/任务"列,非规律标签——实测在 案例A（某回合制 web 游戏） 暴露。"""
    tags = set()
    tag_idx = -1
    for line in block11.splitlines():
        if line.startswith("|") and "幻觉ID" in line:
            headers = [h.strip() for h in line.split("|")[1:-1]]
            for i, h in enumerate(headers):
                if "规律标签" in h:
                    tag_idx = i
                    break
            break
    for line in block11.splitlines():
        if not line.startswith("|") or "---" in line or "幻觉ID" in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 6:
            idx = tag_idx if 0 <= tag_idx < len(cells) else len(cells) - 2
            if 0 <= idx < len(cells):
                tag = cells[idx]
                if tag and tag not in ("规律标签", "关联角色/任务", "纠正", ""):
                    tags.add(tag)
    for m in re.finditer(r"规律标签[::]\s*([^\n|]+)", block11):
        t = m.group(1).strip()
        if t:
            tags.add(t)
    return tags


def extract_subsection(block, sub_title):
    """从区块正文里抽 ### 子节(如 8.3)。返回子节正文,找不到返''。
    heading 行用 [^\\n]* 不跨行(否则 re.S 下 .* 贪婪吞掉 body),
    body 段用 .*? 跨行直到下一个 ### 或串尾。"""
    pat = re.compile(r"^###\s+" + re.escape(sub_title) + r"(?!\d)[^\n]*\n(.*?)(?=^###\s|\Z)",
                     re.M | re.S)
    m = pat.search(block)
    return m.group(1) if m else ""


def check_p4_checkpoint(block4):
    """区块4.1 任务表:画像为P4(副作用型)的任务必须有检查点记录(副作用门禁,
    见 exception-handling.md handler 1)。返回 (fails, warns)。
    旧实例无画像/检查点列 → warn(不阻断),不 fail(见迁移注记)。"""
    fails, warns = [], []
    if not block4:
        return fails, warns
    sub = extract_subsection(block4, "4.1")
    if not sub:
        return fails, warns  # 无4.1子节,无可查
    # 找表头(含"任务ID"的|行)
    header = None
    for line in sub.splitlines():
        if line.strip().startswith("|") and "任务ID" in line:
            header = line
            break
    if header is None:
        return fails, warns  # 无任务表
    cols = [c.strip() for c in header.split("|")[1:-1]]
    try:
        p_idx = cols.index("画像")
        c_idx = cols.index("检查点")
    except ValueError:
        warns.append("4.1任务表无'画像'或'检查点'列(旧实例)——P4副作用门禁未启用(见 exception-handling.md 迁移注记)")
        return fails, warns
    placeholders = {"", "-", "[...]", "(P4必填)", "(必填)", "待填", "TBD"}
    for line in sub.splitlines():
        if not line.strip().startswith("|"):
            continue
        if "---" in line or "任务ID" in line:
            continue  # 分隔行/表头跳过
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) <= max(p_idx, c_idx):
            continue  # 列数不够,跳过
        if "P4" in cells[p_idx]:
            cp = cells[c_idx]
            if cp in placeholders:
                tid = cells[0] if cells[0] else "?"
                fails.append(f"P4副作用型任务 {tid} 缺检查点(违反副作用门禁,见 exception-handling.md handler 1): 副作用操作须pre-flight建checkpoint(commit/快照id),异常即停+叫人,绝不自动重试")
    return fails, warns


def check_p0_prd_ref(block3):
    """区块3 P0 需求每条须有 'PRD章节:§x' 标注(弱 oracle:验覆盖映射存在,不验内容)。
    无 PRD章节字段或为空的 P0 需求 → fail。但若整个区块3 无任何 PRD章节字段(旧实例)→ 只 warn 不 fail(迁移期)。"""
    fails, warns = [], []
    if not block3:
        return fails, warns
    p0_lines = [l for l in block3.splitlines() if "优先级" in l and "P0" in l and "R-" in l]
    if not p0_lines:
        return fails, warns
    has_any_prd_ref = any("PRD章节" in l for l in p0_lines)
    if not has_any_prd_ref:
        # 旧实例:整个区块3 无 PRD章节 字段 → warn 不 fail
        warns.append("区块3 P0需求无 'PRD章节' 字段(旧实例)——PRD-区块3一致性弱oracle未启用(见模板区块3.1迁移注记)")
        return fails, warns
    # 新实例:有字段,逐条核非空
    for line in p0_lines:
        rid = re.search(r"R-\w+", line)
        rid_s = rid.group(0) if rid else "?"
        if "PRD章节" not in line:
            fails.append(f"P0需求 {rid_s} 缺 PRD章节字段——每条P0须标注对应PRD章节号(见模板区块3.1)")
            continue
        m = re.search(r"PRD章节[:：]\s*\[?([^\]]*)\]?", line)
        val = m.group(1).strip() if m else ""
        if not val or val in ("§x", "§x.x"):
            fails.append(f"P0需求 {rid_s} 的 PRD章节为空——每条P0须标注对应PRD章节号(弱oracle,见模板区块3.1)")
    return fails, warns


def check_ui_interaction_ref(block1, block3, project_dir):
    """区块3 P0 中标 '界面交互:是' 的需求每条须有非空 '交互规约章节:§y' 标注,
    且区块1 声明的交互规约文档(docs/INTERACTION_SPEC.md)须实际落盘(弱 oracle:
    验映射存在+文件落盘,不验内容)。无 '界面交互' 字段(旧实例)→ 只 warn 不 fail(迁移期)。
    所有 P0 都标 '界面交互:否' → 无 UI 需求,不查。返回 (fails, warns)。"""
    fails, warns = [], []
    if not block3:
        return fails, warns
    p0_lines = [l for l in block3.splitlines() if "优先级" in l and "P0" in l and "R-" in l]
    if not p0_lines:
        return fails, warns
    has_any_ui_marker = any("界面交互" in l for l in p0_lines)
    if not has_any_ui_marker:
        # 旧实例:整个区块3 无 '界面交互' 字段 → warn 不 fail
        warns.append("区块3 P0需求无 '界面交互' 字段(旧实例)——交互规约一致性弱oracle未启用(见模板区块3.1)")
        return fails, warns
    ui_lines = [l for l in p0_lines if re.search(r"界面交互[:：]\s*是", l)]
    if not ui_lines:
        # 新实例但所有 P0 都标 '界面交互:否' → 无 UI 需求,无需交互规约
        return fails, warns
    # (a) 区块1 须声明 INTERACTION_SPEC.md 且落盘(弱 exists,不执行命令)
    spec_path = None
    if block1:
        m = re.search(r"([\w/.\-]*INTERACTION_SPEC\.md)", block1)
        spec_path = m.group(1) if m else None
    if not spec_path:
        fails.append("区块1 未声明交互规约文档路径(INTERACTION_SPEC.md)——有 '界面交互:是' 的 P0 需求但无规约落点")
    elif not os.path.exists(os.path.join(project_dir, spec_path)):
        fails.append(f"交互规约文档缺失: {spec_path}(区块1声明但未落盘)——'界面交互:是' 的 P0 须有对应 INTERACTION_SPEC.md")
    # (b) 每条 '界面交互:是' 的 P0 须有非空 '交互规约章节'(弱 contains,验字段非空)
    for line in ui_lines:
        rid = re.search(r"R-\w+", line)
        rid_s = rid.group(0) if rid else "?"
        if "交互规约章节" not in line:
            fails.append(f"P0需求 {rid_s} 标 '界面交互:是' 但缺 '交互规约章节' 字段——UI触及的P0须标注对应交互规约章节号(见模板区块3.1)")
            continue
        m = re.search(r"交互规约章节[:：]\s*\[?([^\]]*)\]?", line)
        val = m.group(1).strip() if m else ""
        if not val or val in ("§y", "§y.y"):
            fails.append(f"P0需求 {rid_s} 标 '界面交互:是' 但 '交互规约章节' 为空——UI触及的P0须标注对应交互规约章节号(弱oracle,见模板区块3.1)")
    return fails, warns


def check_p0_assumptions(block3):
    """区块3 每个 P0 需求须有 ≥1 条 '假设' 子条目(弱 oracle:验存在,不验内容/验证状态)。
    无 '假设' 字段(旧实例,所有 P0 都无)→ 只 warn 不 fail(迁移期)。
    块级解析:P0 头(优先级+P0+R-)→ 收集到下一个 ####/###/## 头 → body 含'假设'。返回 (fails, warns)。"""
    fails, warns = [], []
    if not block3:
        return fails, warns
    lines = block3.splitlines()
    p0_header_idx = [i for i, l in enumerate(lines)
                     if "优先级" in l and "P0" in l and "R-" in l]
    if not p0_header_idx:
        return fails, warns
    blocks_with = 0
    blocks_without = []
    for k, idx in enumerate(p0_header_idx):
        end = p0_header_idx[k + 1] if k + 1 < len(p0_header_idx) else len(lines)
        body = []
        for j in range(idx + 1, end):
            l = lines[j]
            if re.match(r"^#{2,4}\s", l):
                break
            body.append(l)
        rid = re.search(r"R-\w+", lines[idx])
        rid_s = rid.group(0) if rid else "?"
        if "假设" in "\n".join(body):
            blocks_with += 1
        else:
            blocks_without.append(rid_s)
    if blocks_with == 0:
        # 区分旧实例(连 PRD章节/界面交互 都没有) vs 新实例漏写假设
        has_new_era = any("PRD章节" in lines[i] or "界面交互" in lines[i] for i in p0_header_idx)
        if has_new_era:
            # 新实例但所有 P0 都漏了 假设 → fail(不是迁移期)
            for idx in p0_header_idx:
                rid = re.search(r"R-\w+", lines[idx])
                rid_s = rid.group(0) if rid else "?"
                fails.append(f"P0需求 {rid_s} 缺 '假设' 子条目——每条P0须列依赖假设(带 已验证/未验证,见模板区块3.1;guard-check检查8)")
        else:
            # 旧实例:连 PRD章节/界面交互 都没有 → warn 不 fail(迁移期)
            warns.append("区块3 P0需求无 '假设' 子条目(旧实例)——假设清单弱oracle未启用(见模板区块3.1)")
    else:
        for rid_s in blocks_without:
            fails.append(f"P0需求 {rid_s} 缺 '假设' 子条目——每条P0须列依赖假设(带 已验证/未验证,见模板区块3.1;guard-check检查8)")
    return fails, warns


def extract_verify_rules(block8):
    """从区块8的8.3子节解析可执行验证规则表。
    返回 [{id, cmd, kind, substr, blocking}, ...]。
    expected 形如 pass/fail/exists/contains:文本。畸形行跳过。"""
    sub = extract_subsection(block8, "8.3") if block8 else ""
    rules = []
    for line in sub.splitlines():
        if not line.startswith("|") or "---" in line or "规则ID" in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 4:
            continue  # 畸形行跳过
        rid, _what, cmd, expected = cells[0], cells[1], cells[2], cells[3]
        exp = expected.strip().lower()
        blocking = "★" in rid
        if exp.startswith("contains:"):
            kind, substr = "contains", expected.split(":", 1)[1]
        elif exp in ("pass", "fail", "exists"):
            kind, substr = exp, ""
        else:
            kind, substr = "malformed", ""
        rules.append({"id": rid, "cmd": cmd, "kind": kind, "substr": substr,
                      "blocking": blocking})
    return rules


def is_safe_command(cmd):
    """白名单runner + 拒元字符/eval flag。返回(ok, reason)。"""
    if any(ch in cmd for ch in FORBIDDEN_METACHARS):
        return False, "含shell元字符,拒执行"
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return False, "命令解析失败"
    if not argv:
        return False, "空命令"
    if argv[0] not in WHITELIST_RUNNERS:
        return False, f"runner '{argv[0]}' 非白名单"
    for a in argv[1:]:
        if a in FORBIDDEN_FLAGS:
            return False, f"含eval类flag '{a}'"
    return True, ""

COUNCIL_MARKERS = ["council", "council-orchestrate", "council-review", "双模型", "多模型", "Kimi+DeepSeek", "delta_review"]
# 报告路径正则：匹配 reviews/xxx_council.md 或 reviews/xxx_delta.md
import re as _re
REPORT_PATH_PAT = _re.compile(r'(reviews/[^\s`\]]+_(?:council|delta)\.md)', _re.IGNORECASE)

def check_council_review_marker(block4, project_dir=None):
    """检查9: ★多模型审查标记——审查结论须含 council/多模型 标记(强制 council-orchestrate)。
    验证两件事：
      (a) 区块4.2 审查结论文本含 council/双模型/delta_review 字样
      (b) 文本含报告文件路径(reviews/xxx_council.md)，且该文件真实存在(exists 验证)
    旧实例无此标记 → warn(不阻断,迁移期);新实例须含标记+报告路径。
    报告路径不存在 = 看起来跑了但报告没落盘 = 可能没真跑 → fail。"""
    fails = []
    warns = []
    if not block4:
        return fails, warns
    review_text = ""
    if "审查结论" in block4:
        review_text = block4["审查结论"]
    elif "4.2" in block4:
        review_text = str(block4["4.2"])
    if not review_text:
        warns.append("区块4.2 无审查结论——无法检查多模型审查标记(旧实例 warn)")
        return fails, warns

    # (a) 字样检查
    has_marker = any(m.lower() in review_text.lower() for m in COUNCIL_MARKERS)
    if not has_marker:
        warns.append("4.2 审查结论无多模型标记(council/双模型/delta_review)——迁移期 warn,新实例须走 council-orchestrate")

    # (b) 报告路径存在性检查
    path_matches = REPORT_PATH_PAT.findall(review_text)
    if not path_matches:
        warns.append("4.2 审查结论无 council/delta 报告路径——迁移期 warn,新实例须含 reviews/xxx_council.md 路径证明真跑过")
    else:
        from pathlib import Path as _P
        import os as _os
        for rel_path in path_matches:
            # 尝试相对 project_dir + 绝对路径两种
            candidates = []
            if project_dir:
                candidates.append(_P(project_dir) / rel_path)
            candidates.append(_P(rel_path))
            candidates.append(_P.cwd() / rel_path)
            exists = any(c.exists() for c in candidates)
            if not exists:
                fails.append(f"4.2 审查结论含报告路径 {rel_path} 但文件不存在——可能没真跑 review_engine,或报告未归档")

    return fails, warns


def run_verify_rule(rule, project_dir, timeout):
    """执行单条规则,返回(status, detail)。status:
    pass/fail=验证结果; blocked=安全拒绝; norunner=runner缺失;
    timeout=超时; malformed=信号未知。"""
    kind = rule["kind"]
    if kind == "malformed":
        return "malformed", f"期望信号未知: {rule['cmd']}"
    if kind == "exists":
        paths = [p.strip() for p in rule["cmd"].split(",") if p.strip()]
        missing = [p for p in paths
                   if not os.path.exists(os.path.join(project_dir, p))]
        if missing:
            return "fail", "缺失文件: " + ", ".join(missing)
        return "pass", f"全部{len(paths)}个文件存在"
    # pass/fail/contains: 执行命令
    ok, reason = is_safe_command(rule["cmd"])
    if not ok:
        return "blocked", reason
    argv = shlex.split(rule["cmd"])
    # 先用 shutil.which 探 runner 是否存在(Windows 下能找到 .cmd/.bat shim);
    # 否则 shell=False 跑 .cmd 会 FileNotFoundError 误报——npm/jest/pytest 等全是 .cmd。
    if shutil.which(argv[0]) is None:
        return "norunner", f"runner未安装/不在PATH: {argv[0]}"
    try:
        # shell=True: Windows 下 .cmd shim(如 npm/jest/pytest)须经 cmd.exe 才能跑。
        # 安全由 is_safe_command 保证:白名单 runner + 元字符拒(经 shell 的注入向量
        # ;&|><$`%^ 已拒),args 无这些字符,cmd.exe 无法链第二命令。
        r = subprocess.run(rule["cmd"], shell=True, cwd=project_dir,
                           timeout=timeout, capture_output=True, text=True,
                           encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return "norunner", f"runner未安装/不在PATH: {argv[0]}"
    except subprocess.TimeoutExpired:
        return "timeout", f"超时(>{timeout}s)"
    combined = (r.stdout or "") + (r.stderr or "")
    tail = combined[-300:]
    if kind == "pass":
        return ("pass" if r.returncode == 0 else "fail"), f"exit={r.returncode}\n{tail}"
    if kind == "fail":
        return ("pass" if r.returncode != 0 else "fail"), f"exit={r.returncode}(期望≠0)\n{tail}"
    if kind == "contains":
        hit = rule["substr"] in combined
        return ("pass" if hit else "fail"), f"输出含'{rule['substr']}'? {'是' if hit else '否'}\n{tail}"
    return "malformed", ""


def main():
    args = sys.argv[1:]
    if not args:
        print("用法: python guard-check.py <PROJECT_CONTEXT.md> [--execute] [--project-dir DIR] [--timeout N]")
        sys.exit(2)
    do_execute = False
    project_dir = None
    timeout = DEFAULT_TIMEOUT
    doc_path = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--execute":
            do_execute = True
        elif a == "--project-dir":
            i += 1
            project_dir = args[i] if i < len(args) else None
        elif a == "--timeout":
            i += 1
            try:
                timeout = int(args[i]) if i < len(args) else DEFAULT_TIMEOUT
            except (ValueError, IndexError):
                timeout = DEFAULT_TIMEOUT
        elif not a.startswith("--"):
            doc_path = a
        i += 1
    if doc_path is None:
        print("GUARD FAIL: 未指定事实来源文档")
        sys.exit(1)
    path = Path(doc_path)
    if not path.exists():
        print(f"GUARD FAIL: 找不到事实来源文档 {path}")
        sys.exit(1)
    if project_dir is None:
        project_dir = str(path.parent)

    text = path.read_text(encoding="utf-8", errors="ignore")
    sections = parse_sections(text)

    def get(secname):
        for k, v in sections.items():
            if secname in k:
                return v
        return ""

    block4 = get("当前任务状态")
    block11 = get("幻觉日志")

    fails = []
    warns = []

    # 检查1: 完成声明有无非作者复现证据
    if block4:
        fails.extend(check_decl_has_evidence(block4))

    # 检查2: 幻觉规律标签回流为本轮必查项
    tags = extract_hallucination_tags(block11) if block11 else set()

    # 检查3: 有"完成"但区块8空 → 可能没独立验证
    block8 = get("验证与质量状态")
    has_completed = any("完成" in l for l in block4.splitlines()) if block4 else False
    if has_completed and block8 and not re.search(r"PASS|通过|全绿|✓", block8):
        fails.append("有任务完成,但区块8(验证状态)无通过/全绿记录——可能缺独立验证")

    # 检查4: 可执行验证规则(execute-verify原语)
    rules = extract_verify_rules(block8)
    exec_results = []  # 仅 --execute 时填充
    if rules:
        if not do_execute:
            warns.append(f"检测到{len(rules)}条可执行验证规则(区块8.3),但未传--execute——这些claim仍是模型声称,未独立验证")
        else:
            for rule in rules:
                status, detail = run_verify_rule(rule, project_dir, timeout)
                exec_results.append((rule, status, detail))
                first = detail.splitlines()[0] if detail else ""
                if status == "fail" and rule["blocking"]:
                    fails.append(f"必绿规则 {rule['id']} 验证失败: {first}")
                elif status == "fail" and not rule["blocking"]:
                    warns.append(f"规则 {rule['id']} 验证失败(非必绿,不阻断): {first}")
                elif status in ("blocked", "norunner", "timeout", "malformed"):
                    warns.append(f"规则 {rule['id']} 无法验证({status}): {first}")

    # 检查5: P4副作用型任务必须有检查点(副作用门禁,见 exception-handling.md handler 1)
    p4_fails, p4_warns = check_p4_checkpoint(block4)
    fails.extend(p4_fails)
    warns.extend(p4_warns)

    # 检查6: P0需求须有 PRD章节 标注(PRD-区块3一致性弱oracle,见模板区块3.1)
    block3 = get("需求与验收")
    p0_fails, p0_warns = check_p0_prd_ref(block3)
    fails.extend(p0_fails)
    warns.extend(p0_warns)

    # 检查7: '界面交互:是' 的 P0 须有交互规约章节 + 区块1声明的INTERACTION_SPEC.md须落盘(交互规约一致性弱oracle)
    block1 = get("项目身份与意图")
    ui_fails, ui_warns = check_ui_interaction_ref(block1, block3, project_dir)
    fails.extend(ui_fails)
    warns.extend(ui_warns)

    # 检查8: P0 须有 '假设' 子条目(假设清单弱oracle,见模板区块3.1)
    a_fails, a_warns = check_p0_assumptions(block3)
    fails.extend(a_fails)
    warns.extend(a_warns)

    # 检查9: ★多模型审查标记(强制 council-orchestrate,见 collaboration-flow.md 内层循环+退出门禁3)
    council_fails, council_warns = check_council_review_marker(block4)
    fails.extend(council_fails)
    warns.extend(council_warns)

    # 输出
    print("=== 守卫断言检查 ===")
    if tags:
        print("【本轮必查项(从幻觉日志回流)】")
        for t in sorted(tags):
            print(f"  - 必查: {t}")
        print()
    if exec_results:
        print("【可执行验证规则(guard-check --execute 独立执行)】")
        for rule, status, detail in exec_results:
            mark = "✓" if status == "pass" else ("✗" if status == "fail" else "?")
            blk = "★" if rule["blocking"] else " "
            print(f"  {mark}{blk} {rule['id']} [{rule['kind']}] {status}")
            for ln in detail.splitlines():
                print(f"        {ln}")
        print()
    if warns:
        print("【提醒(warn,不阻断)】")
        for w in warns:
            print(f"  - ⚠ {w}")
        print()
    if fails:
        print("GUARD FAIL:")
        for f in fails:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("GUARD PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
