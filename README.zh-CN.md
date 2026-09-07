# codex-model-routing

[English](./README.md) · [开始使用](#开始使用) · [变更边界](#会改什么不会改什么)

<p align="center">
  <picture>
    <source media="(max-width: 600px)" srcset="./docs/readme/assets/hero.zh-CN.mobile.svg">
    <img src="./docs/readme/assets/hero.zh-CN.svg" width="100%" alt="Codex 路由策略：沿用当前主模型。简单任务由主线程直做；只有值得拆分的独立工作才交给 Luna 或 Terra，最终由主线程验收。">
  </picture>
</p>

沿用当前主模型，简单任务直接完成；只有值得拆分时，才交给 Luna 或 Terra。

这是一个 Codex Skill，用于审计并按授权写入路由规则与子代理默认值；仅安装 Skill 不会修改配置。它**不会自动切换主模型，不要求 Sol Max**，也不会因为任务涉及文档、测试或多个文件就强制派发。

## 实际会怎样分工

以下是策略示例，不是真实运行记录：

| 你的任务 | 预期路线 |
| --- | --- |
| 改一个错字，再检查结果 | 主线程直做，保持完整闭环 |
| 审查一处紧密关联的小改动 | 主线程直做，不为配额另设复核 |
| 主线程实现功能时，独立调研另一主题 | 交接值得时，使用 Luna Medium |
| 实现边界清楚、可独立验收的模块 | 拆分值得时，使用 Terra High |
| 决定高风险迁移或安全方案 | 核心判断留在主线程 |

**先判断是否值得派发，再选模型。** 工作项必须边界清楚、可独立验收，且并行或独立复核的价值超过启动、交接与集成成本。不确定时先直做；尊重用户明确要求使用或不使用子代理。

## 开始使用

需要 Codex 与 **Python 3.11+**；路由脚本只使用标准库。

请 Agent 安装[这个 Skill](https://github.com/MuziGeek/codex-model-routing)，或使用可选的命令安装器（需要 Node.js）：

```text
npx skills add MuziGeek/codex-model-routing --skill codex-model-routing
```

添加 `--list` 可只查看、不安装。也可将仓库中的整个 `codex-model-routing/` 目录复制到 Codex 可发现的 Skill 位置。

安装后，先这样说：

> 使用 codex-model-routing 审计我当前的路由配置，展示建议差异，暂时不要写入。

或在**已安装的 Skill 目录**运行：

```text
python scripts/codex_model_routing.py audit
```

这里的 `python` 指已确认的 Python 3.11+ 解释器，可按环境替换为 `py -3`、`python3` 或完整路径。默认目标为 `CODEX_HOME`；未设置时使用当前用户的 `.codex`。指定其他目录时，将 `--codex-home "目标目录"` 放在子命令**之前**。

## 先预览，再修改

`audit` 检查现状，`plan` 展示候选差异，两者都不写文件。`apply` 需要用户明确授权本次用户级变更；确认参数不能代替用户许可。

**只更新路由行为、保留全部配置字节**时：

```text
python scripts/codex_model_routing.py --rules-only plan
```

审阅差异并授权后，再执行：

```text
python scripts/codex_model_routing.py --rules-only apply --confirm-user-level-change
```

`--rules-only` 仅管理 `AGENTS.md` 中的路由标记块，不读取、验证或写入 `config.toml`。只有还需要设置子代理默认值时，才使用完整模式。

<details>
<summary>完整模式：路由规则 + 子代理默认值</summary>

写入前，核对当前官方[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)、[模型说明](https://learn.chatgpt.com/docs/models)，以及目标宿主的实际模型可用性或严格加载结果。不兼容时停止，不静默替换模型。

```text
python scripts/codex_model_routing.py plan
```

审阅差异并授权后，再执行：

```text
python scripts/codex_model_routing.py apply --confirm-user-level-change
```

脚本管理唯一根表中的以下四个字段：

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
default_subagent_model = "gpt-5.6-terra"
default_subagent_reasoning_effort = "high"
```

默认值本身不能证明实际派发。请结合官方[子代理文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)，在加载规则后验证真实行为。

</details>

## 会改什么，不会改什么

- **主模型由你决定。** 两种模式都不新增或覆盖 `model`、`model_reasoning_effort` 和 `plan_mode_reasoning_effort`，原有缺省状态也保留。Plan 仍手动进入，沿用你的设置。
- **只改明确范围。** 完整模式管理上述四个字段与 `AGENTS.md` 中一段成对标记块；插件、MCP、权限、服务层级、自定义代理角色和其他配置保持不变。
- **写入可恢复。** 变更文件先备份到目标目录的 `backups/`，附 SHA-256 清单。写入对单文件是原子的，并非跨两文件事务；无差异时不重复备份。
- **不安全就停止。** 标记冲突、TOML 无法解析或安全编辑、非受管值变化都会阻止写入。部分合法但复杂的 TOML 布局也会被拒绝。写入失败时，应核对报告中的备份与当前状态后再恢复。

## 值得派发后，怎样选模型

Luna Medium 处理独立的检索、文档、机械修改或明确测试；Terra High 处理常规实现、集成、调试或审查。非高风险调试在留下 Terra High 失败证据后，最多升级**一次**至 XHigh；权限不足、缺依赖或测试环境故障不靠升级模型解决。

规则限制最多三个并行子代理，禁止嵌套派发，同一文件或共享状态只允许一个写入者。实际派发前说明范围和模型，主线程检查差异与相关测试后再验收。简单直做不增加路由宣告。

## 验证真实行为

授权更新后，重新打开 Codex，或启动会加载新规则的任务。分别检查两条路线：小任务应直做；真正独立的工作才考虑派发。确认主模型保持原样，模型身份看父级实际派发参数，不看子代理自述。

**静态检查不能证明宿主已加载配置，也不能证明真实模型身份。** 本 Skill 不提供自动路由遥测。Windows 文件行为已测试；macOS、Linux 运行时行为尚未验证。

维护者可在仓库根目录运行：

```text
python codex-model-routing/tests/test_codex_model_routing.py
```

[路由场景](./codex-model-routing/evals/routing-cases.json) · [独立安装使用说明](./codex-model-routing/README.md) · [Skill 执行约定](./codex-model-routing/SKILL.md)

## 许可证

[MIT](./LICENSE) · Copyright (c) 2026 Muzi。
