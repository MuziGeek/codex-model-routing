#!/usr/bin/env python3
"""Audit, preview, and safely apply the managed Codex model-routing policy."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import sys
import tempfile
import tomllib
from typing import Any


TOP_LEVEL_VALUES = {
    "model": '"gpt-5.6-sol"',
    "model_reasoning_effort": '"max"',
    "plan_mode_reasoning_effort": '"max"',
}
AGENT_VALUES = {
    "enabled": "true",
    "max_concurrent_threads_per_session": "3",
    "default_subagent_model": '"gpt-5.6-terra"',
    "default_subagent_reasoning_effort": '"high"',
}
BEGIN = "<!-- CODEX_MODEL_ROUTING_BEGIN -->"
END = "<!-- CODEX_MODEL_ROUTING_END -->"
ROUTING_BLOCK = f"""{BEGIN}
## Codex 模型路由：Sol Max 规划 + 强制显式派发

主线程固定使用 `gpt-5.6-sol` + `max`，负责理解目标、规划、路由、集成和最终验收。Plan 模式由用户在界面中手动进入；进入 Plan 时只规划、不实施。不要自动选择或升级到 `ultra`；本规则中的“最高”固定指 Sol Max。

### 路由优先级

按以下顺序判断；命中后不得用后续规则覆盖：

1. 纯问答、澄清、无需工具的解释、单步微小任务，以及架构、安全、迁移、数据损失、生产风险或需求高度模糊的任务，由 Sol Max 直接完成。
2. 检索、整理、文档、机械修改，以及范围明确且可验证的测试工作，必须至少派发 1 个 `gpt-5.6-luna` + `medium` 子代理执行独立子任务或只读复核。
3. 常规多文件实现、集成、普通调试与代码审查，必须至少派发 1 个 `gpt-5.6-terra` + `high` 子代理执行独立工作项或只读复核。
4. 顽固但非高风险的耦合调试，仅在已有失败证据和原因记录后，才可将 Terra High 升级为 `gpt-5.6-terra` + `xhigh`；最多升级一次。
5. “子代理启动或交接成本高于任务本身”只适用于未命中上述必须派发类别的任务，由 Sol Max 直接完成。

### 可观察调度

- 每次开始执行前，主线程必须先在 commentary 明示：`执行路由`、模型与推理强度、任务范围和选择原因；Sol Max 直接完成时也必须说明直做原因。
- 派发失败必须立即在 commentary 报告失败原因和当前状态；不得静默改由 Sol Max 执行。若任务在现有权限和范围内仍可安全继续，必须先显式声明回退路线后再由 Sol Max 接管。
- 子代理身份以父级实际 `spawn` 参数为准；不得要求子代理自报或自证模型身份。
- 最终回复必须列出实际路由记录：父级派发的模型、任务、结果或失败，以及 Sol Max 完成的差异检查、相关验证和最终验收。

### 调度与验收约束

- 覆盖子代理模型或推理强度时必须使用 `fork_turns="none"`，并传递完整但紧凑的任务包：目标、允许修改范围、约束、验收标准和验证命令。
- 每个子代理任务包都必须明确写明：不得继续派生代理；不得提交、推送、部署、发布、对外发送、扩大权限或扩大任务范围。
- 同时最多运行 3 个子代理，只并行互不重叠的工作项；同一文件、同一共享状态或同一共享运行环境只允许一个写入者，重叠工作必须串行。单文件任务需要独立复核时，子代理与主线程中仅一方可以写入，另一方保持只读。
- 权限不足、依赖缺失或测试环境故障属于环境阻塞，不能通过升级模型规避。
- 主线程必须检查实际差异、父级派发记录、子代理报告和相关测试结果后，才能宣布任务完成；子代理结论不能替代主线程验收。
{END}
"""

HEADER_RE = re.compile(r"^\s*(\[\[?|\[)([^\]]+)(\]\]|\])\s*(?:#.*)?$")
ASSIGNMENT_RE = re.compile(r"^(\s*)([A-Za-z0-9_-]+)\s*=")
MARKER_LINE_RE = {
    BEGIN: re.compile(r"^[ \t]*<!-- CODEX_MODEL_ROUTING_BEGIN -->[ \t]*$", re.MULTILINE),
    END: re.compile(r"^[ \t]*<!-- CODEX_MODEL_ROUTING_END -->[ \t]*$", re.MULTILINE),
}


class RoutingError(RuntimeError):
    """A safe-to-report condition that must prevent a write."""


def default_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    if not path.is_file():
        raise RoutingError(f"目标不是普通文件：{path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RoutingError(f"无法按 UTF-8 读取：{path}") from exc


def line_ending(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def header_rows(lines: list[str]) -> list[tuple[int, str, bool]]:
    rows: list[tuple[int, str, bool]] = []
    for index, line in enumerate(lines):
        match = HEADER_RE.match(line.rstrip("\r\n"))
        if match:
            opening, name, closing = match.groups()
            is_array = opening == "[[" or closing == "]]"
            rows.append((index, name.strip(), is_array))
    return rows


def assignment_positions(lines: list[str], start: int, end: int, names: dict[str, str]) -> dict[str, list[int]]:
    found = {name: [] for name in names}
    for index in range(start, end):
        match = ASSIGNMENT_RE.match(lines[index])
        if match and match.group(2) in found:
            found[match.group(2)].append(index)
    duplicates = [name for name, positions in found.items() if len(positions) > 1]
    if duplicates:
        raise RoutingError("受管键重复，停止修改：" + ", ".join(duplicates))
    return found


def add_missing_assignments(prefix: str, values: dict[str, str], existing: dict[str, list[int]], ending: str) -> str:
    missing = [f"{key} = {value}{ending}" for key, value in values.items() if not existing[key]]
    if not missing:
        return prefix
    if prefix and not prefix.endswith(("\n", "\r")):
        prefix += ending
    return prefix + "".join(missing)


def render_config(original: str) -> str:
    """Return a TOML candidate, refusing layouts that cannot be edited safely."""
    lines = original.splitlines(keepends=True)
    headers = header_rows(lines)
    agent_headers = [(index, is_array) for index, name, is_array in headers if name == "agents"]
    nested_agent_headers = [(index, name, is_array) for index, name, is_array in headers if name.startswith("agents.")]
    if any(is_array for _, is_array in agent_headers):
        raise RoutingError("不支持 [[agents]] 数组表，停止修改")
    if len(agent_headers) > 1:
        raise RoutingError("发现重复 [agents] 表，停止修改")

    try:
        tomllib.loads(original)
    except tomllib.TOMLDecodeError as exc:
        raise RoutingError(f"config.toml 无法解析：{exc}") from exc

    ending = line_ending(original)
    first_header = headers[0][0] if headers else len(lines)
    root_positions = assignment_positions(lines, 0, first_header, TOP_LEVEL_VALUES)
    root = lines[:first_header]
    for name, positions in root_positions.items():
        if positions:
            root[positions[0]] = f"{name} = {TOP_LEVEL_VALUES[name]}{ending}"
    root_text = add_missing_assignments("".join(root), TOP_LEVEL_VALUES, root_positions, ending)
    suffix = "".join(lines[first_header:])
    candidate = root_text + suffix

    if not agent_headers:
        agent_block = f"[agents]{ending}" + "".join(
            f"{key} = {value}{ending}" for key, value in AGENT_VALUES.items()
        )
        if nested_agent_headers:
            insert_at = min(index for index, _, _ in nested_agent_headers)
            candidate = root_text + "".join(lines[first_header:insert_at])
            if candidate and not candidate.endswith(("\n", "\r")):
                candidate += ending
            candidate += agent_block + "".join(lines[insert_at:])
        else:
            if candidate and not candidate.endswith(("\n", "\r")):
                candidate += ending
            candidate += agent_block
        try:
            tomllib.loads(candidate)
        except tomllib.TOMLDecodeError as exc:
            raise RoutingError(f"候选 config.toml 无法解析，停止写入：{exc}") from exc
        return candidate

    # Recompute offsets after root changes by rendering the agents table from the original suffix.
    agent_index = agent_headers[0][0]
    next_headers = [index for index, _, _ in headers if index > agent_index]
    agent_end = next_headers[0] if next_headers else len(lines)
    before_agent = "".join(lines[first_header:agent_index])
    agent_lines = lines[agent_index:agent_end]
    positions = assignment_positions(agent_lines, 1, len(agent_lines), AGENT_VALUES)
    for name, indexes in positions.items():
        if indexes:
            agent_lines[indexes[0]] = f"{name} = {AGENT_VALUES[name]}{ending}"
    agent_text = add_missing_assignments("".join(agent_lines), AGENT_VALUES, positions, ending)
    after_agent = "".join(lines[agent_end:])
    candidate = root_text + before_agent + agent_text + after_agent
    try:
        tomllib.loads(candidate)
    except tomllib.TOMLDecodeError as exc:
        raise RoutingError(f"候选 config.toml 无法解析，停止写入：{exc}") from exc
    return candidate


def render_agents(original: str) -> str:
    raw_begin = original.count(BEGIN)
    raw_end = original.count(END)
    begin_matches = list(MARKER_LINE_RE[BEGIN].finditer(original))
    end_matches = list(MARKER_LINE_RE[END].finditer(original))
    if raw_begin != len(begin_matches) or raw_end != len(end_matches):
        raise RoutingError("路由标记必须独占一行，停止修改")
    if raw_begin == 0 and raw_end == 0:
        ending = line_ending(original)
        base = original
        if base and not base.endswith(("\n", "\r")):
            base += ending
        return base + (ending if base else "") + ROUTING_BLOCK.replace("\n", ending)
    if raw_begin != 1 or raw_end != 1:
        raise RoutingError("路由标记不是唯一成对标记，停止修改")
    begin, end = begin_matches[0], end_matches[0]
    if begin.start() >= end.start():
        raise RoutingError("路由标记顺序冲突或不配对，停止修改")
    ending = line_ending(original)
    replacement = ROUTING_BLOCK.replace("\n", ending)
    end_of_line = end.end()
    if end_of_line < len(original) and original[end_of_line:end_of_line + 1] == "\n":
        end_of_line += 1
    return original[:begin.start()] + replacement + original[end_of_line:]


def unified_diff(before: str, after: str, filename: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"{filename} (current)", tofile=f"{filename} (managed)",
        )
    )


def build_candidates(codex_home: Path) -> tuple[dict[str, Path], dict[str, str], dict[str, str], str]:
    paths = {"config.toml": codex_home / "config.toml", "AGENTS.md": codex_home / "AGENTS.md"}
    current = {name: read_text(path) for name, path in paths.items()}
    candidates = {"config.toml": render_config(current["config.toml"]), "AGENTS.md": render_agents(current["AGENTS.md"])}
    diff = "".join(
        unified_diff(current[name], candidates[name], name)
        for name in ("config.toml", "AGENTS.md")
        if current[name] != candidates[name]
    )
    return paths, current, candidates, diff


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_backup(codex_home: Path, paths: dict[str, Path]) -> Path:
    root = codex_home / "backups"
    root.mkdir(parents=True, exist_ok=True)
    base = "codex-model-routing-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = root / base
    suffix = 1
    while destination.exists():
        destination = root / f"{base}-{suffix}"
        suffix += 1
    destination.mkdir()
    manifest: list[dict[str, Any]] = []
    for name, source in paths.items():
        data = source.read_bytes() if source.exists() else b""
        (destination / name).write_bytes(data)
        manifest.append({"file": name, "existed": source.exists(), "sha256": sha256_bytes(data)})
    (destination / "SHA256SUMS.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            shutil.copymode(path, temporary_path)
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def output(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if not result["ok"]:
        print("停止：" + result["error"])
        return
    print(f"{result['mode']}：{'发现变更' if result['changed'] else '已符合策略，无需变更'}")
    if result.get("backup"):
        print("备份：" + result["backup"])
    if result.get("diff"):
        print(result["diff"], end="" if result["diff"].endswith("\n") else "\n")
    if result.get("runtime_note"):
        print("运行时：" + result["runtime_note"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=default_codex_home())
    parser.add_argument("--json", action="store_true", dest="as_json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audit")
    subparsers.add_parser("plan")
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--confirm-user-level-change", action="store_true")
    args = parser.parse_args(argv)
    codex_home = args.codex_home.expanduser()
    try:
        paths, current, candidates, diff = build_candidates(codex_home)
        changed = bool(diff)
        if args.command == "apply" and not args.confirm_user_level_change:
            raise RoutingError("apply 需要 --confirm-user-level-change；还需要当前用户对用户级变更的明确授权")
        result: dict[str, Any] = {
            "ok": True,
            "mode": args.command,
            "codex_home": str(codex_home),
            "changed": changed,
            "diff": diff,
            "runtime_note": "静态配置未证明运行时已加载或子代理已实际派发；重新打开 Codex 后执行新的只读验证。",
        }
        if args.command == "apply" and changed:
            backup = create_backup(codex_home, paths)
            result["backup"] = str(backup)
            try:
                for name in ("config.toml", "AGENTS.md"):
                    atomic_write(paths[name], candidates[name])
            except Exception as exc:
                raise RoutingError(f"写入失败；未自动恢复。可人工检查备份：{backup}。原因：{exc}") from exc
        output(result, args.as_json)
        return 0
    except RoutingError as exc:
        result = {"ok": False, "mode": args.command, "codex_home": str(codex_home), "changed": False, "error": str(exc)}
        output(result, args.as_json)
        return 2


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        raise SystemExit("需要 Python 3.11+（tomllib）")
    raise SystemExit(main())
