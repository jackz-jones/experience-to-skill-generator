# Experience-to-Skill Generator

> [English](README.md)

Experience-to-Skill Generator 是一个面向 agent 会话的通用 SKILL 生成器。它会读取 OpenClaw 或通用目录中的会话记录，提取任务目标、关键步骤、约束条件与可复用经验，并生成结构化 `SKILL.md`，用于知识沉淀、技能复用和后续人工审核。

### 项目定位

- **跨 agent 适配**：支持 `auto`、`openclaw`、`generic` 三种运行策略，并允许通过配置扩展新的 agent。
- **会话读取与预处理**：支持 `json`、`jsonl`、`md`、`txt` 会话文件，能够处理目录输入、长会话分段和可控截断。
- **敏感信息清理**：默认脱敏令牌、密钥、邮箱、私有路径等敏感内容。
- **结构化 SKILL 生成**：生成包含适用场景、触发条件、执行步骤、注意事项、示例用法和元数据的 `SKILL.md`。
- **安全写入与冲突处理**：支持 `rename`、`skip`、`overwrite`、`merge`、`fail` 五种冲突策略。
- **可脚本化 CLI**：提供稳定退出码、JSON 输出、配置查看、环境诊断和端到端验证能力。

### 适用场景

- **OpenClaw 会话复盘**：从 OpenClaw 工作区或 agent 目录读取会话记录。
- **通用 agent 兼容模式**：从任意 `json`、`jsonl`、`md`、`txt` 会话目录生成技能。
- **自动化脚本集成**：使用 JSON 输出、稳定退出码和冲突策略接入 CI 或定时任务。
- **人工审核工作流**：当分析置信度不足时，在生成结果中标记需要人工确认。
- **企业知识管理**：自动将团队技术讨论转化为标准技能文档，建立内部技能共享库。
- **开发者个人工具箱**：个性化工作流程自动化，常用脚本和命令自动记录。

### 文档导航

- **技术设计**：[doc/TECHNICAL_DESIGN_CN.md](doc/TECHNICAL_DESIGN_CN.md)
- **配置参考**：[doc/CONFIGURATION_CN.md](doc/CONFIGURATION_CN.md)
- **OpenClaw 技能定义**：[skills/experience-to-skill-generator/SKILL.md](skills/experience-to-skill-generator/SKILL.md)

### 目录结构

```text
.
├── README.md
├── README_CN.md
├── doc/
│   ├── TECHNICAL_DESIGN.md
│   ├── TECHNICAL_DESIGN_CN.md
│   ├── CONFIGURATION.md
│   └── CONFIGURATION_CN.md
├── python-scripts/
│   ├── universal_skill_generator.py       # 核心 CLI 入口
│   ├── analyze_conversation.py            # 会话分析模块
│   ├── generate_skill.py                  # SKILL 渲染模块
│   ├── vector_skill_optimizer.py          # 向量相似度引擎（numpy 可选）
│   ├── e2e_validate_universal_skill_generator.py
│   └── test_universal_skill_generator.py
└── skills/
    └── experience-to-skill-generator/
        ├── SKILL.md
        ├── config.json
        └── install.sh
```

### 快速开始

#### 1. 直接运行源码

```bash
python3 python-scripts/universal_skill_generator.py \
  --agent generic \
  --input ./sessions/session.json \
  --output-dir ./generated_skills \
  --conflict rename \
  generate --name reusable-flow
```

生成结果默认写入：

```text
./generated_skills/reusable-flow/SKILL.md
```

#### 2. 安装为本地命令

```bash
ESG_AGENT=generic ESG_NON_INTERACTIVE=1 \
./skills/experience-to-skill-generator/install.sh
```

安装后可使用：

```bash
experience-to-skill-generator --agent generic --input ./sessions diagnose
experience-to-skill-generator --agent generic --input ./sessions/session.json analyze --json-lines
experience-to-skill-generator --agent generic --input ./sessions/session.json --output-dir ./generated_skills generate --name reusable-flow
```

#### 3. OpenClaw 环境安装

```bash
ESG_AGENT=openclaw ESG_NON_INTERACTIVE=1 \
./skills/experience-to-skill-generator/install.sh
```

如果本机没有 `openclaw` 命令，安装脚本会降级为文件复制模式，不会阻塞通用 CLI 使用。

#### 4. 自定义安装路径

```bash
ESG_AGENT=generic \
ESG_SKILL_DIR="$HOME/.agent/skills/experience-to-skill-generator" \
ESG_CONFIG_DIR="$HOME/.agent/config/experience-to-skill-generator" \
ESG_BIN_DIR="$HOME/.local/bin" \
ESG_NON_INTERACTIVE=1 \
./skills/experience-to-skill-generator/install.sh
```

### CLI 命令

通用入口为：

```bash
python3 python-scripts/universal_skill_generator.py [global options] <command> [command options]
```

安装后也可以使用：

```bash
experience-to-skill-generator [global options] <command> [command options]
```

支持的子命令：

| 命令 | 说明 |
| --- | --- |
| `diagnose` | 诊断 Python、agent 适配策略和会话来源 |
| `analyze` | 读取会话并输出结构化分析 JSON |
| `generate` | 分析会话并写入结构化 `SKILL.md` |
| `config` | 输出合并后的配置、适配器和策略 |
| `validate-config` | 校验配置文件、环境变量和 CLI 覆盖项 |

常用全局参数：

| 参数 | 说明 |
| --- | --- |
| `--config` | JSON 配置文件路径 |
| `--agent` | `auto`、`openclaw` 或 `generic` |
| `--input` | 会话文件或目录路径 |
| `--output-dir` | 生成的 SKILL 输出目录 |
| `--conflict` | `rename`、`skip`、`overwrite`、`merge` 或 `fail` |
| `--preserve-raw` | 保留原文内容；启用前请确认不会泄露敏感信息 |

#### analyze 输出字段

`analyze` 命令输出结构化 JSON，包含：

- `summary`：消息数量、来源文件、分段信息、分析时间。
- `tasks`：从用户消息中提取的主要任务。
- `key_steps`：从 assistant 消息中提取的关键步骤。
- `constraints`：必须、禁止、注意事项等约束。
- `keywords`：关键词。
- `confidence`：分析置信度。
- `requires_review`：是否建议人工审核。

#### generate 输出示例

```json
{
  "skill_name": "reusable-flow",
  "write_result": {
    "path": "generated_skills/reusable-flow/SKILL.md",
    "action": "created",
    "reason": "new_skill"
  },
  "confidence": 0.8,
  "requires_review": false
}
```

### 输入格式

支持以下会话文件：

| 格式 | 说明 |
| --- | --- |
| `.json` | 对象或数组；优先读取 `messages`、`conversation` 或单条 `message` |
| `.jsonl` | 每行一个 JSON；无法解析的行会作为文本消息处理 |
| `.md` | 整个文件作为文本消息 |
| `.txt` | 整个文件作为文本消息 |

推荐 JSON 示例：

```json
{
  "messages": [
    {"role": "user", "content": "请实现一个通用安装脚本，必须避免覆盖已有技能"},
    {"role": "assistant", "content": "1. 检查依赖\n2. 识别 agent 环境\n3. 写入技能并处理冲突"}
  ]
}
```

### 输出结构

每个技能默认写入：

```text
<output-dir>/<skill-name>/SKILL.md
```

标准模板包含：

- `metadata` 元信息
- `适用场景`
- `触发条件`
- `执行步骤`
- `注意事项`
- `示例用法`
- `质量与来源`

### 配置方式

配置优先级从低到高为：

1. `python-scripts/universal_skill_generator.py` 中的默认配置
2. `--config` 指定的 JSON 配置文件
3. `ESG_*` 环境变量
4. CLI 参数覆盖项

常用环境变量：

| 变量 | 说明 |
| --- | --- |
| `ESG_AGENT` | `auto`、`openclaw` 或 `generic` |
| `ESG_SESSION_DIR` | 默认会话来源目录 |
| `ESG_OUTPUT_DIR` | 默认 SKILL 输出目录 |
| `ESG_CONFLICT_STRATEGY` | 默认冲突策略 |
| `ESG_MIN_SCORE` | 分析评分阈值 |
| `ESG_PRESERVE_RAW` | 是否保留会话原文 |
| `ESG_SKILL_DIR` | 安装脚本使用的目标技能目录 |
| `ESG_CONFIG_DIR` | 安装脚本使用的目标配置目录 |
| `ESG_BIN_DIR` | 安装脚本创建命令入口的位置 |
| `ESG_NON_INTERACTIVE` | 设为 `1` 时跳过安装确认 |
| `ESG_INSTALL_MODE` | 设为 `copy-only` 时跳过 agent 注册命令 |

完整配置项请查看 [doc/CONFIGURATION_CN.md](doc/CONFIGURATION_CN.md)。

### 安全与冲突处理

默认行为：

- **脱敏开启**：令牌、密钥、邮箱、私有路径会在分析结果、生成文档和诊断输出中被清理。
- **原子写入**：先写入临时文件，再替换目标 `SKILL.md`。
- **冲突可控**：同名或相似技能会按 `--conflict` 指定策略处理。

冲突策略：

| 策略 | 行为 | 适用场景 |
| --- | --- | --- |
| `rename` | 自动生成 `name-2`、`name-3` 等新目录 | 默认推荐，保留历史结果 |
| `skip` | 保留已有技能，不写入新内容 | 批量任务中避免重复生成 |
| `overwrite` | 先创建 `.bak` 备份，再覆盖 | 明确要刷新同名技能 |
| `merge` | 将新内容追加到已有 `SKILL.md` | 多次会话沉淀到同一技能 |
| `fail` | 发现冲突即失败并返回非零退出码 | CI 或严格自动化流程 |

脱敏覆盖范围：

- API key、token、secret、password
- Bearer token、OpenAI key、AWS key、GitHub token、Slack token
- 私钥、SSH 公钥片段
- 邮箱地址
- `/Users/<name>`、`/home/<name>`、`/root/...` 等私有路径

如确实需要保留原文，可使用：

```bash
experience-to-skill-generator --preserve-raw --input ./sessions analyze
```

启用前请确认会话内容不会泄露敏感信息。

### 自动化示例

```bash
set -e

OUTPUT="./generated_skills"
SESSION="./sessions/session.json"

experience-to-skill-generator \
  --agent generic \
  --input "$SESSION" \
  --output-dir "$OUTPUT" \
  --conflict fail \
  generate --name ci-generated-skill
```

### 产出物

| 分类 | 文件 |
| --- | --- |
| 核心 CLI | `universal_skill_generator.py`、`analyze_conversation.py`、`generate_skill.py`、`vector_skill_optimizer.py` |
| 测试 | `test_universal_skill_generator.py`、`e2e_validate_universal_skill_generator.py` |
| OpenClaw 技能包 | `skills/experience-to-skill-generator/SKILL.md`、`skills/experience-to-skill-generator/config.json`、`skills/experience-to-skill-generator/install.sh` |
| 文档 | `README.md`、`README_CN.md`、`doc/TECHNICAL_DESIGN.md`、`doc/TECHNICAL_DESIGN_CN.md`、`doc/CONFIGURATION.md`、`doc/CONFIGURATION_CN.md` |

### 验证清单

- ✅ **功能完整性** — CLI 子命令全部实现并通过测试
- ✅ **多 agent 适配** — 支持 openclaw 和 generic 两种适配模式
- ✅ **集成成熟度** — 完整 OpenClaw 技能适配 + 通用 CLI
- ✅ **代码质量** — Python 脚本通过单元测试和端到端验证
- ✅ **文档完整性** — 中英文技术设计和配置参考

### 验证

运行单元测试：

```bash
python3 -m unittest python-scripts/test_universal_skill_generator.py
```

运行端到端验证：

```bash
python3 python-scripts/e2e_validate_universal_skill_generator.py
```

端到端验证会覆盖 `generic` 与 `openclaw` 两种适配模式，并确认 `diagnose`、`analyze`、`generate` 可以生成有效 `SKILL.md`。

### 联系方式

由 jackz-jones 开发 — https://github.com/jackz-jones/experience-to-skill-generator

### 许可证

本项目使用 Apache License 2.0，详见 [LICENSE](LICENSE)。

