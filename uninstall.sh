#!/usr/bin/env bash
set -euo pipefail

BIN="${HOME}/.local/bin/taskwarrior-jira-sync"
HOOK="${HOME}/.task/hooks/on-modify.taskwarrior-jira-sync"

rm -f "$BIN"
rm -f "$HOOK"

cat <<EOF
Removed:
  $BIN
  $HOOK

Left in place:
  ~/.taskwarrior-jira-sync.log
  Taskwarrior UDA lines in ~/.taskrc
EOF

