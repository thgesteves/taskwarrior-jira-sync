# taskwarrior-jira-sync

[![CI](https://github.com/thgesteves/taskwarrior-jira-sync/actions/workflows/ci.yml/badge.svg)](https://github.com/thgesteves/taskwarrior-jira-sync/actions/workflows/ci.yml)

Small Python Jira sync for Taskwarrior.

Taskwarrior stays the source of truth. The sync reads tasks with `task export` and writes tasks with native `task add`. Jira transitions are requested from a Taskwarrior `on-modify` hook when you change `jira_status`.

## Requirements

- `python3`
- `task`
- `acli`

Authenticate `acli` before using the sync.

## Install ACLI

Official install guide:

https://developer.atlassian.com/cloud/acli/guides/install-acli/

macOS with Homebrew:

```sh
brew tap atlassian/homebrew-acli
brew install acli
acli --version
```

Linux:

Use Atlassian's Linux install guide:

https://developer.atlassian.com/cloud/acli/guides/install-linux/

It covers Debian/Ubuntu, Red Hat/Fedora/CentOS, and manual binary installs.

Authenticate Jira with an Atlassian API token:

```sh
echo <token> | acli jira auth login --site "your-site.atlassian.net" --email "you@example.com" --token
```

Verify Jira access:

```sh
acli jira workitem search --jql "assignee = currentUser() AND statusCategory != Done" --json
```

This repo's `install.sh` only checks that `acli` exists. It does not install `acli`.

## Install

```sh
./install.sh
```

The installer:

- installs `bin/taskwarrior-jira-sync` to `~/.local/bin/taskwarrior-jira-sync`
- installs `hooks/on-modify.taskwarrior-jira-sync` to `~/.task/hooks/on-modify.taskwarrior-jira-sync`
- backs up existing installed files before replacing them
- appends missing Taskwarrior UDA lines to `~/.taskrc` after backing it up
- warns if `~/.local/bin` is not on `PATH`

## Custom UDAs

The installer appends these UDA keys if missing:

```ini
uda.source.type=string
uda.source.label=Source

uda.jira_id.type=string
uda.jira_id.label=Jira ID

uda.jira_url.type=string
uda.jira_url.label=Jira URL

uda.jira_status.type=string
uda.jira_status.label=Jira Status
```

Tasks imported from Jira use `source:jira`. Tags stay available for your own labels such as `+waiting`, `+blocked`, and `+today`.

## Configuration

Configuration is intentionally minimal.

```sh
export TASKW_JIRA_PROJECT=work
export TASKW_JIRA_BASE_URL=https://your-site.atlassian.net/browse
export TASKW_JIRA_LOG=~/.taskwarrior-jira-sync.log
```

All variables are optional. The default project is `work`, and the default log file is `~/.taskwarrior-jira-sync.log`.

Set `TASKW_JIRA_BASE_URL` if the URL returned by `acli` is not browser-friendly for your Jira site. Use the issue browser URL prefix, not only the site root. The importer appends the Jira key:

```text
https://your-site.atlassian.net/browse/SWAT-2824
```

## Import Jira Issues

Run:

```sh
taskwarrior-jira-sync
```

It fetches Jira issues assigned to you and not done:

```sh
acli jira workitem search --jql "assignee = currentUser() AND statusCategory != Done" --json
```

For each issue, it skips creation if a Taskwarrior task with the same `jira_id` already exists. Otherwise it creates:

```sh
task add project:work source:jira jira_id:<KEY> jira_url:<URL> jira_status:<STATUS> "<KEY> <summary>"
```

If `TASKW_JIRA_BASE_URL` is set, `jira_url` is built from that value and the Jira key. Otherwise the importer uses the URL returned by `acli`. If neither is available, `jira_url` is omitted.

## Re-import Jira Issues

The importer skips any Jira issue when `task export` still contains a task with the same `jira_id`.

Deleting a task in Taskwarrior marks it as deleted, but deleted tasks can still remain in Taskwarrior data and appear in export. To re-import the same Jira issue, hard-delete the old Taskwarrior record with purge:

```sh
task <id> delete
task purge
```

Preview carefully before deleting or purging tasks.

## Transition Jira From Taskwarrior

Use Taskwarrior normally:

```sh
task list
task 12 modify jira_status:"In Review"
```

The hook detects Jira-sourced tasks:

- If `jira_status` changes, it transitions Jira to the new value.
- Completing a Taskwarrior task does not transition Jira.

The hook starts the transition asynchronously and does not wait for Jira or network work. Taskwarrior should not fail because Jira is unavailable.

Transition mode calls:

```sh
acli jira workitem transition --key SWAT-2824 --transition "In Review"
```

There is no retry queue. Errors are logged.

## Reports

Configure the sample reports:

```sh
./configure-reports.sh
```

Create a report for pending Jira-imported tasks:

```sh
task config report.jira.description "Jira imported tasks"
task config report.jira.columns "id,project,description,jira_id,jira_status,jira_url"
task config report.jira.labels "ID,Project,Description,Jira ID,Jira Status,Jira URL"
task config report.jira.filter "status:pending source:jira"
task config report.jira.sort "project+,jira_status+,description+"
```

Use it with:

```sh
task jira
```

Create a compact Jira status report:

```sh
task config report.jira_status.description "Jira tasks by status"
task config report.jira_status.columns "id,jira_id,jira_status,description"
task config report.jira_status.labels "ID,Jira ID,Jira Status,Description"
task config report.jira_status.filter "status:pending source:jira"
task config report.jira_status.sort "jira_status+,jira_id+"
```

Use it with:

```sh
task jira_status
```

## Debug Logging

Normal logs include import counts, skipped counts, transition successes, and errors.

Use debug mode for full native command calls:

```sh
taskwarrior-jira-sync --debug
taskwarrior-jira-sync --transition --jira-id SWAT-2824 --status "In Review" --debug
```

Inspect logs:

```sh
tail -f ~/.taskwarrior-jira-sync.log
```

## Cron

Add a cron entry if you want periodic imports:

```cron
*/10 * * * * ~/.local/bin/taskwarrior-jira-sync
```

The hook handles transitions automatically once installed.

## Uninstall

```sh
./uninstall.sh
```

The uninstall script removes the installed binary and hook. It leaves logs and Taskwarrior UDA lines in place.
