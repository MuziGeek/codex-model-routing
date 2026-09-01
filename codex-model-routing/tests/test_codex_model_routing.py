from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import tomllib
import unittest


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
        self.assertIn("强制显式派发", agents)
        self.assertIn("必须至少派发 1 个 `gpt-5.6-luna`", agents)
        self.assertIn("必须至少派发 1 个 `gpt-5.6-terra`", agents)
        self.assertIn('fork_turns="none"', agents)
        self.assertIn("不得静默改由 Sol Max 执行", agents)

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


if __name__ == "__main__":
    unittest.main()
