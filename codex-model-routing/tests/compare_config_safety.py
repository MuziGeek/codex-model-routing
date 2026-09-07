"""Run deterministic CLI comparisons using an oil-skill-creator run_plan.

Timing and zero model tokens describe subprocess tests only, not the coordinating
Agent's reasoning. Outputs and grading stay in the external evaluation workspace.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_case(run: dict, outputs: Path) -> tuple[list[bool], list[dict]]:
    script = Path(run["skill_path"]) / "scripts" / "codex_model_routing.py"
    records: list[dict] = []
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    def invoke(home: Path, args: list[str]) -> tuple[int, dict]:
        command = [sys.executable, str(script), "--codex-home", str(home), "--json", *args]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=env, timeout=30)
        parsed = json.loads(result.stdout)
        records.append({"command": command, "returncode": result.returncode, "stdout": parsed, "stderr": result.stderr})
        return result.returncode, parsed

    if run["eval_name"] == "multiline-config-safety":
        sources = [
            'description = """\n[not_a_table]\n"""\nkeep = true\n',
            "developer_instructions = '''\nmodel = \"example\"\n'''\n",
            "[agents]\ndescription = '''\nenabled = false\n'''\n",
        ]
        all_safe = True
        failures_untouched = True
        for index, source in enumerate(sources):
            home = outputs / f"home-{index}"
            home.mkdir()
            config, agents = home / "config.toml", home / "AGENTS.md"
            config.write_bytes(source.encode("utf-8"))
            agents.write_bytes(b"# keep\n")
            before = {p.name: p.read_bytes() for p in home.iterdir()}
            code, result = invoke(home, ["apply", "--confirm-user-level-change"])
            if code != 0:
                untouched = before == {p.name: p.read_bytes() for p in home.iterdir() if p.is_file()} and not (home / "backups").exists()
                all_safe &= code == 2 and untouched and result.get("ok") is False
                failures_untouched &= untouched
            else:
                expected = tomllib.loads(source)
                expected.update(model="gpt-5.6-sol", model_reasoning_effort="max", plan_mode_reasoning_effort="max")
                expected.setdefault("agents", {}).update(enabled=True, max_concurrent_threads_per_session=3, default_subagent_model="gpt-5.6-terra", default_subagent_reasoning_effort="high")
                all_safe &= tomllib.loads(config.read_text(encoding="utf-8")) == expected
        return [all_safe, failures_untouched], records

    home = outputs / "home"
    home.mkdir()
    config, agents = home / "config.toml", home / "AGENTS.md"
    config.write_bytes(b'model = "user-selected"\r\nmodel_reasoning_effort = "high"\r\nkeep = true\r\n')
    agents.write_bytes(b"# keep guidance\r\n")
    original = {p.name: p.read_bytes() for p in home.iterdir()}
    if run["eval_name"] == "rules-only-keeps-user-model":
        code, _ = invoke(home, ["--rules-only", "apply", "--confirm-user-level-change"])
        block = agents.read_text(encoding="utf-8")
        kept = code == 0 and config.read_bytes() == original["config.toml"] and block.count("<!-- CODEX_MODEL_ROUTING_BEGIN -->") == 1 and block.count("<!-- CODEX_MODEL_ROUTING_END -->") == 1
        backups = sorted(p.name for p in (home / "backups").iterdir())
        prior_agents = agents.read_bytes()
        code, result = invoke(home, ["--rules-only", "apply", "--confirm-user-level-change"])
        idempotent = code == 0 and result["changed"] is False and agents.read_bytes() == prior_agents and backups == sorted(p.name for p in (home / "backups").iterdir())
        return [kept, idempotent], records
    if run["eval_name"] != "preview-is-read-only":
        raise ValueError("Unknown comparison case")
    code, result = invoke(home, ["plan"])
    return [code == 0 and bool(result.get("diff")), original == {p.name: p.read_bytes() for p in home.iterdir() if p.is_file()} and not (home / "backups").exists()], records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--configuration", choices=["with_skill", "old_skill"], required=True)
    args = parser.parse_args()
    plan_path = args.plan.resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    for run in plan["runs"]:
        if run["configuration"] != args.configuration:
            continue
        run_dir = Path(run["run_dir"]).resolve()
        run_dir.relative_to(plan_path.parent)
        outputs = Path(run["outputs_dir"]).resolve()
        if outputs != run_dir / "outputs" or not outputs.is_dir() or any(outputs.iterdir()):
            raise ValueError("Expected an empty prepared outputs directory")
        if (run_dir / "grading.json").exists() or (run_dir / "timing.json").exists():
            raise ValueError("Refusing to overwrite prior run evidence")
        start = time.perf_counter()
        checks, evidence = run_case(run, outputs)
        duration_ms = (time.perf_counter() - start) * 1000
        if len(checks) != len(run["expectations"]):
            raise ValueError("Unexpected grading contract")
        save(outputs / "result.json", {"checks": checks, "subprocesses": evidence})
        save(run_dir / "grading.json", {"expectations": [{"text": text, "passed": bool(passed), "evidence": "outputs/result.json"} for text, passed in zip(run["expectations"], checks)]})
        save(run_dir / "timing.json", {"total_tokens": 0, "duration_ms": duration_ms, "total_duration_seconds": duration_ms / 1000})
        print(json.dumps({"run": run["run_id"], "checks": checks, "duration_ms": duration_ms}))


if __name__ == "__main__":
    main()
