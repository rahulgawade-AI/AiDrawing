#!/usr/bin/env bash
set -euo pipefail

PROJECT="${1:-$HOME/llmproject/ai-town-planning}"
cd "$PROJECT"

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="runtime_backup_${STAMP}"
mkdir -p "$BACKUP"

FILES=(
  "townplanning/modules/regulations/extraction/postgresql_authoritative_table_resolver.py"
  "townplanning/modules/planning/mandatory/mandatory_rule_engine.py"
  "townplanning/modules/planning/services/planning_service.py"
)

echo "[1/4] Backing up current runtime files -> $BACKUP"
for f in "${FILES[@]}"; do
  if [[ -f "$f" ]]; then
    mkdir -p "$BACKUP/$(dirname "$f")"
    cp -a "$f" "$BACKUP/$f"
  fi
done

echo "[2/4] Installing authoritative PostgreSQL resolver"
mkdir -p townplanning/modules/regulations/extraction
cp -f "$(dirname "$0")/townplanning/modules/regulations/extraction/postgresql_authoritative_table_resolver.py" \
  townplanning/modules/regulations/extraction/postgresql_authoritative_table_resolver.py

echo "[3/4] Installing MandatoryRuleEngine and PlanningService"
cp -f "$(dirname "$0")/townplanning/modules/planning/mandatory/mandatory_rule_engine.py" \
  townplanning/modules/planning/mandatory/mandatory_rule_engine.py
cp -f "$(dirname "$0")/townplanning/modules/planning/services/planning_service.py" \
  townplanning/modules/planning/services/planning_service.py

echo "[4/4] Python syntax check"
python -m py_compile \
  townplanning/modules/regulations/extraction/postgresql_authoritative_table_resolver.py \
  townplanning/modules/planning/mandatory/mandatory_rule_engine.py \
  townplanning/modules/planning/services/planning_service.py

echo
echo "Installed."
echo "Backup: $PROJECT/$BACKUP"
echo
echo "Run test:"
echo "  pytest -s -v tests/functional/planning/test_postgresql_authoritative_pipeline.py"
