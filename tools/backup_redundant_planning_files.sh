#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLANNING="$ROOT/townplanning/modules/planning"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$ROOT/backup/planning_redundant_$STAMP"

if [[ ! -d "$PLANNING" ]]; then
  echo "ERROR: active planning module not found: $PLANNING" >&2
  exit 1
fi

mkdir -p "$BACKUP"

move_if_exists() {
  local src="$1"
  if [[ -e "$src" ]]; then
    local rel="${src#$PLANNING/}"
    mkdir -p "$BACKUP/$(dirname "$rel")"
    mv "$src" "$BACKUP/$rel"
    echo "BACKED UP: $rel"
  fi
}

# Historical copies inside the active module. These are not imported by the
# active package and should not be left beside production modules.
move_if_exists "$PLANNING/llm/constraint_discovery.py_bkp"
move_if_exists "$PLANNING/llm/constraint_discovery.py_bkplatest"
move_if_exists "$PLANNING/regulations/constraint_calculator.py.before_all_constraints"
move_if_exists "$PLANNING/regulations/udcpr_rule_resolver.py.bak"
move_if_exists "$PLANNING/regulations/udcpr_rule_resolver.py.bak-chroma-first"
move_if_exists "$PLANNING/rules/rule_condition_engine.py_bkp"

# Python bytecode is generated and never belongs in the source tree.
while IFS= read -r -d '' pycache; do
  rel="${pycache#$PLANNING/}"
  mkdir -p "$BACKUP/$(dirname "$rel")"
  mv "$pycache" "$BACKUP/$rel"
  echo "BACKED UP: $rel"
done < <(find "$PLANNING" -type d -name __pycache__ -print0)

# Older complete planning-module snapshots are also kept out of the import
# tree. They are moved only if present; nothing is deleted.
for old in \
  "$ROOT/townplanning/modules/planning.backup" \
  "$ROOT/townplanning/modules/planning.backup-v2" \
  "$ROOT/townplanning/modules/planning.backup-v3"; do
  if [[ -d "$old" ]]; then
    name="$(basename "$old")"
    mv "$old" "$BACKUP/$name"
    echo "BACKED UP: $name"
  fi
done

echo
echo "Backup created: $BACKUP"
echo "Nothing was deleted."
