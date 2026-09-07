---
name: codex-model-routing
description: 配置、审计、修复和验证 Codex 的当前主线程与 Luna/Terra 子代理模型路由。用户要求安装、更新、排查、恢复或验证 config.toml 与全局 AGENTS.md 中的模型路由和可观察派发规则时使用。不要用于普通项目任务、单次模型选择、与模型路由无关的 Codex 设置，或替代实际执行子代理任务。
license: MIT
compatibility: Codex 专用；脚本需要 Python 3.11+ 标准库，Windows 已实测，macOS/Linux 未实测。离线可审计本地文件，运行时派发依赖宿主子代理能力。
---

# Codex 模型路由

这个 Skill 将主线程与子代理的模型策略落实为可审计的用户级配置和行为规则。主线程沿用当前任务实际使用的模型和推理强度，不设固定型号；所有模式都不新增或覆盖主模型及 Plan 设置。简单任务默认直做；只有独立工作或复核的收益高于交接成本时才派发，然后按任务性质选 Luna Medium 或 Terra High。非高风险顽固调试在 Terra High 失败后最多升级一次至 XHigh；高风险核心判断留在主线程，不自动使用 Ultra。

## 拆分门槛

先判断是否值得派发，再选择模型。工具调用、文档、测试、多文件这些标签本身都不触发派发；读取、修改和验证同一个小目标属于一个闭环。不要为配额额外拆出复核任务。只有可独立验收、能与主线程有用工作并行或值得独立复核、且收益超过启动与集成成本时才派发；不确定时直做。尊重用户明确要求使用或不使用子代理，安全与权限边界始终有效。简单任务直做无需额外路由宣告。

使用前先判断用户要的是哪一种模式；不要把查看、解释或审计升级为写入。

先找到并确认 Python 3.11+ 解释器。下文 `python` 表示该解释器；Windows 可检测 `py -3`，macOS/Linux 可检测 `python3`，不可用时使用已验证的解释器路径，不自动安装系统依赖。

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

如果用户只要求优化派发行为、保留模型选择，使用 `--rules-only`，不要执行完整配置修复：

```text
python scripts/codex_model_routing.py --codex-home <目录> --rules-only plan
python scripts/codex_model_routing.py --codex-home <目录> --rules-only apply --confirm-user-level-change
```

此模式只检查、备份和更新 `AGENTS.md`，不读取、不验证也不写入 `config.toml`；不会证明现有模型配置有效。它不需要重新选择模型，但仍须先预览并获得写入授权。完整模式还管理子代理默认配置，须核对子代理兼容性；两种模式均不管理主模型或 Plan 设置。

只有用户明确授权此次用户级变更后，才可执行：

```text
python scripts/codex_model_routing.py --codex-home <目录> apply --confirm-user-level-change
```

脚本会在写入前解析候选 TOML、检查唯一 `[agents]` 表与唯一成对的路由标记，并备份原始 `config.toml`、`AGENTS.md` 和 SHA-256 清单。它只管理既定字段与标记块，保留其他内容。`plan` 绝不写入；无变更时 `apply` 不创建重复备份。

完整模式还会比较修改前后的解析值：所有受管字段必须等于目标值，全部非受管值必须保留。无法安全定位的复杂 TOML 布局会在备份和写入前停止；不得跳过校验、删除用户说明或把失败改成成功。仅行为更新仍使用 `--rules-only`。

## 运行时验收

文件通过审计不等于桌面端已加载配置。写入后让用户重新打开 Codex 或启动加载新指令的任务：简单只读任务应直接完成，另用确有独立工作价值的任务验证显式派发，不为了验收而要求每个小任务派发。完整配置更新还须检查默认子代理，确认主线程与 Plan 的现有选择未改变。模型清单、宿主版本与桌面端行为可能漂移；不要用旧记录、PATH 中的另一套 CLI 或子代理自述代替此验证。

若宿主不支持目标模型、运行时显示与配置不同、或用户未授权写入，停止并报告证据。配置冲突、重复 `[agents]`、不配对或冲突标记、无法解析的候选 TOML、写入失败也必须停止。写入失败后只报告备份位置；不得自动恢复或覆盖可能由升级迁移的配置。恢复旧配置、改插件/MCP/权限或更改服务层级是单独请求。

## 输出

报告所用模式、Codex Home、审计/计划状态、受管差异或冲突、备份位置（若有）、运行的命令和结果，以及仍需用户在运行时确认的项目。不要声称模型已实际派发，除非已完成新的运行时验证。

## 资源导航

- 解释策略、评估兼容性或准备写入前：读取 [参考设计](references/routing-design.md)。
- 需要确定性审计、计划或写入时：运行 [路由脚本](scripts/codex_model_routing.py)。
- 优化行为后：运行 `python -m unittest discover -s tests -v`；发布评估用例在源仓库 `evals/`，结果保存在 Skill 外部。区分决策模拟、脚本测试和真实宿主派发，不向盲测评估者提供预期答案。
