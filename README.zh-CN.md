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

**先直做，值得拆分才派发。** 查一个位置、小改动、局部审查或运行一次测试默认由主线程完成。同一小目标的读取、修改、验证，即使涉及几个关联文件，也不拆成多个任务。只有边界清楚、可独立验收、确有并行或独立复核价值且收益超过交接与集成成本时才派发；不确定时直做。尊重用户明确要求使用或不使用子代理，不为配额额外制造复核。简单直做也不增加路由宣告。

模型分工依据 OpenAI 当前关于 [Sol、Terra、Luna、Max 与 Ultra](https://learn.chatgpt.com/docs/models) 的说明；派发条件和显式覆盖优先级来自官方[子代理文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)。可用配置键则必须始终以当前[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)为准。

| 工作形态 | 预期处理 |
| --- | --- |
| 简单完整任务、强串行耦合工作或拆分收益不清楚 | 主线程直做，不强拆 |
| 架构、安全、迁移、数据损失、生产风险或需求模糊 | 核心决策保留在主线程 |
| 通过拆分门槛的检索、整理、文档或机械任务 | Luna Medium |
| 通过拆分门槛的日常实现、集成、调试或审查 | Terra High |
| 仍通过门槛、已有 Terra High 失败记录的非高风险调试 | Terra 最多一次升至 XHigh，再重新判断 |

## 安装与第一个安全动作

把仓库地址交给 Agent：**请帮我安装这个 Skill：https://github.com/MuziGeek/codex-model-routing**。

也可使用命令安装（安装器需要 Node.js，Skill 本身不依赖 Node.js）：

```text
npx skills add MuziGeek/codex-model-routing --skill codex-model-routing
```

可先添加 `--list` 只检查 Skill 发现结果，不安装。若安装器不可用，可把仓库中的整个 `codex-model-routing` 目录手动复制到 Codex 可发现的 Skill 位置。

随后从已安装的 Skill 目录开始只读审计：

脚本需要 Python 3.11+。下文 `python` 代表已验证的解释器；Windows 可检查 `py -3`，macOS/Linux 可检查 `python3`，或使用可用解释器的完整路径。

```text
python scripts/codex_model_routing.py --codex-home <Codex Home> audit
```

若设置了 `CODEX_HOME`，脚本会使用它；否则使用当前用户的 `.codex` 目录。可通过 `--codex-home` 指向隔离测试目录。

## 先预览，再写入

只优化行为、保留用户当前主模型时，使用 `--rules-only`。它只检查、备份和更新 `AGENTS.md` 的路由标记块，**不读取、不验证也不写入 `config.toml`**：

```text
python scripts/codex_model_routing.py --codex-home <Codex Home> --rules-only plan
python scripts/codex_model_routing.py --codex-home <Codex Home> --rules-only apply --confirm-user-level-change
```

下面的完整模式会安装 Sol Max 预设，需要通过模型兼容性检查；用户已选择其他主模型时，不能仅为更新派发行为而使用完整模式。

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

[路由场景](./codex-model-routing/evals/routing-cases.json)覆盖直做、有价值的派发、用户限制、风险与环境故障。盲测时只给评估者策略和问题，结束后再比较预期路线。决策模拟和脚本测试不证明真实宿主行为；新任务加载规则后还需分别验证简单任务直做、独立工作合理派发。评估结果保存在 Skill 与仓库之外。

## 边界与限制

- payload 只管理三个顶层模型字段、唯一根 `[agents]` 表的四个字段，以及 `AGENTS.md` 中一段成对的路由标记块。
- 它不会修改插件、MCP、权限、服务层级、官方 `[agents.<role>]` 子表，或其他未知配置。
- 完整模式写入前校验实际解析值：受管字段必须符合目标，非受管值必须保留。无法安全编辑的复杂 TOML 布局会被拒绝，即使其语法合法；这不是通用 TOML 编辑器。
- Windows 行为已检查；Linux 和 macOS 只做了静态兼容性设计覆盖，尚未进行运行时验证。
- 写入前必须重新核对公开模型/配置文档和目标宿主；推理强度的可用性尤其属于漂移点。
- 本 README 不作 release 声明，也不提供自动路由遥测。

## 许可证

本项目采用 [MIT License](./LICENSE) 开源。Copyright (c) 2026 Muzi。

用户级行为和安全条件请阅读已安装的 [Skill README](./codex-model-routing/README.md) 与 [SKILL.md](./codex-model-routing/SKILL.md)。
