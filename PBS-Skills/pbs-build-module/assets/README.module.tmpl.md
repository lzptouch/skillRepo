# <name>

<!-- 一句话：它做什么，什么时候用。 -->

## 快速开始

```bash
# 安装 / 引入方式
```

```ts
// 最小可用示例 —— 必须能直接复制运行，pbs-audit-module 会把它抽出来跑
import { <fn> } from '@pbs/<name>'

const result = <fn>({ ... })
```

## 接口

| 函数 | 输入 | 输出 | 异常 |
|---|---|---|---|
| `<fn>` | | | |

| 参数 | 类型 | 必填 | 约束 |
|---|---|---|---|
| | | | |

## 边界行为

| 场景 | 行为 |
|---|---|
| 输入为空 | |
| 输入超长 | |
| 外部依赖超时 | |
| 并发调用 | |

## 坏例子（不要这么写）

```ts
// 错误：忽略了错误分支，失败时静默返回 undefined
const r = await <fn>(x)
save(r.id)          // r 可能已经失败

// 正确：显式处理失败
const r = await <fn>(x)
if (!r.ok) return handleError(r.error)
save(r.value.id)
```

## 什么时候不要用

<!-- 最容易漏、也最能防误用的一段。 -->

- 不要用它的场景：
- 已有的更好的替代：`<另一个模块>`

## 已知限制

- 未覆盖：
- 依赖：
- 性能基线：

## 验证状态

- 测试：`pnpm vitest run modules/<lang>/<name>`
- 覆盖率：
- 最近验证日期：

## 变更

见 `CHANGELOG.md`。接口变更需同步更新 `../flows/<name>/flow.md`。
