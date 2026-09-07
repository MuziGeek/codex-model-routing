from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "codex_model_routing.py"
SPEC = importlib.util.spec_from_file_location("codex_model_routing", SCRIPT)
assert SPEC and SPEC.loader
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)


class CodexModelRoutingTests(unittest.TestCase):
    def make_home(self, config: str = "", agents: str = "") -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory()
        home = Path(temporary.name)
        if config:
            (home / "config.toml").write_text(config, encoding="utf-8")
        if agents:
            (home / "AGENTS.md").write_text(agents, encoding="utf-8")
        return temporary

    def run_main(self, home: Path, *arguments: str) -> tuple[int, str]:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = routing.main(["--codex-home", str(home), *arguments])
        return status, stream.getvalue()

    def test_apply_preserves_unknown_configuration_and_agents_content(self) -> None:
        temporary = self.make_home(
            'custom_option = "keep"\n[experimental]\nfeature = true\n',
            "# Existing guidance\nKeep this line.\n",
        )
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)

        status, _ = self.run_main(home, "apply", "--confirm-user-level-change")

        self.assertEqual(0, status)
        config = (home / "config.toml").read_text(encoding="utf-8")
        agents = (home / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn('custom_option = "keep"', config)
        self.assertIn("[experimental]\nfeature = true", config)
        self.assertIn('model = "gpt-5.6-sol"', config)
        self.assertIn("[agents]", config)
        self.assertIn("Keep this line.", agents)
        self.assertIn(routing.BEGIN, agents)
        self.assertTrue(agents.endswith(routing.ROUTING_BLOCK))
        self.assertEqual(1, agents.count(routing.BEGIN))
        self.assertEqual(1, agents.count(routing.END))

    def test_custom_agent_table_is_preserved(self) -> None:
        config = '[agents.reviewer]\ndescription = "keep"\nconfig_file = "reviewer.toml"\n'
        temporary = self.make_home(config, "# guidance\n")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)

        status, _ = self.run_main(home, "apply", "--confirm-user-level-change")

        self.assertEqual(0, status)
        updated = (home / "config.toml").read_text(encoding="utf-8")
        parsed = tomllib.loads(updated)
        self.assertEqual("keep", parsed["agents"]["reviewer"]["description"])
        self.assertEqual("reviewer.toml", parsed["agents"]["reviewer"]["config_file"])
        self.assertEqual("gpt-5.6-terra", parsed["agents"]["default_subagent_model"])

    def test_apply_is_idempotent_and_does_not_create_another_backup(self) -> None:
        temporary = self.make_home("model = \"other\"\n", "# guidance\n")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)

        first, _ = self.run_main(home, "apply", "--confirm-user-level-change")
        backups = list((home / "backups").iterdir())
        second, output = self.run_main(home, "apply", "--confirm-user-level-change")

        self.assertEqual(0, first)
        self.assertEqual(0, second)
        self.assertIn("无需变更", output)
        self.assertEqual(backups, list((home / "backups").iterdir()))

    def test_apply_creates_original_file_backups_and_manifest(self) -> None:
        temporary = self.make_home("feature = true\n", "# guidance\n")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)

        status, _ = self.run_main(home, "apply", "--confirm-user-level-change")

        self.assertEqual(0, status)
        backups = list((home / "backups").iterdir())
        self.assertEqual(1, len(backups))
        backup = backups[0]
        self.assertEqual("feature = true\n", (backup / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual("# guidance\n", (backup / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertTrue((backup / "SHA256SUMS.json").is_file())

    def test_duplicate_agents_table_is_rejected_without_writing(self) -> None:
        config = "[agents]\nenabled = true\n[other]\nx = 1\n[agents]\nenabled = false\n"
        temporary = self.make_home(config, "# original\n")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)

        status, output = self.run_main(home, "plan")

        self.assertEqual(2, status)
        self.assertIn("重复 [agents]", output)
        self.assertEqual(config, (home / "config.toml").read_text(encoding="utf-8"))
        self.assertFalse((home / "backups").exists())

    def test_conflicting_markers_are_rejected_without_writing(self) -> None:
        agents = "# existing\n" + routing.BEGIN + "\n"
        temporary = self.make_home("feature = true\n", agents)
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)

        status, output = self.run_main(home, "plan")

        self.assertEqual(2, status)
        self.assertIn("不是唯一成对标记", output)
        self.assertEqual(agents, (home / "AGENTS.md").read_text(encoding="utf-8"))

    def test_plan_only_outputs_diff_without_writing(self) -> None:
        temporary = self.make_home("feature = true\n", "# existing\n")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        before_config = (home / "config.toml").read_text(encoding="utf-8")
        before_agents = (home / "AGENTS.md").read_text(encoding="utf-8")

        status, output = self.run_main(home, "plan")

        self.assertEqual(0, status)
        self.assertIn("config.toml (managed)", output)
        self.assertEqual(before_config, (home / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual(before_agents, (home / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertFalse((home / "backups").exists())

    def test_rules_only_upgrades_old_policy_preserving_surrounding_guidance(self) -> None:
        prefix, suffix = "# User guidance\n保留前文。\n\n", "\n# Project guidance\n保留后文。\n"
        old = prefix + routing.BEGIN + "\n旧版强制派发规则\n" + routing.END + "\n" + suffix
        temporary = self.make_home('model = "gpt-6-astra"\nmodel_reasoning_effort = "high"\n', old)
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        config_bytes = (home / "config.toml").read_bytes()
        agents_bytes = (home / "AGENTS.md").read_bytes()

        status, _ = self.run_main(home, "--rules-only", "apply", "--confirm-user-level-change")

        self.assertEqual(0, status)
        self.assertEqual(prefix + routing.ROUTING_BLOCK + suffix, (home / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(config_bytes, (home / "config.toml").read_bytes())
        backup = next((home / "backups").iterdir())
        self.assertEqual(old, (backup / "AGENTS.md").read_text(encoding="utf-8"))
        manifest = json.loads((backup / "SHA256SUMS.json").read_text(encoding="utf-8"))
        self.assertEqual(["AGENTS.md"], [entry["file"] for entry in manifest])
        self.assertEqual(routing.sha256_bytes(agents_bytes), manifest[0]["sha256"])
        self.assertEqual(agents_bytes, (backup / "AGENTS.md").read_bytes())

    def test_rules_only_plan_and_audit_are_read_only_and_scoped(self) -> None:
        temporary = self.make_home('model = "custom"\n', "# guidance\n")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        before = {path.name: path.read_bytes() for path in home.iterdir()}
        for command in ("plan", "audit"):
            status, output = self.run_main(home, "--rules-only", "--json", command)
            result = json.loads(output)
            self.assertEqual(0, status)
            self.assertEqual("rules-only", result["scope"])
            self.assertNotIn("config.toml (", result["diff"])
            self.assertEqual(before, {path.name: path.read_bytes() for path in home.iterdir()})

    def test_rules_only_is_idempotent(self) -> None:
        temporary = self.make_home(agents=routing.ROUTING_BLOCK)
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        status, output = self.run_main(home, "--rules-only", "--json", "apply", "--confirm-user-level-change")
        self.assertEqual(0, status)
        self.assertFalse(json.loads(output)["changed"])
        self.assertFalse((home / "backups").exists())
        self.assertFalse((home / "config.toml").exists())

    def test_rules_only_does_not_read_or_create_config(self) -> None:
        for content in (None, b"invalid TOML \xff\r\n"):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as folder:
                home = Path(folder)
                config = home / "config.toml"
                if content is not None:
                    config.write_bytes(content)
                status, _ = self.run_main(home, "--rules-only", "apply", "--confirm-user-level-change")
                self.assertEqual(0, status)
                self.assertEqual(content, config.read_bytes() if config.exists() else None)

    def test_rules_only_rejects_conflicting_markers_without_writes(self) -> None:
        temporary = self.make_home(agents=routing.BEGIN + "\n")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        before = (home / "AGENTS.md").read_bytes()
        status, _ = self.run_main(home, "--rules-only", "apply", "--confirm-user-level-change")
        self.assertEqual(2, status)
        self.assertEqual(before, (home / "AGENTS.md").read_bytes())
        self.assertFalse((home / "backups").exists())

    def test_rules_only_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            status, _ = self.run_main(home, "--rules-only", "apply")
            self.assertEqual(2, status)
            self.assertEqual([], list(home.iterdir()))

    def test_rules_only_preserves_lf_and_crlf_outside_managed_block(self) -> None:
        for ending in ("\n", "\r\n"):
            with self.subTest(ending=ending), tempfile.TemporaryDirectory() as folder:
                home = Path(folder)
                prefix = "# Keep prefix" + ending + ending
                suffix = ending + "# Keep suffix" + ending
                old = prefix + routing.BEGIN + ending + "old" + ending + routing.END + ending + suffix
                path = home / "AGENTS.md"
                path.write_bytes(old.encode("utf-8"))
                status, _ = self.run_main(home, "--rules-only", "apply", "--confirm-user-level-change")
                self.assertEqual(0, status)
                expected = prefix + routing.ROUTING_BLOCK.replace("\n", ending) + suffix
                self.assertEqual(expected.encode("utf-8"), path.read_bytes())
                backups = list((home / "backups").iterdir())
                status, _ = self.run_main(home, "--rules-only", "apply", "--confirm-user-level-change")
                self.assertEqual(0, status)
                self.assertEqual(backups, list((home / "backups").iterdir()))

    def test_full_modes_reject_multiline_false_headers_and_assignments_without_writes(self) -> None:
        configs = [
            'description = """\n[not_a_table]\n"""\nkeep = true\n',
            "developer_instructions = '''\nmodel = \"example\"\n'''\n",
            "[agents]\ndescription = '''\nenabled = false\n'''\n",
            'description = """\n[agents]\nenabled = false\n"""\n',
        ]
        for config in configs:
            tomllib.loads(config)
            for command in ("audit", "plan", "apply"):
                with self.subTest(config=config, command=command), self.make_home(config, "# keep\n") as folder:
                    home = Path(folder)
                    before = {path.name: path.read_bytes() for path in home.iterdir()}
                    args = [command] + (["--confirm-user-level-change"] if command == "apply" else [])
                    status, _ = self.run_main(home, *args)
                    self.assertEqual(2, status)
                    self.assertEqual(before, {path.name: path.read_bytes() for path in home.iterdir()})

    def test_full_apply_preserves_benign_multiline_and_special_toml_values(self) -> None:
        config = 'description = """\nordinary text\n"""\nnumber = nan\nvalues = [inf, -inf, nan]\ndate = 2026-01-01\n'
        with self.make_home(config, "# guidance\n") as folder:
            home = Path(folder)
            status, _ = self.run_main(home, "apply", "--confirm-user-level-change")
            self.assertEqual(0, status)
            before = tomllib.loads(config)
            after = tomllib.loads((home / "config.toml").read_text(encoding="utf-8"))
            for key, value in before.items():
                self.assertTrue(routing.same_toml_value(value, after[key]))
            self.assertEqual("gpt-5.6-sol", after["model"])

    def test_semantic_guard_rejects_unknown_value_mutation_before_backup(self) -> None:
        with self.make_home('keep = true\n', "# guidance\n") as folder:
            home = Path(folder)
            before = {path.name: path.read_bytes() for path in home.iterdir()}
            original = routing.add_missing_assignments
            def corrupt(prefix, values, existing, ending):
                return original(prefix, values, existing, ending).replace("keep = true", "keep = false")
            with mock.patch.object(routing, "add_missing_assignments", side_effect=corrupt):
                status, _ = self.run_main(home, "apply", "--confirm-user-level-change")
            self.assertEqual(2, status)
            self.assertEqual(before, {path.name: path.read_bytes() for path in home.iterdir()})

    def test_semantic_guard_rejects_missing_real_model_even_if_toml_parses(self) -> None:
        with self.make_home(agents="# guidance\n") as folder:
            home = Path(folder)
            original = routing.add_missing_assignments
            def omit_model(prefix, values, existing, ending):
                result = original(prefix, values, existing, ending)
                return result.replace('model = "gpt-5.6-sol"' + ending, "")
            with mock.patch.object(routing, "add_missing_assignments", side_effect=omit_model):
                status, _ = self.run_main(home, "apply", "--confirm-user-level-change")
            self.assertEqual(2, status)
            self.assertFalse((home / "config.toml").exists())
            self.assertFalse((home / "backups").exists())


if __name__ == "__main__":
    unittest.main()
