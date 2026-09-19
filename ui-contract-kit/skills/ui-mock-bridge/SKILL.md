---
name: ui-mock-bridge
description: "把后端 OpenAPI/Swagger 转成前端数据契约、mock 数据与 MSW handler，并让 error/empty/loading 状态在本地可达。用于有接口文档要生成页面、需要 mock 数据先跑前端、后端改了接口要查前端漂移。当用户说「有 OpenAPI 帮我生成页面」「造点 mock 数据」「生成 MSW handler」时使用。"
license: Apache-2.0
metadata:
  author: skillRepo
  kit: ui-contract-kit
  version: "2.0"
  compatibility: 需要 Python 3.9+（纯标准库）；OpenAPI 为 YAML 输入时需 pyyaml
---

# ui-mock-bridge — OpenAPI ↔ UI-SPEC ↔ Mock

## 定位

后端工程师最容易上手的一环：**你已经有 OpenAPI 了，那就别手写数据契约。**
一条命令把它变成 UI-SPEC 的第 3 节 + 可直接跑的 mock。

## 本 skill 自带的资源

| 路径 | 内容 |
|---|---|
| `scripts/mockgen.py` | OpenAPI → 数据契约 / mock / MSW handler |
| `scripts/check_spec_coverage.py` | 确认状态矩阵真的在代码里有实现 |

## 命令

```bash
# 1) 看看有哪些接口
python3 scripts/mockgen.py openapi.json --list

# 2) 生成 UI-SPEC 第 3 节「数据契约」表格
python3 scripts/mockgen.py openapi.json --endpoint /api/v1/orders --contract \
    --out specs/ui/contract-orders.md

# 3) 生成 mock JSON（自动附带超长文本边界样本）
python3 scripts/mockgen.py openapi.json --endpoint /api/v1/orders --mock --count 5 \
    --out mock/orders.json

# 4) 生成 MSW handler（含 error 态开关）
python3 scripts/mockgen.py openapi.json --endpoint /api/v1/orders --msw \
    --out mocks/orders.ts
```

## 它做了什么

### 数据契约表

自动展开 `$ref`、`allOf`，识别 `{data:[], total:n}` 这类包装结构，输出：

| 字段 | 类型 | 约束 | 控件 | 默认 |
|---|---|---|---|---|

字段 → 控件推荐规则：

- enum ≤3 → Segmented / Radio
- enum >3 → Select（多选）
- number/integer → InputNumber / Slider
- boolean → Switch / Checkbox
- format=date/date-time → DatePicker
- 名字含 id/no/code → 主键列（等宽字体）
- 名字含 amount/price/total → 金额列（右对齐 tabular-nums）
- 名字含 remark/desc/content → 长文本（截断 + title）
- 名字含 status/state → Badge

> ⚠️ 控件列是**猜的**，脚本已在输出里明说必须人工复核。别直接入库。

### Mock 数据

按字段名和类型生成语义合理的值（手机号、邮箱、订单号、金额、日期），
并额外产出一条 `__edge__` 超长文本样本——专门用于验证「超长文本」这个最容易漏的状态。

### MSW handler

生成的 handler 带 `?__case=error` 开关，**这是重点**：
没有它，error / empty / loading 三个状态在开发环境里根本不可达，模型永远只能做 happy path。

```ts
http.get("/api/v1/orders", ({ request }) => {
  // ?__case=error 时返回 500，让 UI 的 error 分支可达
});
```

## 与状态矩阵的对接

在 UI-SPEC 第 5 节，每个状态都应写清「怎么在本地复现」：

| 状态 | 本地复现方式 |
|---|---|
| error | `<route>?__case=error` |
| empty | mock 里 `data: []` |
| loading | DevTools 限速 + 首次渲染截图 |
| 超长文本 | mockgen 生成的 `__edge__` 行 |
| 窄屏 | Playwright resize 375×812 |

然后：

```bash
python3 scripts/check_spec_coverage.py specs/ui/*.md --src src
```

确认这些状态真的在代码里有对应实现。

## 反向：变更检测

后端改了 OpenAPI？重新跑一次 `--contract`，diff 新旧表格，
能立刻发现「后端新增了字段但前端列没加」「类型从 string 改成了 enum」这类漂移。

## 常见坑

- OpenAPI 的 `$ref` 嵌套超过一层时脚本可能解析不出字段，会提示「检查 $ref 是否嵌套过深」。
- 不同后端的包装结构不同（`data`/`items`/`list`/`rows`/`records`/`content`），脚本已覆盖常见的几种；
  遇到别的前往 `mockgen.py` 的 `unwrap_list()` 加一行即可。
- YAML 输入要装 pyyaml，或者让后端同事导出一份 JSON。
