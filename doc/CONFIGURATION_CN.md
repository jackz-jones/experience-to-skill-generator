# 配置参考

> [English](CONFIGURATION.md)

### 1. 配置优先级

运行时配置按以下顺序合并，后者覆盖前者：

1. 默认配置 `DEFAULT_CONFIG`
2. `--config` 指定的 JSON 文件
3. 环境变量 `ESG_*`
4. CLI 参数，例如 `--input`、`--output-dir`、`--conflict`

---

### 2. 默认配置（DEFAULT_CONFIG）

代码内置的默认配置如下：

```json
{
  "agent": "auto",
  "compatibility_mode": true,
  "session_sources": [
    {
      "type": "openclaw",
      "path": "~/.openclaw/workspace/memory",
      "patterns": ["*.json", "*.jsonl", "*.md", "*.txt"]
    },
    {
      "type": "openclaw",
      "path": "~/.openclaw/agents",
      "patterns": ["*.jsonl", "*.json"]
    }
  ],
  "output": {
    "target_dir": "generated_skills",
    "format": "markdown",
    "conflict_strategy": "rename",
    "metadata_format": "generic"
  },
  "analysis": {
    "min_score": 50,
    "max_chars": 120000,
    "chunk_chars": 30000,
    "confidence_threshold": 0.55
  },
  "security": {
    "redact_sensitive": true,
    "preserve_raw": false
  },
  "templates": {
    "skill": "standard",
    "include_sources": true
  },
  "adapters": {}
}
```

#### 配置项说明

| 配置节 | 字段 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `session_sources` | `type` | `openclaw` | 会话来源类型：`openclaw`、`generic`、`custom` 或 `cli` |
| `session_sources` | `path` | `~/.openclaw/workspace/memory`、`~/.openclaw/agents` | 会话文件或目录路径 |
| `session_sources` | `patterns` | `["*.json", "*.jsonl", "*.md", "*.txt"]` | 目录扫描文件模式 |
| `output` | `target_dir` | `generated_skills` | 技能输出目录 |
| `output` | `format` | `markdown` | 当前仅支持 Markdown |
| `output` | `conflict_strategy` | `rename` | 冲突策略：`rename` / `skip` / `overwrite` / `merge` / `fail` |
| `output` | `metadata_format` | `generic` | metadata 渲染格式：`generic` / `openclaw` / `json` |
| `analysis` | `min_score` | `50` | 预留评分阈值 |
| `analysis` | `max_chars` | `120000` | 单次分析最大字符数 |
| `analysis` | `chunk_chars` | `30000` | 长会话分段大小 |
| `analysis` | `confidence_threshold` | `0.55` | 低于该值时标记需要人工审核 |
| `security` | `redact_sensitive` | `true` | 是否脱敏敏感信息 |
| `security` | `preserve_raw` | `false` | 是否保留会话原文 |
| `templates` | `skill` | `standard` | 生成模板：`standard` / `compact` / `checklist` |
| `templates` | `include_sources` | `true` | 是否在结果中包含来源文件信息 |

---

### 3. JSON 配置文件（--config）

通过 `--config` 参数指定 JSON 配置文件，其内容会覆盖默认配置。

```bash
experience-to-skill-generator --config ./config.json ...
```

示例配置文件：

```json
{
  "session_sources": [
    {
      "type": "openclaw",
      "path": "~/.openclaw/agents",
      "patterns": ["*.json", "*.jsonl"]
    }
  ],
  "output": {
    "target_dir": "./my-skills",
    "conflict_strategy": "merge"
  },
  "analysis": {
    "min_score": 60,
    "confidence_threshold": 0.6
  },
  "security": {
    "preserve_raw": true
  },
  "templates": {
    "skill": "compact"
  }
}
```

> 注意：`agent` 配置项固定为 `auto`，安装脚本和 CLI 会自动检测运行环境，无需手动修改。

---

### 4. 环境变量（ESG_*）

环境变量会覆盖默认配置和 JSON 配置文件中的对应项。

#### CLI 运行时变量

| 变量 | 影响配置 | 说明 |
| --- | --- | --- |
| `ESG_OUTPUT_DIR` | `output.target_dir` | 默认输出目录 |
| `ESG_SESSION_DIR` | `session_sources` | 默认会话来源目录；**同时会被 `install.sh` 读取作为安装阶段 adapter 的 `session_dir`** |
| `ESG_CONFLICT_STRATEGY` | `output.conflict_strategy` | 默认冲突策略 |
| `ESG_MIN_SCORE` | `analysis.min_score` | 评分阈值，必须是整数 |
| `ESG_PRESERVE_RAW` | `security.preserve_raw` | 是否保留原文 |
| `ESG_SKILL_DIR` | adapter `skill_dir` | 覆盖自动检测出的 adapter 技能输出目录；**`install.sh`（安装目标）和 CLI（运行时 adapter 覆盖）都会读取** |
| `ESG_CONFIG_DIR` | adapter `config_dir` | 覆盖自动检测出的 adapter 配置目录；**`install.sh`（安装目标）和 CLI（运行时 adapter 覆盖）都会读取** |

#### 仅安装脚本使用的变量

| 变量 | 说明 |
| --- | --- |
| `PYTHON_BIN` | 指定 Python 可执行文件，默认 `python3` |
| `ESG_INSTALL_MODE` | `auto` 或 `copy-only` |
| `ESG_NON_INTERACTIVE` | `1` 或 `true` 时跳过确认 |
| `ESG_BIN_DIR` | 命令入口目录，默认 `$HOME/.local/bin` |
| `ESG_EXAMPLES_DIR` | 示例会话目录 |
| `ESG_PROJECT_DIR` | CLI 源码所在项目目录 |

> 💡 `ESG_SKILL_DIR`、`ESG_CONFIG_DIR`、`ESG_SESSION_DIR` 同时被 `install.sh`（决定安装路径）**和** CLI 运行时（覆盖自动检测出的 adapter）读取。在 shell profile 中设置后，两个阶段会保持一致。

---

### 5. CLI 参数

CLI 参数优先级最高，会覆盖所有其他配置来源。

| 参数 | 可选值 | 说明 |
| --- | --- | --- |
| `--config` | 文件路径 | JSON 配置文件 |
| `--input` | 文件或目录路径 | 覆盖 `session_sources` |
| `--output-dir` | 目录路径 | 覆盖 `output.target_dir` |
| `--conflict` | `rename`、`skip`、`overwrite`、`merge`、`fail` | 覆盖 `output.conflict_strategy` |
| `--preserve-raw` | flag | 开启后保留会话原文 |

#### 子命令参数

| 子命令 | 参数 | 说明 |
| --- | --- | --- |
| `analyze` | `--json-lines` | 输出紧凑 JSON，便于脚本解析 |
| `generate` | `--name` | 指定生成的技能名称 |
| `config` | 无 | 输出合并配置和适配信息 |
| `validate-config` | 无 | 校验配置并输出结果 |
| `diagnose` | 无 | 诊断运行环境和会话来源 |

---

### 6. Agent 自动检测说明

#### 检测逻辑

安装脚本和 CLI 运行时会自动检测运行环境，决定安装模式和工作目录。检测流程如下：

1. 若检测到 `~/.openclaw` 目录或 `openclaw` 命令 → **OpenClaw 原生模式**
2. 否则 → **通用模式**

| 检测条件 | 安装模式 | 技能目录 | 配置目录 |
| --- | --- | --- | --- |
| 存在 `~/.openclaw` 目录或 `openclaw` 命令 | OpenClaw 原生技能 | `~/.openclaw/skills/experience-to-skill-generator` | `~/.openclaw/config/skills/experience-to-skill-generator` |
| 未检测到 OpenClaw | 通用模式 | `~/.experience-to-skill-generator/skills/experience-to-skill-generator` | `~/.experience-to-skill-generator/config` |

#### 两种模式的区别

| | OpenClaw 原生模式 | 通用模式 |
| --- | --- | --- |
| **谁在用** | 本地安装了 OpenClaw 的用户 | 使用其他 AI agent（Claude Code、Cursor 等）的用户 |
| **会话来源** | 自动从 `~/.openclaw/agents/` 读取 | 需手动将对话文件放到 `./sessions/` 或用 `--input` 指定 |
| **技能输出** | 自动安装到 OpenClaw 技能目录 | 输出到 `./generated_skills/`，需自行集成到 agent |
| **agent 自动加载** | ✅ OpenClaw 会自动识别技能目录下的技能 | ❌ 生成的 SKILL.md 不会自动被其他 agent 识别，需手动集成 |
| **metadata 格式** | `openclaw` 格式 | `generic` 格式 |

> 💡 **关键理解**：本工具的"自动检测"只是决定文件放到哪里、以什么格式输出。**只有 OpenClaw 有原生技能加载能力**，其他 agent（Claude Code、Cursor 等）不会自动识别生成的技能文件，需要你手动集成（例如将 SKILL.md 内容贴到对话开头，或写入项目的 `CLAUDE.md` / `.cursorrules` 文件）。

#### adapters 配置

`adapters` 用于扩展本工具对新 agent 目录结构的识别。内置两个 adapter：`openclaw` 和 `generic`。

**它的作用**：让工具知道新 agent 的技能目录、配置目录、会话目录在哪里，从而：
- 在自动检测时，通过 `markers` 字段判断该 agent 是否存在
- 将 SKILL.md 输出到该 agent 对应的目录下

**它的局限**：`adapters` 只是让**本工具**知道目录布局，**不能让 agent 自动加载技能**。agent 是否识别和使用技能，取决于 agent 自身的能力。

配置示例：

```json
{
  "adapters": {
    "my-agent": {
      "markers": [".my-agent"],
      "skill_dir": "~/.my-agent/skills",
      "config_dir": "~/.my-agent/config/experience-to-skill-generator",
      "session_dir": "~/.my-agent/sessions",
      "metadata_format": "generic"
    }
  }
}
```

各字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `markers` | `string[]` | 用于检测 agent 是否存在的文件或目录标记。检测时会在用户主目录下查找这些标记是否存在 |
| `skill_dir` | `string` | 技能文件输出目录，工具会将生成的 SKILL.md 写入此目录 |
| `config_dir` | `string` | 工具自身的配置目录，用于存放 config.json 等 |
| `session_dir` | `string` | 该 agent 的会话文件目录，工具在 `auto` 模式下会从此目录读取会话 |
| `metadata_format` | `string` | SKILL.md 中 metadata 的渲染格式，可选值：`generic`、`openclaw`、`json` |

---

### 7. 校验配置

```bash
experience-to-skill-generator --config ./config.json validate-config
```

成功输出：

```json
{
  "valid": true,
  "adapter_strategy": "auto:generic-fallback",
  "config_path": "/path/to/config.json"
}
```

校验失败示例：

```json
{
  "valid": false,
  "error": "配置项 output.conflict_strategy 只能是 rename、skip、overwrite、merge 或 fail"
}
```

#### 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 成功 |
| `2` | 配置或运行时错误（如会话文件不存在、配置项非法、冲突策略为 `fail` 时同名技能已存在等） |
| `130` | 用户中断（Ctrl+C） |

> 💡 退出码 `2` 对应代码中 `UserFacingError` 异常的捕获，所有面向用户的错误（配置校验失败、会话文件问题、冲突处理失败等）统一返回此退出码，便于脚本化判断。