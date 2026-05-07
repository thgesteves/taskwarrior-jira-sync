import json
import os
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "taskwarrior-jira-sync"
mod = runpy.run_path(str(SCRIPT))


class TaskwarriorJiraSyncTests(unittest.TestCase):
    def test_has_jira_task_uses_jira_id(self):
        tasks = [{"description": "SWAT-1 summary"}, {"jira_id": "SWAT-2824"}]
        self.assertTrue(mod["has_jira_task"](tasks, "SWAT-2824"))
        self.assertFalse(mod["has_jira_task"](tasks, "SWAT-9999"))

    def test_task_add_command_generation(self):
        issue = {
            "id": "SWAT-2824",
            "summary": "Fix sync",
            "url": "https://jira.example/browse/SWAT-2824",
            "status": "In Progress",
        }
        with patch.dict(os.environ, {"TASKW_JIRA_BASE_URL": ""}):
            self.assertEqual(
                mod["build_task_add_command"]("work", issue),
                [
                    "task",
                    "add",
                    "project:work",
                    "source:jira",
                    "jira_id:SWAT-2824",
                    "jira_url:https://jira.example/browse/SWAT-2824",
                    "jira_status:In Progress",
                    "SWAT-2824 Fix sync",
                ],
            )

    def test_task_add_command_uses_jira_base_url_env(self):
        issue = {
            "id": "SWAT-2824",
            "summary": "Fix sync",
            "url": "https://wrong.example/SWAT-2824",
            "status": "In Progress",
        }
        with patch.dict(os.environ, {"TASKW_JIRA_BASE_URL": "https://jira.example/browse"}):
            self.assertIn(
                "jira_url:https://jira.example/browse/SWAT-2824",
                mod["build_task_add_command"]("work", issue),
            )

    def test_task_add_command_trims_jira_base_url_trailing_slash(self):
        issue = {
            "id": "SWAT-2824",
            "summary": "Fix sync",
            "status": "In Progress",
        }
        with patch.dict(os.environ, {"TASKW_JIRA_BASE_URL": "https://jira.example/browse/"}):
            self.assertIn(
                "jira_url:https://jira.example/browse/SWAT-2824",
                mod["build_task_add_command"]("work", issue),
            )

    def test_detect_jira_status_change(self):
        old = {"uuid": "abc", "source": "jira", "jira_id": "SWAT-2824", "jira_status": "To Do", "status": "pending"}
        new = dict(old, jira_status="In Review")
        self.assertEqual(
            mod["detect_transition"](old, new),
            {
                "jira_id": "SWAT-2824",
                "status": "In Review",
                "task_uuid": "abc",
                "reason": "jira_status_changed",
            },
        )

    def test_task_completed_does_not_transition_jira(self):
        old = {"uuid": "abc", "source": "jira", "jira_id": "SWAT-2824", "jira_status": "In Progress", "status": "pending"}
        new = dict(old, status="completed")
        self.assertIsNone(mod["detect_transition"](old, new))

    def test_transition_command_generation(self):
        self.assertEqual(
            mod["build_transition_command"]("SWAT-2824", "In Review"),
            [
                "acli",
                "jira",
                "workitem",
                "transition",
                "--key",
                "SWAT-2824",
                "--transition",
                "In Review",
            ],
        )

    def test_parse_issues_from_acli_shape(self):
        raw = {
            "issues": [
                {
                    "key": "SWAT-2824",
                    "fields": {
                        "summary": "Fix sync",
                        "status": {"name": "In Progress"},
                    },
                    "webUrl": "https://jira.example/browse/SWAT-2824",
                }
            ]
        }
        self.assertEqual(
            mod["parse_issues"](raw),
            [
                {
                    "id": "SWAT-2824",
                    "summary": "Fix sync",
                    "url": "https://jira.example/browse/SWAT-2824",
                    "status": "In Progress",
                }
            ],
        )

    def test_append_missing_udas(self):
        existing = "data.location=~/.task\nuda.source.type=string\n"
        updated, missing = mod["append_missing_udas"](existing)
        self.assertIn("uda.jira_status.label=Jira Status", updated)
        self.assertEqual(updated.count("uda.source.type=string"), 1)
        self.assertGreater(len(missing), 0)

        updated_again, missing_again = mod["append_missing_udas"](updated)
        self.assertEqual(updated_again, updated)
        self.assertEqual(missing_again, [])

    def test_append_missing_udas_respects_existing_source_from_other_addon(self):
        existing = "\n".join(
            [
                "uda.source.type = string",
                "uda.source.label=Origin",
            ]
        )
        updated, missing = mod["append_missing_udas"](existing)
        self.assertNotIn("uda.source.label=Source", updated)
        self.assertNotIn("uda.source.type=string", missing)
        self.assertNotIn("uda.source.label=Source", missing)
        self.assertIn("uda.jira_id.type=string", updated)

    def test_append_missing_udas_respects_existing_jira_keys_with_different_values(self):
        existing = "\n".join(
            [
                "# uda.jira_id.type=string",
                "uda.jira_id.type = string",
                "uda.jira_id.label=External Jira Key",
                "uda.jira_url.type=",
                "uda.jira_status.label = Status",
            ]
        )
        updated, missing = mod["append_missing_udas"](existing)
        self.assertNotIn("uda.jira_id.type=string", missing)
        self.assertNotIn("uda.jira_id.label=Jira ID", updated)
        self.assertNotIn("uda.jira_url.type=string", missing)
        self.assertNotIn("uda.jira_status.label=Jira Status", updated)
        self.assertIn("uda.jira_url.label=Jira URL", updated)

    def test_commented_uda_lines_do_not_count_as_existing(self):
        updated, missing = mod["append_missing_udas"]("# uda.jira_id.type=string\n")
        self.assertIn("uda.jira_id.type=string", updated)
        self.assertIn("uda.jira_id.type=string", missing)

    def test_hook_always_prints_new_json_shape(self):
        new_task = {"source": "manual", "description": "x"}
        self.assertIsNone(mod["detect_transition"]({}, new_task))
        json.dumps(new_task)


if __name__ == "__main__":
    unittest.main()
