#!/usr/bin/env bash
set -euo pipefail

if ! command -v task >/dev/null 2>&1; then
	printf 'Missing required tool: task\n' >&2
	exit 1
fi

task_config() {
	task rc.confirmation=no config "$@"
}

task_config report.jira.description "Jira imported tasks"
task_config report.jira.columns "id,project,description,jira_id,jira_status,jira_url"
task_config report.jira.labels "ID,Project,Description,Jira ID,Jira Status,Jira URL"
task_config report.jira.filter "status:pending source:jira"
task_config report.jira.sort "project+,jira_status+,description+"

task_config report.jira_status.description "Jira tasks by status"
task_config report.jira_status.columns "id,jira_id,jira_status,description"
task_config report.jira_status.labels "ID,Jira ID,Jira Status,Description"
task_config report.jira_status.filter "status:pending source:jira"
task_config report.jira_status.sort "jira_status+,jira_id+"

cat <<'EOF'
Configured Taskwarrior reports:
  task jira
  task jira_status
EOF
