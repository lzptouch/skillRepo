#!/usr/bin/env python3
"""
check_components.py — 设计漂移检测（component drift）

扫描 COMPONENTS.md 登记的组件 vs 代码里实际用到的组件，找出三类问题：

  D001 使用了未登记的 UI 组件（模型很可能自己造了一个）
  D002 Quarantine（未过审）组件被业务代码引用
  D003 疑似重复造轮子：业务层新建了与已登记组件同义的本地组件
  D004 业务代码直接从 design-system 内部文件深导入

用法:
    python3 check_components.py --components COMPONENTS.md --src src
    python3 check_components.py --json
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

SOURCE_GLOBS = ["**/*.tsx", "**/*.jsx"]
EXCLUDE = ["**/node_modules/**", "**/dist/**", "**/.next/**", "**/build/**", "**/*.stories.tsx"]

HEADING_RE = re.compile(r"^#{1,3}\s+`?([A-Z][A-Za-z0-9_]*)`?\s*$", re.M)
JSX_TAG_RE = re.compile(r"<([A-Z][A-Za-z0-9_.]*)([\s/>])")
IMPORT_FROM_DS_RE = re.compile(r"import\s+\{([^}]+)\}\s+from\s+[\"']([^\"']*design-system[^\"']*)[\"']")
DEEP_IMPORT_RE = re.compile(r"from\s+[\"'](@/(?:design-system|components|ui)/[^\"']+)[\"']")

# 已登记组件的常见别名/近似名，用于 D003 重复造轮子检测
SYNONYM_GROUPS = [
    {"Button", "Btn", "MyButton", "IconButton", "LinkButton", "ActionButton"},
    {"Input", "TextField", "TextInput", "MyInput"},
    {"Select", "Dropdown", "Combo", "Combobox", "Picker"},
    {"Card", "Panel", "Tile"},
    {"Dialog", "Modal", "Popup"},
    {"Toast", "Snackbar", "Notification"},
    {"DataTable", "Table", "Grid", "ListTable"},
    {"Tabs", "TabGroup", "Segmented", "SegmentedControl"},
    {"EmptyState", "Empty", "NoData", "BlankState"},
    {"Skeleton", "Shimmer", "Placeholder"},
    {"Badge", "Tag", "Chip", "Pill"},
    {"Pagination", "Pager"},
    {"Switch", "Toggle"},
    {"Spinner", "Loading", "Loader"},
]


def iter_files(root: Path) -> list[Path]:
    out, seen = [], set()
    for pat in SOURCE_GLOBS:
        for p in root.glob(pat):
            rel = p.relative_to(root).as_posix()
            if p.is_dir() or rel in seen:
                continue
            if any(fnmatch.fnmatch(rel, e) or fnmatch.fnmatch("/" + rel, e) for e in EXCLUDE):
                continue
            seen.add(rel)
            out.append(p)
    return sorted(out)


def parse_components_md(path: Path) -> tuple[set[str], set[str]]:
    """返回 (已登记组件, quarantine 组件)"""
    if not path.exists():
        return set(), set()
    text = path.read_text(encoding="utf-8")
    q_start = text.lower().find("## quarantine")
    head, quarantine_part = (text, "") if q_start == -1 else (text[:q_start], text[q_start:])
    registered = set(HEADING_RE.findall(head))
    quarantine = set(HEADING_RE.findall(quarantine_part))
    quarantine |= set(re.findall(r"^\|\s*`?([A-Z][A-Za-z0-9_]*)`?\s*\|", quarantine_part, re.M))
    return registered, quarantine


def main() -> int:
    ap = argparse.ArgumentParser(description="设计漂移检测")
    ap.add_argument("--root", default=".")
    ap.add_argument("--components", help="COMPONENTS.md 路径")
    ap.add_argument("--src", help="要扫描的源码根目录")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    comp_md = Path(args.components) if args.components else root / "COMPONENTS.md"
    src_root = Path(args.src) if args.src else root
    if not src_root.is_dir():
        print(f"[check_components] 源码目录不存在: {src_root}", file=sys.stderr)
        return 2

    registered, quarantine = parse_components_md(comp_md)
    files = iter_files(src_root)

    drift_raw: list[dict] = []
    for f in files:
        rel = f.relative_to(root).as_posix() if f.is_relative_to(root) else str(f)
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        is_ds = rel.startswith("design-system/")

        imported_from_ds: set[str] = set()
        for m in IMPORT_FROM_DS_RE.finditer(text):
            for name in [x.strip() for x in m.group(1).split(",") if x.strip()]:
                imported_from_ds.add(name)
            if "/" in m.group(2).replace("@/design-system", "").strip("/"):
                drift_raw.append({"rule": "D004", "file": rel, "component": m.group(2),
                                  "message": f"从 design-system 深路径导入 `{m.group(2)}`，应从根导入"})

        for m in DEEP_IMPORT_RE.finditer(text):
            if not is_ds and not m.group(1).startswith("@/design-system?"):
                drift_raw.append({"rule": "D004", "file": rel, "component": m.group(1),
                                  "message": f"深路径 UI 导入 `{m.group(1)}`，应改为 @/design-system"})

        for m in JSX_TAG_RE.finditer(text):
            name = m.group(1).split(".")[-1]
            # Quarantine 检查必须优先：业务代码引用未过审组件是硬性阻断
            if not is_ds and name in quarantine:
                drift_raw.append({"rule": "D002", "file": rel, "component": name,
                                  "message": f"`{name}` 还在 Quarantine 区（未过审），业务代码不得使用"})
                continue
            if is_ds or name in imported_from_ds:
                continue
            if name in registered:
                continue
            drift_raw.append({"rule": "D001", "file": rel, "component": name,
                              "message": f"`{name}` 未在 COMPONENTS.md 登记"})

        # D003 重复造轮子
        for group in SYNONYM_GROUPS:
            canonical = group & registered
            if not canonical:
                continue
            local = {n for n in group - registered if re.search(rf"\b(?:function|const)\s+{re.escape(n)}\b", text)}
            local = {n for n in local if re.search(rf"<{re.escape(n)}[\s/>]", text)}
            for n in local:
                drift_raw.append({"rule": "D003", "file": rel, "component": n,
                                  "message": f"疑似重复实现 `{n}`，COMPONENTS.md 已有 {sorted(canonical)[0]}"})

    # 去重
    seen, drift = set(), []
    for d in drift_raw:
        key = (d["rule"], d["file"], d["component"])
        if key in seen:
            continue
        seen.add(key)
        drift.append(d)

    # D001 噪音很大（例如 ReportTable、MyCard 这类业务组件），降级为 info 并折叠统计
    by_rule: dict[str, int] = {}
    for d in drift:
        by_rule[d["rule"]] = by_rule.get(d["rule"], 0) + 1
    errors = [d for d in drift if d["rule"] in ("D002", "D004")]

    if args.json:
        print(json.dumps({"registered": sorted(registered), "quarantine": sorted(quarantine),
                          "scanned_files": len(files), "summary": by_rule,
                          "findings": drift}, ensure_ascii=False, indent=2))
        return 1 if errors else 0

    print(f"\ncheck_components  {len(files)} 个文件 / 已登记 {len(registered)} 个组件\n")
    if not drift:
        print("  ✅ 未发现设计漂移\n")
        return 0
    icons = {"D001": "🔎", "D002": "❌", "D003": "⚠️", "D004": "⚠️"}
    for d in drift:
        print(f"  {icons.get(d['rule'], '·')} [{d['rule']}] {d['file']}  —  {d['message']}")
    print(f"\n  合计 {len(drift)} 条  {by_rule}")
    print("  D001 里若混着真实业务组件，请把它们加进 COMPONENTS.md 或改写本脚本的白名单\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
