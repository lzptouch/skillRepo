#!/usr/bin/env python3
"""
ui_lint.py — 前端 UI 合规静态检查（纯标准库，Python 3.9+）

检查 UI 代码是否遵守 DESIGN.md / COMPONENTS.md 建立的契约。
把「prompt 里说过的话」变成「每次必然执行的 linter」。

用法:
    python3 ui_lint.py                       # 检查当前目录
    python3 ui_lint.py --root ../..          # 指定仓库根
    python3 ui_lint.py --json                # JSON 输出（喂给大模型）
    python3 ui_lint.py --only R001,R005      # 只跑指定规则
    python3 ui_lint.py --fix-hint            # 每条违规附带修改建议

退出码: 0 = 无 error 级违规; 1 = 有 error; 2 = 配置/运行错误
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List

DEFAULT_CONFIG: Dict = {
    "source_globs": [
        "src/**/*.tsx", "src/**/*.jsx", "src/**/*.ts",
        "app/**/*.tsx", "app/**/*.jsx",
        "components/**/*.tsx", "design-system/**/*.tsx",
        "features/**/*.tsx", "pages/**/*.tsx",
        "wireframe/**/*.tsx",
    ],
    "css_globs": ["**/*.css", "**/*.scss"],
    "exclude_globs": [
        "**/node_modules/**", "**/dist/**", "**/build/**", "**/.next/**",
        "**/coverage/**", "**/*.stories.tsx",
    ],
    "design_system_dir": "design-system",
    "design_system_pkg": "@/design-system",
    "severity": {
        "R001": "error", "R002": "error", "R003": "warn", "R004": "error",
        "R005": "error", "R006": "warn", "R007": "warn", "R008": "warn",
        "R009": "warn", "R010": "warn", "R011": "warn",
    },
    "allowed_tailwind_spacing": ["0", "0.5", "1", "2", "3", "4", "6", "8", "12"],
    "allow_arbitrary_variant_prefix": True,
    "banned_api": ["window.confirm", "window.alert", "confirm(", "alert(",
                   "prompt(", "dangerouslySetInnerHTML", "eval("],
    "raw_html_tags": ["<table", "<thead", "<tbody", "<tr>", "<th>", "<td>",
                      "<button", "<input", "<select", "<textarea"],
    "components_md": "COMPONENTS.md",
}

COLOR_RE = re.compile(
    r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b"
    r"|\b(?:rgb|rgba|hsl|hsla|hwb)\s*\("
    r"|\boklch\s*\(",
)
ARBITRARY_RE = re.compile(r"[a-z][a-z0-9-]*-\[[^\]]+\]")
TAILWIND_SPACING_RE = re.compile(
    r"(?:^|[\s\"'`])(-?(?:p|pt|pb|pl|pr|px|py|m|mt|mb|ml|mr|mx|my|gap|gap-x|gap-y"
    r"|space-x|space-y|w|h|min-w|min-h|top|left|right|bottom))-([0-9]+(?:\.5)?)"
    r"(?=[\s\"'`]|$)"
)
INLINE_STYLE_RE = re.compile(r"style\s*=\s*\{\{")
INLINE_STYLE_CSS_RE = re.compile(r"style\s*=\s*\"")
IMPORTANT_RE = re.compile(r"!\s*important")
TS_IGNORE_RE = re.compile(r"@ts-ignore|@ts-expect-error|eslint-disable")
CLASSNAME_PROP_RE = re.compile(r"\bclassName\s*=")
COMPONENT_CLASSNAME_RE = re.compile(
    r"<([A-Z][A-Za-z0-9_.]*)\b[^<>]*?\bclassName\s*=", re.S)
DIRECT_UI_IMPORT_RE = re.compile(r"from\s+[\"']@/(?:components|ui)/")


# --------------------------------------------------------------------------
def load_config(root: Path, explicit: str | None) -> Dict:
    cfg = dict(DEFAULT_CONFIG)
    cfg["severity"] = dict(DEFAULT_CONFIG["severity"])
    candidates = [Path(explicit)] if explicit else [
        root / ".ui-lintrc.json",
        root / "ui_rules.json",
        root / "design-system" / "ui_rules.json",
    ]
    for c in candidates:
        if c.exists():
            try:
                data = json.loads(c.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                fail(f"配置文件 {c} 不是合法 JSON: {e}")
            if isinstance(data, dict):
                for k, v in data.items():
                    if k == "severity" and isinstance(v, dict):
                        cfg["severity"].update(v)
                    else:
                        cfg[k] = v
            break
    return cfg


def fail(msg: str):
    print(f"[ui_lint] {msg}", file=sys.stderr)
    sys.exit(2)


def iter_project_files(root: Path, cfg: Dict) -> List[Path]:
    files: List[Path] = []
    globs = list(cfg["source_globs"]) + list(cfg["css_globs"])
    excludes = list(cfg["exclude_globs"])
    seen = set()
    for pattern in globs:
        for p in root.glob(pattern):
            rel = p.relative_to(root).as_posix()
            if p.is_dir() or rel in seen:
                continue
            if any(fnmatch.fnmatch("/" + rel, g.lstrip("/")) or
                   fnmatch.fnmatch(rel, g) for g in excludes):
                continue
            seen.add(rel)
            files.append(p)
    return sorted(files)


def any_match(rel: str, globs) -> bool:
    return any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch("/" + rel, g.lstrip("/"))
               for g in globs)


def in_design_system(path: Path, root: Path, cfg: Dict) -> bool:
    """path 已经可能是相对路径，也可能是绝对路径，两种都要处理"""
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return rel.startswith(cfg["design_system_dir"] + "/")


def strip_comments(text: str, path: Path) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    if path.suffix.lower() in {".css", ".scss"}:
        return text
    text = re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.S)
    return text


def finding(rule: str, file: Path, line: int, snippet: str, message: str) -> Dict:
    return {"rule": rule, "file": str(file), "line": line,
            "snippet": snippet.strip()[:160], "message": message}


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def snippet_at(text: str, idx: int) -> str:
    start = text.rfind("\n", 0, idx) + 1
    end = text.find("\n", idx)
    return text[start: end if end != -1 else len(text)]


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------
def make_rules(cfg: Dict, root: Path) -> Dict[str, Callable]:
    rules: Dict[str, Callable] = {}

    def r001(text, path):  # 裸色值
        rel = path.as_posix()
        if any_match(rel, cfg.get("allow_raw_color_globs",
                                  ["design-system/tokens.*", "**/tokens.css", "**/theme.css"])):
            return []
        out = []
        for m in COLOR_RE.finditer(text):
            snippet = snippet_at(text, m.start())
            if re.search(r"var\s*\(\s*--", snippet):
                continue
            if "允许本文件维护色板" in snippet or "palette" in snippet.lower():
                continue
            out.append(finding("R001", path, line_of(text, m.start()), snippet,
                               f"裸色值 `{m.group(0)}`，应改用 DESIGN.md 里的语义 token（如 var(--color-danger)）"))
        return out

    def r002(text, path):  # Tailwind 任意值
        out = []
        for m in ARBITRARY_RE.finditer(text):
            snippet = snippet_at(text, m.start())
            if cfg.get("allow_arbitrary_variant_prefix") and m.group(0).startswith("["):
                continue
            out.append(finding("R002", path, line_of(text, m.start()), snippet,
                               f"Tailwind 任意值 `{m.group(0)}`，应改为 token 或标准尺度"))
        return out

    def r003(text, path):  # 内联样式
        out = []
        for rx in (INLINE_STYLE_RE, INLINE_STYLE_CSS_RE):
            for m in rx.finditer(text):
                out.append(finding("R003", path, line_of(text, m.start()),
                                   snippet_at(text, m.start()),
                                   "内联样式，应改用语义 token / 组件 props"))
        return out

    def r004(text, path):
        return [finding("R004", path, line_of(text, m.start()),
                        snippet_at(text, m.start()), "使用了 !important，应通过调整 token 或选择器解决")
                for m in IMPORTANT_RE.finditer(text)]

    def r005(text, path):  # 禁用 API
        out = []
        for api in cfg["banned_api"]:
            for m in re.finditer(re.escape(api), text):
                if api in ("confirm(", "alert(", "prompt(") and \
                        re.search(r"window\.\s*" + re.escape(api[:-1]) + r"\s*\(", snippet_at(text, m.start())) is None \
                        and re.search(r"\." + re.escape(api[:-1]) + r"\s*\(", text[:m.start()][-40:] + api):
                    continue
                out.append(finding("R005", path, line_of(text, m.start()),
                                   snippet_at(text, m.start()),
                                   f"使用了禁用的浏览器原生 API `{api}`，应改用设计系统组件（Dialog / Toast）"))
        return out

    def r006(text, path):  # 原生 HTML 控件
        if in_design_system(path, root, cfg):
            return []
        out = []
        for tag in cfg["raw_html_tags"]:
            for m in re.finditer(re.escape(tag), text):
                out.append(finding("R006", path, line_of(text, m.start()),
                                   snippet_at(text, m.start()),
                                   f"在业务代码里用了原生标签 `{tag}`，应复用 design-system 组件"))
        return out

    def r007(text, path):  # 直接深路径导入 UI
        if in_design_system(path, root, cfg):
            return []
        out = []
        for m in DIRECT_UI_IMPORT_RE.finditer(text):
            out.append(finding("R007", path, line_of(text, m.start()),
                               snippet_at(text, m.start()),
                               f"应从 `{cfg['design_system_pkg']}` 根导入，不要深路径引用 UI 内部文件"))
        return out

    def r008(text, path):  # design-system 里混入业务逻辑
        if not in_design_system(path, root, cfg):
            return []
        out = []
        patterns = {
            "网络请求": r"\b(fetch|axios|useQuery|useMutation|trpc)\s*\(",
            "路由": r"\b(useRouter|useNavigate|next/link|next/navigation)\b",
            "全局状态": r"\b(useStore|zustand|redux|useContext)\b",
        }
        for name, pat in patterns.items():
            for m in re.finditer(pat, text):
                out.append(finding("R008", path, line_of(text, m.start()),
                                   snippet_at(text, m.start()),
                                   f"design-system 组件里出现了{name}逻辑，应保持纯 UI"))
        return out

    def r009(text, path):  # 间距尺度
        allowed = set(str(x) for x in cfg["allowed_tailwind_spacing"])
        out = []
        for m in TAILWIND_SPACING_RE.finditer(text):
            if re.search(r"[a-zA-Z0-9_-]-\[[^\]]+\]", m.group(0)):
                continue
            value = m.group(2)
            if value not in allowed:
                out.append(finding("R009", path, line_of(text, m.start()),
                                   snippet_at(text, m.start()),
                                   f"间距/尺寸 `{m.group(1)}-{value}` 不在 DESIGN.md 的尺度内（允许: {sorted(allowed, key=float)}）"))
        return out

    def r010(text, path):  # 绕过类型/lint
        return [finding("R010", path, line_of(text, m.start()),
                        snippet_at(text, m.start()),
                        "绕过了类型检查或 lint 规则，应修正根因而不是屏蔽")
                for m in TS_IGNORE_RE.finditer(text)]

    def r011(text, path):  # 给受控组件传 className
        if in_design_system(path, root, cfg):
            return []
        out = []
        for m in COMPONENT_CLASSNAME_RE.finditer(text):
            out.append(finding("R011", path, line_of(text, m.start()),
                               snippet_at(text, m.start()),
                               f"给受控组件 `<{m.group(1)}>` 传了 className —— 组件样式已收敛，"
                               f"应改用 variant / size / tone 等语义 props"))
        return out

    for name, fn in [("R001", r001), ("R002", r002), ("R003", r003), ("R004", r004),
                     ("R005", r005), ("R006", r006), ("R007", r007), ("R008", r008),
                     ("R009", r009), ("R010", r010), ("R011", r011)]:
        rules[name] = fn
    return rules


RULE_DOCS = {
    "R001": "禁止裸色值 → 用语义 token",
    "R002": "禁止 Tailwind 任意值 → 用 token / 标准尺度",
    "R003": "禁止内联样式",
    "R004": "禁止 !important",
    "R005": "禁止 window.confirm / alert / dangerouslySetInnerHTML 等",
    "R006": "禁止在业务代码里写原生 HTML 控件",
    "R007": "UI 必须从 design-system 根导入",
    "R008": "design-system 必须是纯 UI，不得含网络/路由/全局状态",
    "R009": "间距/尺寸必须落在 DESIGN.md 的尺度内",
    "R010": "不得用 @ts-ignore / eslint-disable 绕过门禁",
    "R011": "不得给已收敛的组件传 className",
}
FIX_HINTS = {
    "R001": "把 `{}` 换成 DESIGN.md 中对应的 `var(--color-*)`",
    "R002": "换成标准 Tailwind 尺度；必须要特殊值时先来问是否要加 token",
    "R003": "改为 className + token，或给组件加语义 props",
    "R004": "调整选择器优先级或 token，不要用 !important",
    "R005": "用 Dialog 做确认、Toast 做提示、OutboundLink 做跳转",
    "R006": "改用 COMPONENTS.md 里登记的等价组件",
    "R007": f'改为 import {{ X }} from "@/design-system"',
    "R008": "把副作用移到 src/features 层，组件只接收 props 和回调",
    "R009": "改用 4px 基准尺度里的值",
    "R010": "修正根因；确有必要时来问，不要自己屏蔽规则",
    "R011": "用 variant/size/tone 等已在组件契约里登记的 props",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="前端 UI 契约合规静态检查")
    ap.add_argument("--root", default=".", help="仓库根目录")
    ap.add_argument("--config", help="指定配置文件路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON（供大模型消费）")
    ap.add_argument("--only", help="只跑指定规则，逗号分隔，如 R001,R005")
    ap.add_argument("--skip", help="跳过指定规则")
    ap.add_argument("--fix-hint", action="store_true", help="附带修改建议")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        fail(f"根目录不存在: {root}")

    cfg = load_config(root, args.config)
    rules = make_rules(cfg, root)
    active = set(rules)
    if args.only:
        active = {r.strip() for r in args.only.split(",")}
    for r in (args.skip.split(",") if args.skip else []):
        active.discard(r.strip())

    files = iter_project_files(root, cfg)
    all_findings: List[Dict] = []
    for f in files:
        try:
            raw = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        text = strip_comments(raw, f)
        for rid in sorted(active & set(rules)):
            all_findings.extend(rules[rid](text, f.relative_to(root)))

    # 同一规则在同一行的重复命中只保留一条（如 window.confirm 同时命中 confirm(）
    deduped, seen_keys = [], set()
    for x in all_findings:
        key = (x["rule"], x["file"], x["line"], x["snippet"], x["message"])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(x)
    all_findings = deduped

    severity_of = lambda r: cfg["severity"].get(r, "warn")
    errors = [x for x in all_findings if severity_of(x["rule"]) == "error"]

    if args.json:
        print(json.dumps({
            "root": str(root),
            "scanned_files": len(files),
            "summary": {
                "total": len(all_findings),
                "errors": len(errors),
                "warnings": len(all_findings) - len(errors),
                "by_rule": {r: len([x for x in all_findings if x["rule"] == r]) for r in sorted(active)},
            },
            "findings": all_findings,
        }, ensure_ascii=False, indent=2))
        return 1 if errors else 0

    if not args.quiet:
        print(f"\nui_lint  扫描 {len(files)} 个文件  (root: {root})\n")
        if not all_findings:
            print("  ✅ 全部通过，没有发现契约违规\n")
            return 0
        for x in all_findings:
            sev = severity_of(x["rule"])
            mark = "❌" if sev == "error" else "⚠️"
            print(f"  {mark} [{x['rule']}] {x['file']}:{x['line']}  {x['message']}")
            if args.fix_hint:
                print(f"       → {FIX_HINTS.get(x['rule'], '')}")
        print(f"\n  合计 {len(all_findings)} 条：{len(errors)} error / "
              f"{len(all_findings) - len(errors)} warn")
        print("  规范化后再跑一次：python3 ui_lint.py\n")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
