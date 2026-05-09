# Experience-to-Skill Generator

将 AI 会话历史自动转化为可复用的技能文档，提取有价值的技术知识和最佳实践。

> 📖 完整文档请参阅 [README.md](../../README.md)

## 1. 可用命令

本工具提供以下 CLI 子命令：

| 命令 | 说明 | 关键参数 |
| --- | --- | --- |
| `analyze` | 读取会话文件并分析，输出结构化 JSON | `--json-lines` 紧凑 JSON 输出 |
| `generate` | 分析会话并生成 SKILL.md | `--name` 指定技能名称 |
| `config` | 输出合并后的配置和适配策略 | 无 |
| `validate-config` | 校验配置文件、环境变量和 CLI 覆盖项 | 无 |
| `diagnose` | 诊断运行环境和会话来源 | 无 |

全局参数：

| 参数 | 说明 |
| --- | --- |
| `--input` | 会话文件或目录路径（对 `analyze` / `generate` / `diagnose` 必填，对 `config` / `validate-config` 可省略） |
| `--output-dir` | SKILL 输出目录 |
| `--conflict` | 冲突策略：`rename` / `skip` / `overwrite` / `merge` / `fail` |
| `--preserve-raw` | 保留原文内容（⚠️ 可能泄露敏感信息） |
| `--config` | JSON 配置文件路径 |

## 2. 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 成功 |
| `2` | 配置或运行时错误（如会话文件不存在、配置项非法等） |
| `130` | 用户中断（Ctrl+C） |

## 3. 快速开始

```bash
# 诊断环境（推荐先运行）
experience-to-skill-generator --input ./sessions diagnose

# 分析会话
experience-to-skill-generator --input ./sessions/session.json analyze

# 分析并输出紧凑 JSON（便于脚本解析）
experience-to-skill-generator --input ./sessions/session.json analyze --json-lines

# 生成技能文档
experience-to-skill-generator --input ./sessions/session.json --output-dir ./generated_skills generate --name my-skill

# 查看当前配置
experience-to-skill-generator config

# 校验配置
experience-to-skill-generator validate-config
```

---

*由 [Experience-to-Skill Generator](https://github.com/jackz-jones/experience-to-skill-generator) 生成*