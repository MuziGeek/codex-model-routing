---
name: codex-model-routing
description: 配置、审计、修复和验证 Codex 的 Sol Max 主线程与 Luna/Terra 子代理模型路由。用户要求安装、更新、排查、恢复或验证 config.toml 与全局 AGENTS.md 中的模型路由和可观察派发规则时使用。不要用于普通项目任务、单次模型选择、与模型路由无关的 Codex 设置，或替代实际执行子代理任务。
---

# Codex 模型路由

这个 Skill 将主线程与子代理的模型策略落实为可审计的用户级配置和行为规则：Sol Max 负责规划、路由和验收；Luna Medium 处理范围明确的检索、整理、文档和机械任务；Terra High 处理常规多文件实现、集成、调试和审查。Terra XHigh 只可对非高风险顽固调试升级一次；架构、安全、迁移、数据损失、生产风险和高度模糊的判断留在 Sol，且不自动使用 Ultra。

使用前先判断用户要的是哪一种模式；不要把查看、解释或审计升级为写入。

## 模式

### Explain

用于解释当前策略、模型职责、配置限制或运行时边界。读取 [参考设计](references/routing-design.md)；若要对当前机器作出结论，再运行脚本 `audit`。不改文件。

### Audit

用于检查某个 Codex Home 中的 `config.toml` 和 `AGENTS.md` 是否符合策略。先读取 [参考设计](references/routing-design.md)，再运行：

```text
python scripts/codex_model_routing.py --codex-home <目录> audit
```

未提供目录时脚本使用 `CODEX_HOME`，否则使用当前用户主目录下的 `.codex`。可添加 `--json` 供其他工具读取。审计应报告受管字段、标记块、冲突、待修改 diff 与尚未验证的运行时状态；它不写入文件。

### Apply or repair

用于用户明确要求写入或修复用户级配置时。先读取 [参考设计](references/routing-design.md)，再执行 `plan`，审阅其 diff 和冲突：

```text
python scripts/codex_model_routing.py --codex-home <目录> plan
```

写入前核对当前官方配置参考与本机实际模型目录或严格加载结果。若官方文档与本机运行时对目标模型或推理强度的支持结论不一致，先向用户报告差异；不得静默降级、替换模型或继续写入。

只有用户明确授权此次用户级变更后，才可执行：

```text
python scripts/codex_model_routing.py --codex-home <目录> apply --confirm-user-level-change
```

脚本会在写入前解析候选 TOML、检查唯一 `[agents]` 表与唯一成对的路由标记，并备份原始 `config.toml`、`AGENTS.md` 和 SHA-256 清单。它只管理既定字段与标记块，保留其他内容。`plan` 绝不写入；无变更时 `apply` 不创建重复备份。

## 运行时验收

文件通过审计不等于桌面端已加载配置。写入后让用户重启或重新打开 Codex，并在新的只读小任务中验证：主线程模型、Plan 推理强度、默认子代理和实际显式派发是否符合当前宿主可用模型。模型清单、宿主版本与桌面端行为可能漂移；不要用旧记录、PATH 中的另一套 CLI 或子代理自述代替此验证。

若宿主不支持目标模型、运行时显示与配置不同、或用户未授权写入，停止并报告证据。配置冲突、重复 `[agents]`、不配对或冲突标记、无法解析的候选 TOML、写入失败也必须停止。写入失败后只报告备份位置；不得自动恢复或覆盖可能由升级迁移的配置。恢复旧配置、改插件/MCP/权限或更改服务层级是单独请求。

## 输出

报告所用模式、Codex Home、审计/计划状态、受管差异或冲突、备份位置（若有）、运行的命令和结果，以及仍需用户在运行时确认的项目。不要声称模型已实际派发，除非已完成新的运行时验证。

## 资源导航

- 解释策略、评估兼容性或准备写入前：读取 [参考设计](references/routing-design.md)。
- 需要确定性审计、计划或写入时：运行 [路由脚本](scripts/codex_model_routing.py)。
