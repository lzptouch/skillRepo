#!/usr/bin/env python3
"""
llm_review.py — 把「用大模型做 UI 合规检查」变成一条命令

两种模式：

1) 离线组装（默认，推荐）
     把 diff + DESIGN.md + COMPONENTS.md + UI-SPEC + lint 结果打包成一个
     review 包，写进 .ui-review/，你把它丢进 Claude Code / Cursor 即可。
     python3 llm_review.py --diff HEAD~1 --bundle

2) 直连 API（需要 key）
     python3 llm_review.py --diff HEAD~1 --call
     环境变量：OPENAI_API_KEY, OPENAI_BASE_URL(可选), OPENAI_MODEL(可选)
     兼容 OpenAI / 智谱 / 通义 / DeepSeek 等 OpenAI 风格接口。

先跑 ui_lint.py，把结果作为事实依据喂给模型 —— 别让模型只凭肉眼读代码。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REVIEW_SYSTEM = """你是一名资深前端架构师，负责审查 AI 生成的前端代码是否符合本项目已建立的设计契约。

你的审查必须基于**事实**（DESIGN.md / COMPONENTS.md / UI-SPEC / lint 输出），
而不是你的个人审美。不要提「可以优化」这类建议，只报三类硬伤：

A. 契约违规：使用了未登记的组件、裸色值、任意间距、自创样式、绕过 design-system
B. 规格缺失：UI-SPEC 的状态矩阵里有、但代码没有实现的分支
C. 正确性缺陷：a11y（焦点管理 / 键盘路径 / ARIA）、绑错字段、可复现的布局问题

输出格式（严格）：
## A. 契约违规
- `文件:行号` 问题 → 改法
## B. 规格缺失
- 状态/字段：现状 → 应补什么
## C. 正确性缺陷
- `文件:行号` 问题 → 改法
## 结论
通过 / 需修改（一句话说明最严重的一条）

如果某一类没有问题，就写「无」。不要编造。
"""


def run(cmd: list[str], cwd: Path) -> str:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=120).stdout
    except Exception as e:
        return f"(执行失败: {e})"


def git_diff(root: Path, target: str, staged: bool) -> str:
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--cached")
    cmd.append(target)
    out = run(cmd, root)
    return out or "(没有 diff，可能已经在 HEAD 上未产生变更)"


def read_if_exists(p: Path, limit: int = 20000) -> str:
    if not p.exists():
        return "(文件不存在)"
    text = p.read_text(encoding="utf-8", errors="ignore")
    return text[:limit] + ("\n...(已截断)" if len(text) > limit else "")


def run_lint(root: Path, scripts_dir: Path) -> str:
    script = scripts_dir / "ui_lint.py"
    if not script.exists():
        return "(未找到 ui_lint.py)"
    return run([sys.executable, str(script), "--root", str(root), "--json"], root)


def build_prompt(root: Path, scripts_dir: Path, args) -> str:
    parts = ["以下是本次改动的完整上下文。\n"]

    if args.spec:
        for s in args.spec:
            parts.append(f"\n===== UI-SPEC: {s} =====\n{read_if_exists(root / s)}\n")
    parts.append(f"\n===== DESIGN.md =====\n{read_if_exists(root / 'DESIGN.md')}\n")
    parts.append(f"\n===== COMPONENTS.md =====\n{read_if_exists(root / 'COMPONENTS.md')}\n")

    lint_out = run_lint(root, scripts_dir)
    parts.append("\n===== ui_lint 结构化输出（事实依据）=====\n")
    parts.append(lint_out[:30000] if lint_out.strip() else "(未产出)")

    parts.append(f"\n===== 代码 diff ({args.diff or 'working tree'}) =====\n")
    parts.append(args.diff_file.read_text(encoding="utf-8", errors="ignore")[:60000]
                 if args.diff_file else git_diff(root, args.diff or "HEAD", args.staged))
    parts.append("\n\n请按 SYSTEM 里定义的格式输出审查结果。")
    return "".join(parts)


def call_llm(prompt: str) -> str:
    import urllib.request

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("缺少 OPENAI_API_KEY；或者不加 --call，用生成的 review 包丢给 IDE 里的 agent。")
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": REVIEW_SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        sys.exit(f"调用失败：{e}")
    return data["choices"][0]["message"]["content"]


def main() -> int:
    ap = argparse.ArgumentParser(description="用大模型做 UI 契约合规审查")
    ap.add_argument("--root", default=".")
    ap.add_argument("--diff", help="git diff 目标，如 HEAD~1；省略则用 HEAD")
    ap.add_argument("--diff-file", type=argparse.FileType("r"), help="直接给 diff 文件")
    ap.add_argument("--staged", action="store_true", help="审查已 staged 的改动")
    ap.add_argument("--spec", nargs="*", default=[], help="额外附带的 UI-SPEC 路径")
    ap.add_argument("--bundle", action="store_true", help="把 review 包写入 .ui-review/")
    ap.add_argument("--call", action="store_true", help="直接调用大模型 API")
    ap.add_argument("--print", dest="print_prompt", action="store_true", help="直接打印 prompt")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    scripts_dir = Path(__file__).resolve().parent
    prompt = build_prompt(root, scripts_dir, args)

    if args.print_prompt:
        print(prompt)
        return 0

    if args.call:
        print(call_llm(prompt))
        return 0

    out_dir = root / ".ui-review"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "review-prompt.md").write_text(prompt, encoding="utf-8")
    (out_dir / "SYSTEM.md").write_text(REVIEW_SYSTEM, encoding="utf-8")

    guide = f"""# UI 合规审查包

生成时间：{__import__('datetime').datetime.now().isoformat(timespec='seconds')}
仓库：{root}

## 怎么用（推荐：离线模式，不用花钱也不用配 key）

在 Claude Code / Cursor 里说：

    请读取 .ui-review/SYSTEM.md 作为你的审查准则，
    然后按 .ui-review/review-prompt.md 里的上下文做审查。

## 或者用命令行直连

    export OPENAI_API_KEY=xxx
    export OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4   # 智谱
    # export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # 通义
    # export OPENAI_BASE_URL=https://api.deepseek.com             # DeepSeek
    export OPENAI_MODEL=glm-4-flash
    python3 {scripts_dir/'llm_review.py'} --call --diff HEAD~1

（不同厂家的 BASE_URL 请以官方文档为准，上面只是格式示意。）
"""
    (out_dir / "README.md").write_text(guide, encoding="utf-8")
    print(f"✅ review 包已生成：{out_dir}")
    print("   把它丢给 IDE 里的 agent，或加 --call 直连大模型。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
