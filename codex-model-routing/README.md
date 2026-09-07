# codex-model-routing

这是一个 Codex 专用 Skill，用来把“当前主线程规划与验收、按任务显式选择 Luna/Terra 子代理”的约定变成可检查、可预览、可备份的本地配置。它避免了只修改默认子代理却没有行为规则、误覆盖未知配置、或把静态配置当作运行时事实的问题。

路由先判断拆分收益：简单完整任务默认直做，不因“文档、测试、多文件”标签强制派发；读、改、测同一小目标是一个闭环。仅在独立工作或复核收益超过交接成本后才选择 Luna/Terra，不为配额制造复核；不确定时先直做。用户明确要求使用或不使用子代理时遵从其限制，高风险核心判断始终由主线程负责。

## 安装

把仓库地址交给 Agent：**请帮我安装这个 Skill：https://github.com/MuziGeek/codex-model-routing**。

也可使用命令安装：

```text
npx skills add MuziGeek/codex-model-routing --skill codex-model-routing
```

命令安装需要 Node.js；Skill 本身只需要 Python。可先添加 `--list` 查看可发现的 Skill，不安装。若安装器不可用，手动将仓库中的完整 `codex-model-routing` 目录放入 Codex 可发现的 Skill 位置。首次使用先 `audit`，而非直接 `apply`。

## 配置

运行脚本需要 Python 3.11+，无第三方依赖。默认目标为 `CODEX_HOME`；未设置时是当前用户主目录下的 `.codex`。可用 `--codex-home` 指向测试目录或实际 Codex Home。

先确认解释器版本。下文 `python` 表示已验证的解释器；Windows 可用 `py -3`，macOS/Linux 可用 `python3`，缺少命令时使用可用解释器的完整路径。

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

只优化派发行为、不更改已选模型时，使用以下模式；同样需要授权和差异检查：

```text
python scripts/codex_model_routing.py --codex-home <目录> --rules-only plan
python scripts/codex_model_routing.py --codex-home <目录> --rules-only apply --confirm-user-level-change
```

`--rules-only` 只读取、备份和更新 `AGENTS.md`，不读取或验证 `config.toml`，原配置不存在时也不会创建它。完整模式仅额外更新子代理默认值；两种模式均保留当前主模型、主线程推理强度和 Plan 设置，不新增缺省字段。

可以自然地说“审计我的 Codex 模型路由”“预览修复 config.toml 和 AGENTS.md 的差异”“解释当前主线程与 Luna/Terra 应如何分工”，或在明确授权后说“按此策略修复我的 Codex 全局模型路由”。Skill 会区分仅解释、只读审计和可写入修复。

## 兼容性与边界

这是 Codex 专用工具，不管理普通项目的模型选择，也不替代一次具体任务的派发判断。Python 代码只使用标准库；Windows 上已验证，其余平台仅做了静态兼容性设计检查。实际可用模型、桌面端加载行为和配置格式随 Codex 版本变化，写入后必须在重新打开 Codex 后做新的只读运行时验证。

主线程模型、主线程推理强度与 Plan 设置由用户或宿主决定，本 Skill 不管理这些字段。子代理模型可用性请核对目标宿主与[模型说明](https://learn.chatgpt.com/docs/models)，配置字段见[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)，实际派发边界见[子代理文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)。

脚本只管理唯一 `[agents]` 表的四个字段，以及 `AGENTS.md` 中唯一的路由标记块。它不会修改插件、MCP、权限、服务层级、官方自定义 `[agents.<role>]` 子表或其他未知配置。重复或数组形式的根 `[agents]`、冲突/不配对标记与不可解析 TOML 都会停止而不是猜测修复。

完整模式写入前还会检查候选配置的实际含义：目标字段必须生效，非受管配置值必须保持不变。复杂 TOML 布局若无法安全编辑会停止，不承诺支持所有合法写法。无子代理能力时仍可本地审计、预览和更新文件，但不能证明运行时派发；文件操作无需浏览器或 GUI。

## 数据与输出

所有操作都在本机文件系统中进行，不需要网络、账户访问或付费服务。写入前会在目标 Codex Home 的 `backups/` 中保存原始 `config.toml`、`AGENTS.md` 和 SHA-256 清单；无差异时不会创建备份。输出是简洁的审计报告、统一 diff 或 JSON，包含冲突、变更、备份位置与运行时待验证项。

## 测试

在 Skill 根目录运行：

```text
python -m unittest discover -s tests -v
python <oil-skill-creator>/scripts/validate_skill.py .
```

测试覆盖未知配置保留、幂等、备份、冲突拒绝、只读预览、仅规则更新保留配置字节，以及多行字符串误识别时拒绝写入。发布评估用例在[源仓库 evals](https://github.com/MuziGeek/codex-model-routing/tree/main/codex-model-routing/evals)，评估结果留在外部 workspace，不随 Skill 安装。静态校验与决策模拟不等同于桌面端运行时验收。

## 许可证

本 Skill 采用 [MIT License](LICENSE) 开源。Copyright (c) 2026 Muzi。
