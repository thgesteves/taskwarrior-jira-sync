#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
HOOK_DIR="${HOME}/.task/hooks"
TASKRC="${TASKRC:-${HOME}/.taskrc}"
STAMP="$(date '+%Y%m%d%H%M%S')"

missing=()
for bin in python3 task acli; do
	if ! command -v "$bin" >/dev/null 2>&1; then
		missing+=("$bin")
	fi
done

if [ "${#missing[@]}" -gt 0 ]; then
	printf 'Missing required tools: %s\n' "${missing[*]}" >&2
	exit 1
fi

mkdir -p "$BIN_DIR" "$HOOK_DIR"

case ":$PATH:" in
	*":$BIN_DIR:"*) ;;
	*)
		printf 'Warning: %s is not on PATH.\n' "$BIN_DIR" >&2
		printf 'Add it to your shell profile so taskwarrior-jira-sync can be run directly.\n' >&2
		;;
esac

install_with_backup() {
	local src="$1"
	local dst="$2"
	if [ -e "$dst" ] && ! cmp -s "$src" "$dst"; then
		cp "$dst" "$dst.bak.$STAMP"
		printf 'Backed up %s to %s.bak.%s\n' "$dst" "$dst" "$STAMP"
	fi
	cp "$src" "$dst"
	chmod +x "$dst"
	printf 'Installed %s\n' "$dst"
}

install_with_backup "$SCRIPT_DIR/bin/taskwarrior-jira-sync" "$BIN_DIR/taskwarrior-jira-sync"
install_with_backup "$SCRIPT_DIR/hooks/on-modify.taskwarrior-jira-sync" "$HOOK_DIR/on-modify.taskwarrior-jira-sync"

uda_lines=(
	"uda.source.type=string"
	"uda.source.label=Source"
	"uda.jira_id.type=string"
	"uda.jira_id.label=Jira ID"
	"uda.jira_url.type=string"
	"uda.jira_url.label=Jira URL"
	"uda.jira_status.type=string"
	"uda.jira_status.label=Jira Status"
)

existing_uda_value() {
	local key="$1"
	local file="$2"
	awk -F= -v key="$key" '
		/^[[:space:]]*#/ { next }
		NF < 2 { next }
		{
			lhs = $1
			gsub(/^[[:space:]]+|[[:space:]]+$/, "", lhs)
			if (lhs == key) {
				value = substr($0, index($0, "=") + 1)
				gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
				print "__TASKW_FOUND__" value
				exit
			}
		}
	' "$file" 2>/dev/null
}

missing_udas=()
existing_different_udas=()
for line in "${uda_lines[@]}"; do
	key="${line%%=*}"
	expected="${line#*=}"
	existing_record="$(existing_uda_value "$key" "$TASKRC" || true)"
	if [ -z "$existing_record" ]; then
		missing_udas+=("$line")
	else
		existing_value="${existing_record#__TASKW_FOUND__}"
		if [ "$existing_value" != "$expected" ]; then
			existing_different_udas+=("$key")
		fi
	fi
done

if [ "${#existing_different_udas[@]}" -gt 0 ]; then
	for key in "${existing_different_udas[@]}"; do
		printf 'Keeping existing UDA definition: %s\n' "$key"
	done
fi

if [ "${#missing_udas[@]}" -gt 0 ]; then
	if [ -e "$TASKRC" ]; then
		cp "$TASKRC" "$TASKRC.bak.$STAMP"
		printf 'Backed up %s to %s.bak.%s\n' "$TASKRC" "$TASKRC" "$STAMP"
	else
		touch "$TASKRC"
		printf 'Created %s\n' "$TASKRC"
	fi
	{
		printf '\n# taskwarrior-jira-sync UDAs\n'
		for line in "${missing_udas[@]}"; do
			printf '%s\n' "$line"
		done
	} >>"$TASKRC"
	printf 'Appended missing Taskwarrior UDAs\n'
else
	printf 'Taskwarrior UDA keys already present\n'
fi

cat <<EOF

Installed taskwarrior-jira-sync.

Next steps:
  1. Authenticate acli.
  2. Optionally set TASKW_JIRA_PROJECT. Current default is "work".
  3. Run: taskwarrior-jira-sync
  4. Use Taskwarrior normally:
       task list
       task 12 modify jira_status:"In Review"
       task 12 done

Log:
  \${TASKW_JIRA_LOG:-~/.taskwarrior-jira-sync.log}
EOF
