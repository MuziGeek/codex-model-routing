# codex-model-routing

[简体中文](./README.zh-CN.md) · [Install](#quick-start) · [Safety](#what-changes)

<p align="center">
  <picture>
    <source media="(max-width: 600px)" srcset="./docs/readme/assets/hero.mobile.svg">
    <img src="./docs/readme/assets/hero.svg" width="100%" alt="Codex routing policy: keep the current main model. Simple tasks stay in the main thread; only worthwhile independent work goes to Luna or Terra. The main thread verifies the result.">
  </picture>
</p>

Keep your current main model. Finish small tasks directly. Delegate to Luna or Terra only when the work is worth splitting.

This Codex Skill helps you audit and apply routing rules and optional subagent defaults. Installing the Skill alone does not change your configuration. It does **not** switch the main model automatically, require Sol Max, or dispatch agents merely because a task involves documents, tests, or multiple files.

## What that looks like

These are policy examples, not recorded runtime results:

| Request | Expected route |
| --- | --- |
| Fix a typo and check the result | Main thread; one complete task |
| Review a small, tightly related change | Main thread; no extra reviewer to meet a quota |
| Research an independent topic while the main thread implements | Luna Medium, if handoff is worthwhile |
| Implement a bounded, independent module | Terra High, if delegation is worthwhile |
| Decide on a risky migration or security change | Main thread owns the core decision |

**Decide whether to delegate before choosing a model.** A work item must have a clear boundary, an independently checkable result, and useful parallel-work or independent-review value that exceeds startup and integration cost. When unsure, work directly. Respect explicit requests to use or avoid subagents.

## Quick start

Requires Codex and **Python 3.11+**; the routing script uses only the standard library.

Ask your agent to install [this Skill](https://github.com/MuziGeek/codex-model-routing), or use the optional Node.js-based installer:

```text
npx skills add MuziGeek/codex-model-routing --skill codex-model-routing
```

Add `--list` for discovery without installation. Alternatively, copy the entire `codex-model-routing/` directory to a Codex-discoverable Skill location.

After installation, ask:

> Use codex-model-routing to audit my current routing setup. Show proposed changes, but do not write anything.

Or run this **from the installed Skill directory**:

```text
python scripts/codex_model_routing.py audit
```

Here, `python` means a verified Python 3.11+ interpreter; use `py -3`, `python3`, or its full path as appropriate. The target is `CODEX_HOME` when set, otherwise the current user's `.codex` directory. To select another target, place `--codex-home "path/to/codex-home"` **before** the subcommand.

## Preview before changing anything

`audit` checks the setup. `plan` shows a candidate diff. Neither writes files. `apply` requires explicit authorization for the current user-level change; the confirmation flag is not a substitute for permission.

For **routing rules only**, leaving all configuration bytes untouched:

```text
python scripts/codex_model_routing.py --rules-only plan
```

After reviewing the diff and authorizing the write:

```text
python scripts/codex_model_routing.py --rules-only apply --confirm-user-level-change
```

`--rules-only` manages the routing block in `AGENTS.md`; it does not read, validate, or write `config.toml`. Use full mode only when you also want to configure subagent defaults.

<details>
<summary>Full mode: routing rules + subagent defaults</summary>

Before writing, check the current official [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference), [model guidance](https://learn.chatgpt.com/docs/models), and the target host's model availability or strict-load result. Stop on incompatibility; do not silently substitute models.

```text
python scripts/codex_model_routing.py plan
```

After reviewing the diff and authorizing the write:

```text
python scripts/codex_model_routing.py apply --confirm-user-level-change
```

The script manages these four fields in the unique root table:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
default_subagent_model = "gpt-5.6-terra"
default_subagent_reasoning_effort = "high"
```

Defaults alone do not prove dispatch. See the official [subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) and verify actual behavior after loading the rules.

</details>

## What changes

- **Main model stays yours.** Neither mode adds or overwrites `model`, `model_reasoning_effort`, or `plan_mode_reasoning_effort`. Missing fields stay missing. Enter Plan manually; existing Plan settings remain yours.
- **Only scoped changes.** Full mode manages the four fields above and one paired routing block in `AGENTS.md`. Plugins, MCP, permissions, service tier, custom agent roles, and other configuration remain unchanged.
- **Recoverable writes.** Changed files are backed up under the target's `backups/` with a SHA-256 manifest. Writes are atomic per file, not a two-file transaction. Reapplying an unchanged setup creates no duplicate backup.
- **Stop instead of guessing.** Conflicting markers, malformed or unsafe-to-edit TOML, and changed unmanaged values block a write. Some valid complex TOML layouts are intentionally rejected. On a write failure, inspect the reported backup and current state before recovery.

## When delegation is worthwhile

Luna Medium handles bounded research, documentation, mechanical changes, or clear tests. Terra High handles ordinary implementation, integration, debugging, or review. Non-high-risk debugging may move from Terra High to XHigh **once**, after a documented failure; missing permissions, dependencies, or a broken environment are not reasons to upgrade.

The rules cap concurrency at three subagents, prohibit nested delegation, and require one writer per shared file or state. Actual dispatch must be announced with its scope and model; the main thread checks the diff and relevant tests before accepting the result. Small direct tasks need no routing ceremony.

## Verify actual behavior

After an authorized update, reopen Codex or start a task that loads the new rules. Check both paths: a small task should stay direct; a genuinely independent workload should be considered for delegation. Confirm the main model remains unchanged and inspect the parent's actual dispatch parameters—not a subagent's self-description.

**Static checks do not prove host loading or live model identity.** There is no automatic routing telemetry. Windows file behavior has been tested; macOS and Linux runtime behavior remains unverified.

For maintainers, run from the repository root:

```text
python codex-model-routing/tests/test_codex_model_routing.py
```

[Routing scenarios](./codex-model-routing/evals/routing-cases.json) · [Standalone usage guide](./codex-model-routing/README.md) · [Skill instructions](./codex-model-routing/SKILL.md)

## License

[MIT](./LICENSE) · Copyright (c) 2026 Muzi.
