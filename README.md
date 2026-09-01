# codex-model-routing

[简体中文](./README.zh-CN.md)

<p align="center">
  <picture>
    <source media="(max-width: 600px)" srcset="./docs/readme/assets/hero.mobile.svg">
    <img src="./docs/readme/assets/hero.svg" width="100%" alt="codex-model-routing routing map: Sol Max plans, routes, and verifies; Luna Medium handles clear repeatable work; Terra High handles everyday implementation; risk or ambiguity returns to Sol; all paths lead to acceptance.">
  </picture>
</p>

An auditable Codex Skill for setting up a deliberate model-routing policy: a Sol Max main thread plans, routes, and verifies; Luna Medium takes clear, repeatable work; Terra High takes everyday implementation. It is a configuration and behavior-rule companion—not Codex-native automatic switching of the root model.

## Evidence before promises

The included payload exposes three deliberate modes: `audit`, `plan`, and `apply`.

- `audit` inspects the managed model fields and the routing block without writing.
- `plan` shows the candidate diff without writing.
- `apply` requires an explicit user-level confirmation flag, writes atomically, and records original files plus a SHA-256 manifest in `backups/` when there is a change.

It stops on malformed TOML, duplicate or array-form root `[agents]` tables, conflicting routing markers, and other unsafe states. It preserves unknown configuration rather than replacing the whole file.

## How routing really works

Codex configuration can set defaults for subagent model and reasoning effort. Actual subagent dispatch is a behavior decision: Codex dispatches when directly asked, or when applicable project or Skill instructions require it. An explicit `spawn` model/reasoning override takes precedence over defaults.

This Skill writes the accompanying `AGENTS.md` routing rule so that the model choice is observable and reviewable. It does not claim automatic routing telemetry, a release workflow, or a runtime dispatch that has not been independently observed.

The division follows OpenAI's current guidance for [Sol, Terra, Luna, Max, and Ultra](https://learn.chatgpt.com/docs/models), while the dispatch behavior and override precedence come from the official [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) documentation. Supported configuration keys must always be checked against the current [Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference).

| Work shape | Intended handling |
| --- | --- |
| Architecture, security, migration, data-loss, production risk, or ambiguity | Keep the decision in Sol Max |
| Clear, repeatable research, organization, documentation, or mechanical work | Explicitly dispatch Luna Medium |
| Everyday multi-file implementation, integration, debugging, or review | Explicitly dispatch Terra High |
| Non-high-risk coupled debugging with prior failure evidence | Escalate Terra once to XHigh, then re-evaluate |

## Install and take the first safe action

Install this Skill from its GitHub source with the Codex Skill Installer:

<https://github.com/MuziGeek/codex-model-routing/tree/main/codex-model-routing>

Use the Installer's current flow as the source of truth, and verify that it resolves the `codex-model-routing` directory with its `SKILL.md`, `scripts`, and `references` intact. If an installer is unavailable, manually copy that whole directory into a Codex-discoverable Skill location; do not invent an `npx` command.

Then begin with a read-only audit from the installed Skill directory:

```text
python scripts/codex_model_routing.py --codex-home <Codex Home> audit
```

`CODEX_HOME` is used when set; otherwise the script uses the current user's `.codex` directory. Supplying `--codex-home` is useful for an isolated test directory.

## Plan before apply

Only use a write after reviewing the current plan and receiving explicit authorization for this user-level change:

```text
python scripts/codex_model_routing.py --codex-home <Codex Home> plan
python scripts/codex_model_routing.py --codex-home <Codex Home> apply --confirm-user-level-change
```

Before every write, re-check both the current official Codex configuration reference and the target host's actually available models or strict-load result. Model support and allowed reasoning efforts can drift between app versions, documentation, and hosts. A passing static plan is not permission to apply on every version.

> **Compatibility gate:** the current public configuration reference lists `plan_mode_reasoning_effort` only through `xhigh`, while some desktop model catalogs expose `max` at the model level. This payload's target policy includes `plan_mode_reasoning_effort = "max"`. Do not apply it unless the target host accepts that value; stop and report the drift instead of silently downgrading it.

## Verify, then trust

After an authorized write, reopen Codex and perform a new, read-only runtime check of the main-thread model, plan reasoning effort, default subagent settings, and any explicitly requested dispatch. Static configuration checks do not prove that the desktop host loaded a file or ran a task with the intended model.

Run the payload tests from this repository root:

```text
python codex-model-routing/tests/test_codex_model_routing.py
```

## Boundaries

- The payload manages three top-level model fields, four fields in the unique root `[agents]` table, and one paired routing block in `AGENTS.md`.
- It does not change plugins, MCP, permissions, service tiers, official `[agents.<role>]` subtables, or other unknown configuration.
- Windows behavior has been checked. Linux and macOS have only static compatibility design coverage, not runtime validation.
- The public model/configuration documentation and the target host must be rechecked before writing. In particular, reasoning-effort availability is a drift point.
- This README does not make a release claim and no automatic routing telemetry is provided.

## License

Released under the [MIT License](./LICENSE). Copyright (c) 2026 Muzi.

For the exact user-level behavior and safety conditions, read the installed [Skill README](./codex-model-routing/README.md) and [SKILL.md](./codex-model-routing/SKILL.md).
