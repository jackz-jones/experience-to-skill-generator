# Experience-to-Skill Generator

> [English](README.md)

把你的 AI 会话记录变成可复用的技能文档 —— 只需一行命令。

## 1. 这是什么？

Experience-to-Skill Generator 是一个命令行工具，它能**自动分析你与 AI 的对话历史**，从中提取出有价值的工作流程、技术方案和最佳实践，然后生成一份结构化的 `SKILL.md` 技能文档。

**核心设计理念**：工具只做“数据管道”（读取 → 预处理 → 模板渲染 → 写入），语义分析交给 agent 自身的 LLM 完成。无需额外配置 LLM API Key。

生成的 `SKILL.md` 可供 AI agent 作为技能使用。OpenClaw 可自动加载；其他 agent（Claude Code、Cursor 等）需手动集成（粘贴到对话开头、写入 `CLAUDE.md` / `.cursorrules` 等）。

## 2. 我能用它做什么？

| 场景 | 说明 | 适合谁 |
| --- | --- | --- |
| 🏢 **团队知识沉淀** | 把代码评审、技术讨论等团队对话转为标准技能文档，避免经验流失 | 技术团队管理者 |
| 👨‍💻 **开发者个人工具箱** | 把你自己与 AI 的对话提炼成可复用的工作流，下次遇到同类问题直接参考 | 开发者 |
| 🤖 **OpenClaw 技能集成** | 作为 OpenClaw 技能包使用，由 agent 自动调用 | OpenClaw 用户 |
| 🏭 **自动化/CI 集成** | 用 JSON 输出和稳定退出码接入自动化流水线 | DevOps / SRE |

## 3. 快速上手

### 前置条件

Python 3.8+（无需其他依赖，`numpy` / `scikit-learn` 为可选加速依赖）

### 方式 A：直接运行源码（无需安装）

```bash
# 克隆项目
git clone https://github.com/jackz-jones/experience-to-skill-generator.git
cd experience-to-skill-generator

# 准备会话文件（放到 sessions/ 目录，支持 .json / .jsonl / .md / .txt）
mkdir sessions
cp /path/to/your/ai-conversation.json sessions/

# ① 诊断环境（推荐先运行）
python3 python-scripts/universal_skill_generator.py --input ./sessions diagnose

# ② 预处理会话（输出结构化文本供 LLM 分析）
python3 python-scripts/universal_skill_generator.py --input ./sessions/session.json extract

# ③ 使用内置规则引擎分析（降级方案，不依赖 LLM）
python3 python-scripts/universal_skill_generator.py --input ./sessions/session.json analyze

# ④ 生成技能文档（使用外部 LLM 分析结果）
python3 python-scripts/universal_skill_generator.py \
  --input ./sessions/session.json \
  --output-dir ./generated_skills \
  generate --name my-first-skill \
  --analysis '{"tasks":[...],"key_steps":[...],"constraints":[...],"keywords":[...],"confidence":0.85}'

# ⑤ 生成技能文档（使用内置规则引擎，不传 --analysis）
python3 python-scripts/universal_skill_generator.py \
  --input ./sessions/session.json \
  --output-dir ./generated_skills \
  generate --name my-first-skill
```

### 方式 B：安装为本地命令（推荐日常使用）

```bash
# 一键安装（交互模式下会提示选择 CLI 语言）
./skills/experience-to-skill-generator/install.sh

# 或指定语言 + 跳过交互确认
ESG_LANG=zh ESG_NON_INTERACTIVE=1 ./skills/experience-to-skill-generator/install.sh

# 安装后直接用短命令（帮助文本自动按安装时选择的语言显示）
experience-to-skill-generator --input ./sessions/session.json analyze
experience-to-skill-generator --input ./sessions/session.json --output-dir ./generated_skills generate --name my-skill
```

> 💡 安装脚本会自动检测环境：检测到 OpenClaw 则安装为原生技能；否则安装为通用模式。无需手动指定。
>
> 💡 安装时会选择 CLI 帮助文本语言（中文/英文），选择结果写入命令入口，后续使用无需再设置环境变量。如需临时切换：`ESG_LANG=en experience-to-skill-generator --help`

### 会话文件格式

支持 `.json`、`.jsonl`、`.md`、`.txt` 四种格式。推荐 JSON 格式：

```json
{
  "messages": [
    {"role": "user", "content": "请实现一个通用安装脚本，必须避免覆盖已有技能"},
    {"role": "assistant", "content": "1. 检查依赖\n2. 识别 agent 环境\n3. 写入技能并处理冲突"}
  ]
}
```

<details>
<summary>👉 各 Agent 对话文件查找指南</summary>

#### 🟣 OpenClaw

```bash
~/.openclaw/agents/           # 对话文件目录
~/.openclaw/workspace/memory/ # 工作区内存目录
```

OpenClaw 自动保存每次 agent 对话到 `~/.openclaw/agents/`。

#### 🟢 Claude Code (CLI)

```bash
~/.claude/projects/<project-path>/*.jsonl  # 按项目归档的对话（JSONL 格式）
~/.claude/history.jsonl                     # 全局历史记录
```

```bash
# 复制某个项目的会话到 sessions 目录
cp ~/.claude/projects/-Users-zx-Desktop-ai-myproject/<session-id>.jsonl ./sessions/
```

#### 🟡 Hermes

```bash
~/.hermes/sessions/          # 会话文件目录（*.jsonl, *.json）
~/.hermes/.hermes_history    # 对话历史文件
```

#### 🔵 Cursor

```bash
~/Library/Application Support/Cursor/Session Storage/  # LevelDB 数据库，非 JSON 文件
```

Cursor 使用浏览器存储技术，建议从编辑器中手动复制对话内容。

#### ⚪ ChatGPT (桌面应用)

无标准导出功能，建议从网页版复制对话内容，手动保存为 `.json` 或 `.md` 文件。

</details>

## 4. 生成的 SKILL.md 包含什么？

| 板块 | 说明 |
| --- | --- |
| `metadata` | 元信息（技能名、版本、来源等） |
| `适用场景` | 什么时候用这个技能 |
| `触发条件` | 什么情况会触发 |
| `执行步骤` | 具体操作步骤 |
| `注意事项` | 使用时要注意什么 |
| `示例用法` | 实际使用示例 |
| `质量与来源` | 置信度和来源信息 |

## 5. OpenClaw 模式 vs 通用模式

| | OpenClaw 原生模式 | 通用模式 |
| --- | --- | --- |
| **触发条件** | 检测到 `~/.openclaw` 目录或 `openclaw` 命令 | 未检测到 OpenClaw |
| **技能目录** | `~/.openclaw/skills/experience-to-skill-generator` | `~/.experience-to-skill-generator/skills/experience-to-skill-generator` |
| **会话来源** | 自动从 `~/.openclaw/agents/` 读取 | 需手动放到 `./sessions/` 或用 `--input` 指定 |
| **agent 自动加载** | ✅ 安装时通过 `openclaw skills install` 注册（需本地安装并启动 OpenClaw 运行时） | ❌ 需手动集成 |

### 非 OpenClaw Agent 如何使用生成的技能？

1. **一键生成工作流指引（推荐）**：运行 `setup-agent` 命令，自动生成 agent 对应的配置文件，让 agent 自动学会完整的 extract → LLM 分析 → generate 流程

```bash
experience-to-skill-generator setup-agent claude-code   # 生成 CLAUDE.md
experience-to-skill-generator setup-agent cursor         # 生成 .cursorrules
experience-to-skill-generator setup-agent windsurf       # 生成 .windsurfrules
```

2. **对话开头粘贴**：新建对话时，把 `SKILL.md` 内容粘贴到提问前面
3. **项目级配置文件**：写入 `CLAUDE.md`（Claude Code）或 `.cursorrules`（Cursor），agent 会在每次对话时自动加载
4. **系统提示词**：将 `SKILL.md` 内容添加到 agent 的自定义系统提示词

> 💡 **一句话总结**：OpenClaw 是"自动注入"，其他 agent 通过 `setup-agent` 命令实现"半自动注入"（一次设置，永久生效）——效果类似，只是注入方式不同。

## 6. CLI 命令参考

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `extract` | 预处理会话，输出结构化文本供 LLM 分析 | `experience-to-skill-generator --input ./sessions/session.json extract` |
| `analyze` | 使用内置规则引擎分析（降级方案） | `experience-to-skill-generator --input ./sessions/session.json analyze --json-lines` |
| `generate` | 生成 SKILL.md | `experience-to-skill-generator --input ./sessions/session.json --output-dir ./generated_skills generate --name my-skill` |
| `diagnose` | 诊断运行环境 | `experience-to-skill-generator --input ./sessions diagnose` |
| `config` | 输出合并配置 | `experience-to-skill-generator config` |
| `validate-config` | 校验配置 | `experience-to-skill-generator validate-config` |
| `setup-agent` | 为指定 agent 生成项目级工作流指引文件 | `experience-to-skill-generator setup-agent claude-code` |

| 参数 | 说明 |
| --- | --- |
| `--input` | 会话文件或目录路径（必填） |
| `--output-dir` | 输出目录 |
| `--conflict` | 冲突策略：`rename` / `skip` / `overwrite` / `merge` / `fail` |
| `--preserve-raw` | 保留原文内容（⚠️ 可能泄露敏感信息） |
| `--config` | JSON 配置文件路径 |
| `--analysis` | （generate 子命令）外部 LLM 分析结果 JSON |
| `--analysis-stdin` | （generate 子命令）从 stdin 读取外部分析 JSON |

### 环境变量

| 变量 | 说明 |
| --- | --- |
| `ESG_LANG` | CLI 帮助文本语言：`zh`（中文）或 `en`（英文）。安装时自动写入命令入口，通常无需手动设置 |
| `ESG_NON_INTERACTIVE` | 设为 `1` 跳过所有交互确认 |
| `ESG_SKILL_DIR` | 自定义技能安装目录 |
| `ESG_CONFIG_DIR` | 自定义配置目录 |
| `ESG_OUTPUT_DIR` | 自定义输出目录 |
| `ESG_SESSION_DIR` | 自定义会话目录 |

### 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 成功 |
| `2` | 配置或运行时错误 |
| `130` | 用户中断（Ctrl+C） |

> 📋 完整配置参考（环境变量、JSON 配置项、adapters 等）请查阅 [doc/CONFIGURATION_CN.md](doc/CONFIGURATION_CN.md)。

## 7. 配置

配置优先级从低到高：代码内置默认值 → `--config` 文件 → `ESG_*` 环境变量 → CLI 参数。

> 💡 `ESG_LANG` 在安装时已写入命令入口脚本，等效于永久设置。如需覆盖，在执行命令前临时指定即可。

> 📋 完整配置参考请查阅 [doc/CONFIGURATION_CN.md](doc/CONFIGURATION_CN.md)。

## 8. 安全与脱敏

- **默认脱敏**：令牌、密钥、邮箱、私有路径在分析和生成结果中自动清理
- **原子写入**：先写临时文件再替换目标，避免写入中断导致文件损坏
- **冲突可控**：同名或相似技能按 `--conflict` 指定策略处理

如需保留原文内容：

```bash
experience-to-skill-generator --preserve-raw --input ./sessions analyze
```

> ⚠️ 启用 `--preserve-raw` 前请确认会话内容不会泄露敏感信息。

## 9. 高级用法：CI/CD 自动化集成

> 💡 **适用场景**：团队在**私有仓库**中统一管理脱敏后的会话文件，希望每次提交后自动生成技能文档。对于个人用户，本地直接运行命令即可，通常不需要 CI/CD。

<details>
<summary>👉 展开查看 GitHub Actions 配置示例</summary>

```yaml
# .github/workflows/skill-generator.yml
name: Auto Generate Skills
on:
  push:
    paths: ['sessions/**']    # 仅当对话文件有更新时触发

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: ESG_NON_INTERACTIVE=1 ./skills/experience-to-skill-generator/install.sh
      - run: experience-to-skill-generator --input ./sessions --output-dir ./skill_library --conflict rename generate
      - run: |
          git config user.name "skill-bot"
          git config user.email "bot@example.com"
          git add ./skill_library/
          git diff --cached --quiet || git commit -m "🤖 auto-generate skills from sessions"
          git push
```

**注意事项：**

- `--conflict rename` 保证不会覆盖已有技能文件，每次生成写入新目录
- `paths: sessions/**` 避免无关提交触发工作流
- 每次运行会读取 sessions/ 下**所有**文件重新分析，生成全新的 SKILL（非增量追加）
- 会话文件通常包含私人信息，提交到仓库前请确保已脱敏

</details>

## 10. 常见问题

### ❓ `command not found: experience-to-skill-generator`

安装脚本创建的命令不在 PATH 中：

```bash
export PATH="$HOME/.local/bin:$PATH"   # 添加到 ~/.bashrc 或 ~/.zshrc
```

### ❓ `找不到会话文件`

确认 `--input` 路径正确，文件格式为 `.json` / `.jsonl` / `.md` / `.txt`：

```bash
ls ./sessions/session.json
python3 -c "import json; json.load(open('./sessions/session.json')); print('OK')"
```

### ❓ 生成的 SKILL.md 质量不高

推荐使用 `extract` + agent LLM 分析 + `generate --analysis` 的完整流程，而非仅依赖内置规则引擎。如果使用内置规则引擎，确保会话包含多轮 user/assistant 对话，且问题描述和解决步骤明确。

### ❓ 安装后想回退

```bash
rm -rf ~/.local/bin/experience-to-skill-generator
rm -rf ~/.experience-to-skill-generator                              # 通用模式（技能文件位于 skills/experience-to-skill-generator/ 子目录）
rm -rf ~/.openclaw/skills/experience-to-skill-generator              # OpenClaw 模式
rm -rf ~/.openclaw/config/skills/experience-to-skill-generator      # OpenClaw 模式的配置目录
```

## 11. 验证

```bash
python3 -m unittest python-scripts/test_universal_skill_generator.py
python3 python-scripts/e2e_validate_universal_skill_generator.py
```

## 12. 许可证

Apache License 2.0，详见 [LICENSE](LICENSE)。