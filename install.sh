#!/usr/bin/env bash
# skillRepo 通用安装器
#
#   把仓库里所有 skill 安装到任意基于 agent 的编程工具能识别的目录。
#   所有 skill 均遵循 Agent Skills 开放标准（https://agentskills.io/specification）：
#     一个 skill = 一个自包含目录，含 SKILL.md（name + description frontmatter）
#     外加可选的 scripts/ references/ assets/。
#
# 用法
#   bash install.sh                      # 安装到用户级目录（默认，装所有已装的工具）
#   bash install.sh --all                # 用户级 + 项目级目录都装
#   bash install.sh --project [dir]      # 只装项目级（默认当前目录）
#   bash install.sh --only claude,codex  # 只装指定工具
#   bash install.sh --list               # 列出所有支持的目标与是否命中
#   bash install.sh --dry-run            # 只打印将要做什么
#   bash install.sh --export ./dist      # 导出一份自包含的便携副本
#   bash install.sh --uninstall          # 从所有目标目录移除
#
# 说明
#   · 安装是复制，不是软链：软链在某些工具里不会被跟随，复制最稳。
#     重跑本脚本即可更新。
#   · 安装后通常需要重启 IDE，让 skill 被重新索引。

set -eo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODE="user"          # user | project | all
PROJECT_DIR="$PWD"
ONLY=""
DRY_RUN=0
EXPORT_DIR=""
DO_UNINSTALL=0
DO_LIST=0

# ---- 目标目录表：label|用户级路径|项目级路径(相对项目根) ----
# 依据各工具 2026 年的官方实现整理。
TARGETS=(
  # agents: 开放标准通用目录，Codex / Cursor / Copilot / Gemini CLI 都扫
  "agents|$HOME/.agents/skills|.agents/skills"
  # Claude Code
  "claude|$HOME/.claude/skills|.claude/skills"
  # Cursor（同时兼容读 .claude/skills 与 .codex/skills）
  "cursor|$HOME/.cursor/skills|.cursor/skills"
  # GitHub Copilot / VS Code 代理模式
  "copilot|$HOME/.copilot/skills|.github/skills"
  # OpenAI Codex（官方主目录是 ~/.agents/skills，~/.codex/skills 作为兼容位）
  "codex|$HOME/.codex/skills|.codex/skills"
  # Gemini CLI
  "gemini|$HOME/.gemini/skills|.gemini/skills"
  # WorkBuddy / CodeBuddy
  "codebuddy|$HOME/.workbuddy/skills|.codebuddy/skills"
)

# ---------------------------------------------------------------- 参数解析
while [ $# -gt 0 ]; do
  case "$1" in
    --all)        MODE="all"; shift ;;
    --project)    MODE="project"; [ -n "${2:-}" ] && [ "${2#-}" = "$2" ] && { PROJECT_DIR="$2"; shift; }; shift ;;
    --user)       MODE="user"; shift ;;
    --only)       ONLY="${2:-}"; shift 2 ;;
    --dry-run)    DRY_RUN=1; shift ;;
    --export)     EXPORT_DIR="${2:-}"; shift 2 ;;
    --uninstall)  DO_UNINSTALL=1; shift ;;
    --list)       DO_LIST=1; shift ;;
    -h|--help)    sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "未知参数：$1（用 --help 看用法）" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------- 工具函数
discover_skills() {
  find "$HERE" -name SKILL.md -type f \
    -not -path "*/.git/*" -not -path "*/_shared/*" -not -path "*/node_modules/*" \
    -print0 2>/dev/null | while IFS= read -r -d '' f; do dirname "$f"; done | sort
}

skill_name_of() { basename "$1"; }

validate_skill() {
  # 规范要求 name 必须匹配父目录名；这里只做温和告警，不阻断安装
  local dir="$1" nm declared
  nm="$(basename "$dir")"
  declared="$(sed -n 's/^name:[[:space:]]*//p' "$dir/SKILL.md" | head -1 | tr -d '"'"'"'\r')"
  if [ -n "$declared" ] && [ "$declared" != "$nm" ]; then
    echo "  [warn] $nm：frontmatter 的 name($declared) 与目录名不一致，规范建议一致"
  fi
}

# 组装自包含副本（ui-contract-kit 的共享资源需要先下沉）
prepare() {
  if [ -x "$HERE/ui-contract-kit/sync.sh" ] || [ -f "$HERE/ui-contract-kit/sync.sh" ]; then
    if [ "$DRY_RUN" = "0" ]; then
      ( cd "$HERE/ui-contract-kit" && bash sync.sh ) >/dev/null
    fi
  fi
}

install_into() {
  local root="$1" label="$2"
  [ -n "$root" ] || return 0
  if [ "$DRY_RUN" = "1" ]; then
    echo "  [dry]  -> $root  ($label)"
    return 0
  fi
  mkdir -p "$root"
  local n=0
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    local nm; nm="$(skill_name_of "$d")"
    rm -rf "$root/$nm"
    cp -R "$d" "$root/$nm"
    n=$((n+1))
  done <<< "$SKILLS"
  echo "  [ok]  $label -> $root  (${n} 个 skill)"
}

uninstall_from() {
  local root="$1" label="$2"
  [ -d "$root" ] || return 0
  local n=0
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    local nm; nm="$(skill_name_of "$d")"
    [ -e "$root/$nm" ] && rm -rf "$root/$nm" && n=$((n+1))
  done <<< "$SKILLS"
  [ "$n" -gt 0 ] && echo "  [rm]  $label -> $root  (${n} 个)"
  return 0
}

# ---------------------------------------------------------------- 模式：--list
if [ "$DO_LIST" = "1" ]; then
  echo "支持的目标目录："
  for t in "${TARGETS[@]}"; do
    IFS='|' read -r label upath rpath <<< "$t"
    printf "  %-11s 用户级 %-28s %s\n" "$label" "$upath" \
      "$([ -d "$upath" ] && echo '[已存在]' || echo '[未创建]')"
    printf "  %-11s 项目级 %-28s\n" "" "$rpath"
  done
  echo
  echo "仓库里的 skill："
  discover_skills | while read -r d; do echo "  $(basename "$d")  (${d#$HERE/})"; done
  exit 0
fi

# ---------------------------------------------------------------- 模式：--export
if [ -n "$EXPORT_DIR" ]; then
  prepare
  mkdir -p "$EXPORT_DIR"
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    rm -rf "$EXPORT_DIR/$(basename "$d")"
    cp -R "$d" "$EXPORT_DIR/"
    echo "  [ok]  $(basename "$d")"
  done <<< "$(discover_skills)"
  cp "$HERE/README.md" "$EXPORT_DIR/" 2>/dev/null || true
  echo
  echo "已导出到 $EXPORT_DIR（每个目录自包含，可直接拷进任何工具的 skills 目录）"
  exit 0
fi

# ---------------------------------------------------------------- 主流程
SKILLS="$(discover_skills)"
COUNT="$(printf '%s\n' "$SKILLS" | grep -c . || true)"

echo "skillRepo：发现 ${COUNT} 个 skill"
[ "$DO_UNINSTALL" = "0" ] && prepare

# 校验 name 与目录名一致性
if [ "$DRY_RUN" = "0" ]; then
  while IFS= read -r d; do [ -n "$d" ] && validate_skill "$d"; done <<< "$SKILLS"
fi

for t in "${TARGETS[@]}"; do
  IFS='|' read -r label upath rpath <<< "$t"
  if [ -n "$ONLY" ]; then
    case ",$ONLY," in *",$label,"*) ;; *) continue ;; esac
  fi
  [ "$MODE" = "user" ] || [ "$MODE" = "all" ] && {
    if [ "$DO_UNINSTALL" = "1" ]; then uninstall_from "$upath" "$label(user)"
    else install_into "$upath" "$label(user)"; fi
  }
  [ "$MODE" = "project" ] || [ "$MODE" = "all" ] && {
    if [ "$DO_UNINSTALL" = "1" ]; then uninstall_from "$PROJECT_DIR/$rpath" "$label(project)"
    else install_into "$PROJECT_DIR/$rpath" "$label(project)"; fi
  }
done

echo
if [ "$DO_UNINSTALL" = "1" ]; then
  echo "卸载完成。"
else
  echo "安装完成：${COUNT} 个 skill x 上述目标目录。"
  echo "下一步：重启你的 IDE，让 skill 被重新索引。"
fi
