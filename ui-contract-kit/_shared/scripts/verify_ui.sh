#!/usr/bin/env bash
# verify_ui.sh — 一键 UI 契约门禁
#
# 用法：
#   bash verify_ui.sh            # 跑全部能跑的检查
#   bash verify_ui.sh --quick    # 只跑不依赖 npm 的部分
#
# 建议把它挂进 package.json:  "verify:ui": "bash scripts/verify_ui.sh"
# 并在 AGENTS.md 里写死：改完 UI 必须跑这个，修到全绿才算完成。

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${UI_ROOT:-$(pwd)}"
QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1

RED=$'\033[0;31m'; GRN=$'\033[0;32m'; YEL=$'\033[0;33m'; DIM=$'\033[2m'; RST=$'\033[0m'
failures=0

run_step() {
  local name="$1"; shift
  printf "\n%s▶ %s%s\n" "$DIM" "$name" "$RST"
  if "$@"; then
    printf "%s✔ %s 通过%s\n" "$GRN" "$name" "$RST"
  else
    printf "%s✘ %s 未通过%s\n" "$RED" "$name" "$RST"
    failures=$((failures + 1))
  fi
}

echo "verify_ui  root=$ROOT"

if [ "$QUICK" -eq 0 ] && [ -f "$ROOT/package.json" ]; then
  grep -q '"type-check"' "$ROOT/package.json" && \
    run_step "TypeScript 类型检查" npm run --prefix "$ROOT" type-check
  grep -q '"lint"' "$ROOT/package.json" && \
    run_step "ESLint" npm run --prefix "$ROOT" lint
  grep -q '"lint:css"' "$ROOT/package.json" && \
    run_step "Stylelint（禁裸值）" npm run --prefix "$ROOT" lint:css
else
  [ "$QUICK" -eq 0 ] && echo "${DIM}（非 npm 项目，跳过 tsc/eslint/stylelint）${RST}"
fi

run_step "UI 契约静态检查 (ui_lint)" \
  python3 "$HERE/ui_lint.py" --root "$ROOT" --fix-hint

run_step "设计漂移检测 (check_components)" \
  python3 "$HERE/check_components.py" --root "$ROOT" --components "$ROOT/COMPONENTS.md"

if ls "$ROOT"/specs/ui/*.md >/dev/null 2>&1; then
  run_step "UI-SPEC 状态矩阵覆盖率" \
    python3 "$HERE/check_spec_coverage.py" "$ROOT"/specs/ui/*.md --src "$ROOT/src"
else
  echo "${DIM}（没有 specs/ui/*.md，跳过覆盖率检查）${RST}"
fi

printf "\n"
if [ "$failures" -eq 0 ]; then
  printf "%s✔ verify_ui 全部通过%s\n\n" "$GRN" "$RST"
else
  printf "%s✘ verify_ui 有 %d 项未通过%s\n" "$YEL" "$failures" "$RST"
  printf "%s  1. 优先修 error 级（R001 裸色值 / R002 任意值 / R005 禁用 API）%s\n" "$DIM" "$RST"
  printf "%s  2. 每条修复都要落到 token 或组件 props，不要就地绕过%s\n\n" "$DIM" "$RST"
fi
exit 0
