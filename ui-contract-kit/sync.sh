#!/usr/bin/env bash
# ui-contract-kit 资源同步脚本
#
#   bash sync.sh
#
# 背景：Agent Skills 规范要求「一个 skill = 一个自包含目录」，
# 引用资源只能用相对 skill 根目录的一层路径（scripts/ assets/ references/）。
# 但 6 个 skill 共用同一批脚本和模板，写 6 份会立刻腐烂。
#
# 解法：_shared/ 是唯一真源，本脚本把它复制进每个 skill 目录，
# 让仓库里的 skill 目录本身就是自包含的（可以直接 cp 到任何 IDE 的 skills 目录）。
#
# 改脚本/模板时：改 _shared/ 里的，然后重新跑 bash sync.sh。

set -eo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED="$HERE/_shared"
SKILLS="$HERE/skills"

[ -d "$SHARED" ] || { echo "找不到 _shared：$SHARED" >&2; exit 1; }

# 每个 skill 需要的资源清单（相对 _shared/）
# 格式：skill|脚本|模板|是否带 prompts.md|是否带 guide
MANIFEST=(
  "ui-contract-init|ui_lint.py,check_components.py,verify_ui.sh,ui_rules.json|PRODUCT.md,DESIGN.md,COMPONENTS.md,AGENTS.md,tokens.json,UI-SPEC-订单列表页.md|0|1"
  "ui-spec-edit|mockgen.py,check_spec_coverage.py|UI-SPEC-订单列表页.md|0|0"
  "ui-generate|build_contact_sheet.py,ui_lint.py||1|1"
  "ui-lint|ui_lint.py,check_components.py,check_spec_coverage.py,verify_ui.sh,ui_rules.json||0|0"
  "ui-compliance|llm_review.py,build_contact_sheet.py,ui_lint.py||1|0"
  "ui-mock-bridge|mockgen.py,check_spec_coverage.py||0|0"
)

for entry in "${MANIFEST[@]}"; do
  IFS='|' read -r skill scripts templates want_prompts want_guide <<< "$entry"
  dest="$SKILLS/$skill"
  [ -d "$dest" ] || { echo "跳过（目录不存在）：$dest" >&2; continue; }

  # 清空旧的生成物，保证 _shared 里删掉的资源不会残留
  rm -rf "$dest/scripts" "$dest/assets" "$dest/references"

  if [ -n "$scripts" ]; then
    mkdir -p "$dest/scripts"
    IFS=',' read -ra arr <<< "$scripts"
    for s in "${arr[@]}"; do cp "$SHARED/scripts/$s" "$dest/scripts/$s"; done
  fi

  if [ -n "$templates" ]; then
    mkdir -p "$dest/assets/templates"
    IFS=',' read -ra arr <<< "$templates"
    for t in "${arr[@]}"; do cp "$SHARED/templates/$t" "$dest/assets/templates/$t"; done
  fi

  if [ "$want_prompts" = "1" ]; then
    mkdir -p "$dest/references"
    cp "$SHARED/prompts.md" "$dest/references/prompts.md"
  fi

  if [ "$want_guide" = "1" ]; then
    mkdir -p "$dest/references"
    cp "$SHARED/guide/README-LLM前端受控开发指南.md" "$dest/references/guide-LLM前端受控开发指南.md"
  fi

  printf "  [ok] %-18s %s\n" "$skill" "$(ls "$dest" | grep -Ev '^SKILL.md$' | tr '\n' ' ')"
done

printf "\n同步完成：_shared -> skills（每个 skill 现已自包含，可直接 cp 到任意 IDE 的 skills 目录）\n"
