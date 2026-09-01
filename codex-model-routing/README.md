# codex-model-routing

这是一个 Codex 专用 Skill，用来把“Sol Max 主线程规划与验收、按任务显式选择 Luna/Terra 子代理”的约定变成可检查、可预览、可备份的本地配置。它避免了只修改默认子代理却没有行为规则、误覆盖未知配置、或把静态配置当作运行时事实的问题。

## 安装

优先使用 Codex Skill Installer 从 <https://github.com/MuziGeek/codex-model-routing/tree/main/codex-model-routing> 安装，并确认它保留整个 `codex-model-routing` 目录中的 `SKILL.md`、`scripts` 与 `references`。若 Installer 不可用，可手动将完整目录放入 Codex 可发现的本地 Skill 目录；不要编造 `npx` 安装命令。安装后第一个安全动作是 `audit`，而非直接 `apply`。

## 配置

运行脚本需要 Python 3.11+，无第三方依赖。默认目标为 `CODEX_HOME`；未设置时是当前用户主目录下的 `.codex`。可用 `--codex-home` 指向测试目录或实际 Codex Home。

先审计或预览：

```text
python scripts/codex_model_routing.py --codex-home <目录> audit
python scripts/codex_model_routing.py --codex-home <目录> plan
```

只有已获得当前用户明确授权时，才执行用户级写入：

```text
python scripts/codex_model_routing.py --codex-home <目录> apply --confirm-user-level-change
```

## 使用

可以自然地说“审计我的 Codex 模型路由”“预览修复 config.toml 和 AGENTS.md 的差异”“解释 Sol/Luna/Terra 应如何分工”，或在明确授权后说“按此策略修复我的 Codex 全局模型路由”。Skill 会区分仅解释、只读审计和可写入修复。

## 兼容性与边界

这是 Codex 专用工具，不管理普通项目的模型选择，也不替代一次具体任务的派发判断。Python 代码只使用标准库；Windows 上已验证，其余平台仅做了静态兼容性设计检查。实际可用模型、桌面端加载行为和配置格式随 Codex 版本变化，写入后必须在重新打开 Codex 后做新的只读运行时验证。

当前公开[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)只把 `plan_mode_reasoning_effort` 列到 `xhigh`，而部分桌面宿主的模型目录会在模型层提供 `max`。本 Skill 的目标策略包含 `plan_mode_reasoning_effort = "max"`；只有目标宿主明确接受该值时才能写入，否则必须停止并报告漂移，不能静默降级。模型定位与 Max/Ultra 边界见[模型说明](https://learn.chatgpt.com/docs/models)，实际派发条件见[子代理文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)。

脚本只管理三个顶层模型字段、唯一 `[agents]` 表的四个字段，以及 `AGENTS.md` 中唯一的路由标记块。它不会修改插件、MCP、权限、服务层级、官方自定义 `[agents.<role>]` 子表或其他未知配置。重复或数组形式的根 `[agents]`、冲突/不配对标记与不可解析 TOML 都会停止而不是猜测修复。

## 数据与输出

所有操作都在本机文件系统中进行，不需要网络、账户访问或付费服务。写入前会在目标 Codex Home 的 `backups/` 中保存原始 `config.toml`、`AGENTS.md` 和 SHA-256 清单；无差异时不会创建备份。输出是简洁的审计报告、统一 diff 或 JSON，包含冲突、变更、备份位置与运行时待验证项。

## 测试

在 Skill 根目录运行：

```text
python -m unittest discover -s tests -v
python <oil-skill-creator>/scripts/validate_skill.py .
```

测试覆盖未知配置保留、幂等、备份、重复 `[agents]` 拒绝、标记冲突拒绝和 `plan` 不写入。静态校验不等同于桌面端运行时验收。
