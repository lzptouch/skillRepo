#!/usr/bin/env python3
"""
check_spec_coverage.py — UI-SPEC 状态矩阵覆盖率检查

把 UI-SPEC 里写的「状态矩阵 / 验收标准」和实现代码对起来，
找出「规格写了但代码没做」的部分 —— 这是 LLM 最常偷懒的地方。

用法:
    python3 check_spec_coverage.py specs/ui/UI-SPEC-订单列表页.md --src src
    python3 check_spec_coverage.py specs/ui/*.md --src src --json
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

SOURCE_GLOBS = ["**/*.tsx", "**/*.jsx", "**/*.ts"]
EXCLUDE = ["**/node_modules/**", "**/.next/**", "**/dist/**", "**/build/**"]

HINT_KEYWORDS = {
    "loading": ["loading", "skeleton", "isloading", "ispending", "spinner", "isbusy", "加载中"],
    "empty": ["empty", "nodata", "noresult", "emptystate", "空"],
    "error": ["error", "failed", "failure", "rejected", "tryagain", "onretry", "错误", "失败"],
    "成功": ["success", "toast.success", "成功"],
    "超长": ["truncate", "line-clamp", "ellipsis", "title=", "overflow"],
    "窄屏": ["sm:", "md:", "lg:", "useMediaQuery", "resize", "breakpoint", "mobile"],
    "权限": ["permission", "can(", "rbac", "hasrole", "hasaccess", "authorize", "权限"],
    "禁用": ["disabled", "aria-disabled", "readonly"],
    "选中": ["selected", "checked", "active"],
    "悬停": ["hover:"],
    "焦点": ["focus-visible", "focus:", "outline"],
    "暗色": ["dark:"],
    "部分失败": ["partial", "degrade", "降级"],
    "大数据量": ["total >", "largedata", "virtual", "toomany", "过多"],
}


def spec_primary_word(name: str) -> str:
    match = re.match(r"[A-Za-z]+", name.strip())
    return match.group(0).lower() if match else name.strip()


def parse_checkboxes(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*-\s*\[[ xX]\]\s*(.+)$", text, re.M)]


def extract_spec_sections(text: str) -> tuple[list[str], list[str]]:
    """从 markdown 表格里抽取状态名与验收项。"""
    statuses: list[str] = []
    lines = text.splitlines()
    current_head = ""
    for i, ln in enumerate(lines):
        head = re.match(r"^#{1,4}\s+(.+)$", ln)
        if head:
            current_head = head.group(1)
            continue
        if ln.strip().startswith("|") and ("状态" in current_head or "state" in current_head.lower()):
            cells = [c.strip().strip("`*") for c in ln.strip().strip("|").split("|")]
            if not cells:
                continue
            name = cells[0]
            if not name or set(name) <= set("-: ") or name.lower() in {"状态", "state", "名称"}:
                continue
            statuses.append(name)
    return statuses, parse_checkboxes(text)


def iter_files(root: Path) -> list[Path]:
    out, seen = [], set()
    for pat in SOURCE_GLOBS:
        for p in root.glob(pat):
            rel = p.relative_to(root).as_posix()
            if p.is_dir() or rel in seen:
                continue
            if any(fnmatch.fnmatch(rel, e) for e in EXCLUDE):
                continue
            seen.add(rel)
            out.append(p)
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="UI-SPEC 与实现的覆盖度对比")
    ap.add_argument("specs", nargs="+", help="UI-SPEC 文件")
    ap.add_argument("--src", default=".", help="实现代码根目录")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    src_root = Path(args.src).resolve()
    if not src_root.is_dir():
        print(f"[check_spec_coverage] 源码目录不存在: {src_root}", file=sys.stderr)
        return 2

    files = iter_files(src_root)
    combined = "\n".join(p.read_text(encoding="utf-8", errors="ignore").lower() for p in files)

    report = []
    for spec in args.specs:
        spath = Path(spec)
        text = spath.read_text(encoding="utf-8")
        statuses, checks = extract_spec_sections(text)
        covered, missing = [], []
        for s in statuses:
            word = spec_primary_word(s)
            kws = HINT_KEYWORDS.get(word, [])
            kws = kws + [word] if word and word not in kws else kws
            hit = any(k.lower() in combined for k in kws if k)
            (covered if hit else missing).append(s)
        report.append({"spec": str(spath), "statuses": statuses,
                       "covered": covered, "missing": missing,
                       "checklist_items": checks})

    total_missing = sum(len(r["missing"]) for r in report)

    if args.json:
        print(json.dumps({"src": str(src_root), "scanned_files": len(files),
                          "total_missing": total_missing,
                          "report": report}, ensure_ascii=False, indent=2))
        return 1 if total_missing else 0

    print(f"\ncheck_spec_coverage  对比 {len(args.specs)} 份规格 / {len(files)} 个实现文件\n")
    for r in report:
        print(f"  📄 {r['spec']}")
        print(f"     状态矩阵 {len(r['statuses'])} 项：命中 {len(r['covered'])}，缺失 {len(r['missing'])}")
        for m in r["missing"]:
            print(f"       ❌ 未实现：{m}")
        if r["checklist_items"]:
            print(f"     验收清单 {len(r['checklist_items'])} 条（需人工或截图确认）")
    print()
    if total_missing:
        print(f"  ⚠️  合计 {total_missing} 个状态在代码里找不到对应实现。")
        print("     命中判断是基于关键字的启发式匹配，请人工复核后再下结论。\n")
    else:
        print("  ✅ 状态矩阵全部有对应实现\n")
    return 1 if total_missing else 0


if __name__ == "__main__":
    sys.exit(main())
