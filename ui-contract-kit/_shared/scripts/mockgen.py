#!/usr/bin/env python3
"""
mockgen.py — OpenAPI → UI-SPEC 数据契约 + mock 数据 / MSW handler

把后端已经有的 OpenAPI（Swagger）文档，转成前端 UI-SPEC 需要的东西：
  1. 数据契约 Markdown 表格（字段 / 类型 / 约束 / 建议控件 / 默认值）
  2. 可直接跑的 mock JSON 数据（含边界样本：超长文本、空数组、错误响应）
  3. MSW (Mock Service Worker) handler 片段

用法:
    python3 mockgen.py openapi.json --list
    python3 mockgen.py openapi.json --endpoint /api/v1/orders --contract
    python3 mockgen.py openapi.json --endpoint /api/v1/orders --mock --out mock/orders.json
    python3 mockgen.py openapi.json --endpoint /api/v1/orders --msw --out mocks/orders.ts

支持的输入: JSON；YAML 需安装 pyyaml（pip install pyyaml）
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


# ---------------------------------------------------------------- 载入
def load_doc(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            sys.exit("需要 pyyaml 才能读 YAML：pip install pyyaml（或让对方导出 JSON）")
        return yaml.safe_load(text)
    return json.loads(text)


def resolve(doc: dict, ref: str) -> dict:
    node = doc
    for part in ref.lstrip("#/").split("/"):
        node = node.get(part, {}) if isinstance(node, dict) else {}
    return node if isinstance(node, dict) else {}


def schema_fields(doc: dict, schema: dict) -> List[dict]:
    """展开 properties（含一层 $ref 解引用和 allOf 合并）"""
    if "$ref" in schema:
        schema = resolve(doc, schema["$ref"])
    for sub in schema.get("allOf", []):
        schema.update(resolve(doc, sub["$ref"]) if "$ref" in sub else sub)
    out = []
    required = set(schema.get("required", []))
    for name, prop in (schema.get("properties") or {}).items():
        if "$ref" in prop:
            prop = resolve(doc, prop["$ref"])
        out.append({
            "name": name,
            "type": prop.get("type", "string"),
            "format": prop.get("format"),
            "enum": prop.get("enum"),
            "example": prop.get("example"),
            "description": prop.get("description", ""),
            "maxLength": prop.get("maxLength"),
            "minimum": prop.get("minimum"),
            "maximum": prop.get("maximum"),
            "nullable": bool(prop.get("nullable")),
            "required": name in required,
        })
    return out


def find_operation(doc: dict, endpoint: str, method: str = "get"):
    for path_item, methods in (doc.get("paths") or {}).items():
        if path_item != endpoint:
            continue
        op = methods.get(method)
        if not op:
            continue
        resp = (op.get("responses") or {}).get("200") or {}
        content = (resp.get("content") or {})
        media = content.get("application/json") or next(iter(content.values()), {})
        return op, media.get("schema", {})
    return None, {}


def unwrap_list(doc: dict, schema: dict) -> dict:
    """如果是 {data:[], total:n}，返回 items 的 schema 给表格用"""
    if schema.get("type") == "array":
        items = schema.get("items", {})
        return resolve(doc, items["$ref"]) if "$ref" in items else items
    props = schema.get("properties") or {}
    for key in ("data", "items", "list", "rows", "records", "content"):
        if key in props and props[key].get("type") == "array":
            items = props[key].get("items", {})
            return resolve(doc, items["$ref"]) if "$ref" in items else items
    return schema


# ---------------------------------------------------------------- 控件推荐
def suggest_control(f: dict) -> str:
    if f["enum"]:
        n = len(f["enum"])
        if n <= 3:
            return "Segmented / Radio"
        return "Select（多选）"
    if f["type"] in {"integer", "number"}:
        return "InputNumber / Slider"
    if f["type"] == "boolean":
        return "Switch / Checkbox"
    fmt = f["format"] or ""
    if fmt in {"date", "date-time"}:
        return "DatePicker / DateRangePicker"
    if fmt in {"email", "phone", "tel"}:
        return "Input"
    name = f["name"].lower()
    if any(k in name for k in ("mobile", "phone", "tel")):
        return "Input"
    if any(k in name for k in ("time", "date", "at")) and f["type"] == "string":
        return "Datetime 文本列"
    if any(k in name for k in ("amount", "price", "money", "total", "fee")):
        return "金额文本（右对齐 tabular-nums）"
    if any(k in name for k in ("id", "no", "code", "sn")):
        return "主键列（等宽字体）"
    if any(k in name for k in ("status", "state")):
        return "Badge"
    if any(k in name for k in ("remark", "desc", "content", "note")):
        return "长文本（截断 + title）"
    return "Input / 文本列"


def constraint_text(f: dict) -> str:
    parts = []
    if f["maxLength"]:
        parts.append(f"≤ {f['maxLength']} 字符")
    if f["minimum"] is not None:
        parts.append(f"≥ {f['minimum']}")
    if f["maximum"] is not None:
        parts.append(f"≤ {f['maximum']}")
    if f["nullable"]:
        parts.append("可空")
    if f["required"]:
        parts.append("必填")
    elif parts:
        parts.insert(0, "选填")
    return "；".join(parts) or "—"


def type_text(f: dict) -> str:
    t = f["type"]
    if f["enum"]:
        return "enum"
    if f["format"]:
        return f"{t} ({f['format']})"
    return t


# ---------------------------------------------------------------- 生成
def render_contract(fields: List[dict], endpoint: str, op) -> str:
    op_name = (op or {}).get("summary") or (op or {}).get("operationId") or endpoint
    lines = [
        "## 3. 数据契约",
        "",
        f"**输入（`{endpoint}` 的 Query / Body）**",
        "",
        "| 字段 | 类型 | 约束 | 控件 | 默认 |",
        "|---|---|---|---|---|",
    ]
    for f in fields:
        lines.append(
            f"| `{f['name']}` | {type_text(f)} | {constraint_text(f)} | {suggest_control(f)} | "
            f"{('`' + json.dumps(f['enum'], ensure_ascii=False) + '`') if f['enum'] else '—'} |"
        )
    lines += [
        "",
        f"> 上表由 `mockgen.py` 从 OpenAPI 自动生成（源：`{op_name}`）。",
        "> 「控件」与「默认」两列是机器猜的，**必须人工复核后**才能入库 UI-SPEC。",
        "",
    ]
    return "\n".join(lines)


def gen_value(f: dict, index: int = 0, edge: bool = False) -> Any:
    if f["example"] is not None and not edge:
        return f["example"]
    if f["enum"]:
        return f["enum"][index % len(f["enum"])]
    name = f["name"].lower()
    if f["type"] == "integer":
        base = abs(int(f["maximum"] or 100000)) or 100
        return base if edge else random.randint(1, max(base, 1))
    if f["type"] == "number":
        return 999999.99 if edge else round(random.uniform(1, 5000), 2)
    if f["type"] == "boolean":
        return index % 2 == 0
    if (f["format"] or "") in {"date", "date-time"}:
        d = datetime(2026, 1, 1) + timedelta(days=index)
        return d.strftime("%Y-%m-%d %H:%M:%S") if f["format"] == "date-time" else d.strftime("%Y-%m-%d")
    # 字符串：按名字猜语义
    if any(k in name for k in ("mobile", "phone")):
        return "13800000000"
    if any(k in name for k in ("email",)):
        return f"user{index}@example.com"
    if any(k in name for k in ("id", "no", "code", "sn")):
        return f"ORD20260101{index:04d}"
    if any(k in name for k in ("amount", "price", "total")):
        return "1234567.89"
    base = f["description"] or f["name"]
    if edge:
        return (base * 40)[:300]
    return f"{base}{index}"


def build_mock(fields: List[dict], count: int = 5, edges: bool = True) -> List[dict]:
    rows = [{f["name"]: gen_value(f, i) for f in fields} for i in range(count)]
    if edges and fields:
        edge_row = {f["name"]: gen_value(f, 99, edge=True) for f in fields}
        edge_row["__edge__"] = "超长文本边界样本"
        rows.append(edge_row)
    return rows


def render_msw(endpoint: str, method: str, fields: List[dict]) -> str:
    sample = json.dumps(build_mock(fields, 2, False)[0], ensure_ascii=False, indent=2) \
        if fields else "{}"
    return f'''// 由 mockgen.py 生成 —— 请勿手改，重新生成即可
import {{ http, HttpResponse }} from "msw";

const sample = {sample};

export const handlers = [
  http.{method}("{endpoint}", ({{ request }}) => {{
    const url = new URL(request.url);
    const page = Number(url.searchParams.get("page") ?? 1);
    const pageSize = Number(url.searchParams.get("pageSize") ?? 20);

    // 正常态
    if (url.searchParams.get("__case") !== "error") {{
      return HttpResponse.json({{
        data: Array.from({{ length: pageSize }}, (_, i) => ({{
          ...sample,
          id: `${{page}}-${{i}}`,
        }})),
        total: 137,
        page,
        pageSize,
      }});
    }}
    // 错误态：让 UI 的 error 分支可达
    return HttpResponse.json({{ error: "internal_error" }}, {{ status: 500 }});
  }}),
];
'''


# ---------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description="OpenAPI → UI-SPEC 数据契约 / mock")
    ap.add_argument("openapi")
    ap.add_argument("--endpoint", help="如 /api/v1/orders")
    ap.add_argument("--method", default="get")
    ap.add_argument("--list", action="store_true", help="列出所有 endpoint")
    ap.add_argument("--contract", action="store_true", help="输出数据契约 Markdown")
    ap.add_argument("--mock", action="store_true", help="输出 mock JSON")
    ap.add_argument("--msw", action="store_true", help="输出 MSW handler")
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--out", help="写入文件，省略则打印到 stdout")
    args = ap.parse_args()

    doc = load_doc(Path(args.openapi))

    if args.list:
        print(f"\n{'METHOD':<8} PATH")
        print("-" * 70)
        for p, methods in (doc.get("paths") or {}).items():
            for m in methods:
                if m.lower() in {"get", "post", "put", "patch", "delete"}:
                    print(f"{m.upper():<8} {p}")
        return 0

    if not args.endpoint:
        print("需要 --endpoint（或用 --list 看看有哪些）", file=sys.stderr)
        return 2

    op, resp_schema = find_operation(doc, args.endpoint, args.method)
    if op is None:
        print(f"未找到 {args.method.upper()} {args.endpoint}", file=sys.stderr)
        return 2

    fields = schema_fields(doc, unwrap_list(doc, resp_schema))
    if not fields:
        print("没能从响应 schema 里解析出字段，检查 $ref 是否嵌套过深", file=sys.stderr)
        return 2

    out = []
    if args.contract:
        out.append(render_contract(fields, args.endpoint, op))
    if args.mock:
        out.append(json.dumps({"total": 137, "data": build_mock(fields, args.count)},
                              ensure_ascii=False, indent=2))
    if args.msw:
        out.append("```ts\n" + render_msw(args.endpoint, args.method, fields) + "```")
    if not out:
        out.append(render_contract(fields, args.endpoint, op))

    content = "\n\n".join(out)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(content, encoding="utf-8")
        print(f"✅ 已写入 {args.out}  （{len(fields)} 个字段）")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
