# codex-model-routing

[English](./README.md)

<p align="center">
  <picture>
    <source media="(max-width: 600px)" srcset="./docs/readme/assets/hero.zh-CN.mobile.svg">
    <img src="./docs/readme/assets/hero.zh-CN.svg" width="100%" alt="codex-model-routing 路由图：Sol Max 负责规划、路由和验收；Luna Medium 处理清晰且可重复的工作；Terra High 处理日常实现；高风险或模糊任务回到 Sol；所有路径汇入验收。">
  </picture>
</p>

这是一个可审计的 Codex Skill，用于建立有意图的模型路由策略：Sol Max 主线程负责规划、路由和验收；Luna Medium 处理清晰、可重复的工作；Terra High 处理日常实现。它是配置与行为规则的辅助工具，不是 Codex 原生自动切换根模型的机制。

## 先看事实，再谈承诺

随 Skill 提供的 payload 明确分为 `audit`、`plan` 和 `apply` 三种模式。

- `audit` 只检查受管模型字段和路由标记块，不写入。
- `plan` 只展示候选差异，不写入。
- `apply` 需要明确的用户级确认参数；发生变更时会原子写入，并在 `backups/` 保存原始文件和 SHA-256 清单。

遇到不可解析的 TOML、重复或数组形式的根 `[agents]` 表、冲突的路由标记，以及其他不安全状态时，它会停止。未知配置会被保留，而不是整份覆盖。

## 路由机制的真实边界

Codex 配置可以设定子代理的默认模型和推理强度；真正的子代理派发是行为决策：Codex 在被直接请求时，或适用的项目/Skill 指令要求时派发。显式 `spawn` 指定的模型和推理强度会覆盖默认值。

本 Skill 会写入配套的 `AGENTS.md` 路由规则，使模型选择可观察、可复核。它不声称具备自动路由遥测、发布流程，或未经独立观察的运行时派发事实。

模型分工依据 OpenAI 当前关于 [Sol、Terra、Luna、Max 与 Ultra](https://learn.chatgpt.com/docs/models) 的说明；派发条件和显式覆盖优先级来自官方[子代理文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)。可用配置键则必须始终以当前[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)为准。

| 工作形态 | 预期处理 |
| --- | --- |
| 架构、安全、迁移、数据损失、生产风险或需求模糊 | 决策保留在 Sol Max |
| 清晰、可重复的检索、整理、文档或机械任务 | 显式派发 Luna Medium |
| 日常多文件实现、集成、调试或审查 | 显式派发 Terra High |
| 已有失败证据的非高风险耦合调试 | Terra 最多一次升至 XHigh，再重新判断 |

## 安装与第一个安全动作

使用 Codex Skill Installer 从以下 GitHub 源安装：

<https://github.com/MuziGeek/codex-model-routing/tree/main/codex-model-routing>

以 Installer 当下的流程为准，并确认它解析的是完整的 `codex-model-routing` 目录，其中包含 `SKILL.md`、`scripts` 与 `references`。若 Installer 不可用，可把整个目录手动复制到 Codex 可发现的 Skill 位置；不要编造 `npx` 安装命令。

随后从已安装的 Skill 目录开始只读审计：

```text
python scripts/codex_model_routing.py --codex-home <Codex Home> audit
```

若设置了 `CODEX_HOME`，脚本会使用它；否则使用当前用户的 `.codex` 目录。可通过 `--codex-home` 指向隔离测试目录。

## 先预览，再写入

只有在审阅当前计划、并获得本次用户级变更的明确授权后，才可以写入：

```text
python scripts/codex_model_routing.py --codex-home <Codex Home> plan
python scripts/codex_model_routing.py --codex-home <Codex Home> apply --confirm-user-level-change
```

每次写入前，都要同时复核当前官方 Codex 配置参考，以及目标宿主实际可用的模型或严格加载结果。模型支持和可用推理强度会在应用版本、官方文档和不同宿主之间漂移；静态 `plan` 通过，不代表任何版本都可以直接 `apply`。

> **兼容性门槛：** 当前公开配置参考只把 `plan_mode_reasoning_effort` 列到 `xhigh`，而部分桌面宿主的模型目录会在模型层提供 `max`。本 payload 的目标策略包含 `plan_mode_reasoning_effort = "max"`。只有目标宿主明确接受该值时才能写入；否则应停止并报告漂移，不能静默降级。

## 验证后再信任

在获得授权并完成写入后，重新打开 Codex，进行一次新的只读运行时检查：主线程模型、Plan 推理强度、默认子代理设置，以及实际被显式请求的派发。静态配置检查不能证明桌面宿主已经加载文件，也不能证明任务实际运行在目标模型上。

在本仓库根目录运行 payload 测试：

```text
python codex-model-routing/tests/test_codex_model_routing.py
```

## 边界与限制

- payload 只管理三个顶层模型字段、唯一根 `[agents]` 表的四个字段，以及 `AGENTS.md` 中一段成对的路由标记块。
- 它不会修改插件、MCP、权限、服务层级、官方 `[agents.<role>]` 子表，或其他未知配置。
- Windows 行为已检查；Linux 和 macOS 只做了静态兼容性设计覆盖，尚未进行运行时验证。
- 写入前必须重新核对公开模型/配置文档和目标宿主；推理强度的可用性尤其属于漂移点。
- 本 README 不作 release 声明，也不提供自动路由遥测。

用户级行为和安全条件请阅读已安装的 [Skill README](./codex-model-routing/README.md) 与 [SKILL.md](./codex-model-routing/SKILL.md)。
