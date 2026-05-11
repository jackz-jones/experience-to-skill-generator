# Experience-to-Skill Generator

将 AI 会话历史自动转化为可复用的技能文档，提取有价值的技术知识和最佳实践。

> 📖 完整文档请参阅 [README.md](../../README.md)

## 1. 可用命令

本工具提供以下 CLI 子命令：

| 命令 | 说明 | 关键参数 |
| --- | --- | --- |
| `extract` | 预处理会话：读取、脱敏、归一化、分段，输出结构化文本供 LLM 分析（**不做语义分析**） | `--max-chunks` 最大分段数 |
| `analyze` | 使用内置规则引擎分析会话（不依赖 LLM，作为降级方案） | `--json-lines` 紧凑 JSON 输出 |
| `generate` | 生成 SKILL.md（可接收外部 LLM 分析结果，或使用内置规则引擎） | `--name` 技能名称，`--analysis` 外部分析 JSON |
| `config` | 输出合并后的配置和适配策略 | 无 |
| `validate-config` | 校验配置文件、环境变量和 CLI 覆盖项 | 无 |
| `diagnose` | 诊断运行环境和会话来源 | 无 |
| `setup-agent` | 为指定 agent 生成项目级工作流指引文件（如 `CLAUDE.md`、`.cursorrules`） | `agent_type` 目标 agent 类型 |

全局参数：

| 参数 | 说明 |
| --- | --- |
| `--input` | 会话文件或目录路径（对 `extract` / `analyze` / `generate` / `diagnose` 必填，对 `config` / `validate-config` 可省略） |
| `--output-dir` | SKILL 输出目录 |
| `--conflict` | 冲突策略：`rename` / `skip` / `overwrite` / `merge` / `fail` |
| `--preserve-raw` | 保留原文内容（⚠️ 可能泄露敏感信息） |
| `--config` | JSON 配置文件路径 |

## 2. Agent 集成推荐工作流

当用户要求将会话整理为 skill 时，推荐按以下流程调用：

```
1. 调用 extract 命令，获取预处理后的会话文本
2. 根据返回的 prompt_hint，用你自己的 LLM 能力分析会话内容
3. 将分析结果（JSON）传给 generate --analysis 命令生成 SKILL.md
4. 检查生成的 SKILL.md 内容是否准确覆盖要点
5. 如不满意，调整分析结果后重新调用 generate
```

对于非 OpenClaw 的 agent（Claude Code、Cursor、Windsurf），可通过 `setup-agent` 命令自动生成项目级工作流指引文件，让 agent 自动学会上述流程：

```bash
experience-to-skill-generator setup-agent claude-code   # 生成 CLAUDE.md
experience-to-skill-generator setup-agent cursor         # 生成 .cursorrules
experience-to-skill-generator setup-agent windsurf       # 生成 .windsurfrules
```

> 💡 **设计理念**：工具只负责"数据管道"（读取 → 预处理 → 模板渲染 → 写入），语义分析交给 agent 自身的 LLM，自检循环由 agent 天然完成。无需额外配置 LLM。

## 3. 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 成功 |
| `2` | 配置或运行时错误（如会话文件不存在、配置项非法等） |
| `130` | 用户中断（Ctrl+C） |

## 4. 快速开始

```bash
# 诊断环境（推荐先运行）
experience-to-skill-generator --input ./sessions diagnose

# 预处理会话（输出结构化文本供 LLM 分析）
experience-to-skill-generator --input ./sessions/session.json extract

# 使用内置规则引擎分析（降级方案）
experience-to-skill-generator --input ./sessions/session.json analyze

# 使用外部 LLM 分析结果生成技能文档
experience-to-skill-generator --input ./sessions/session.json --output-dir ./generated_skills generate --name my-skill --analysis '{"tasks":[...],"key_steps":[...],"constraints":[...],"keywords":[...],"confidence":0.85}'

# 使用内置规则引擎生成（不传 --analysis）
experience-to-skill-generator --input ./sessions/session.json --output-dir ./generated_skills generate --name my-skill

# 查看当前配置
experience-to-skill-generator config

# 校验配置
experience-to-skill-generator validate-config
```

---

*由 [Experience-to-Skill Generator](https://github.com/jackz-jones/experience-to-skill-generator) 生成*