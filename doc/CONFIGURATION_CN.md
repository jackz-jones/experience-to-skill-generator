# 配置参考

> [English](CONFIGURATION.md)

### 配置优先级

运行时配置按以下顺序合并，后者覆盖前者：

1. 默认配置 `DEFAULT_CONFIG`
2. `--config` 指定的 JSON 文件
3. 环境变量 `ESG_*`
4. CLI 参数，例如 `--input`、`--output-dir`、`--conflict`

### CLI 全局参数

| 参数 | 可选值 | 说明 |
| --- | --- | --- |
| `--config` | 文件路径 | JSON 配置文件 |
| `--agent` | `auto`、`openclaw`、`generic` | agent 适配策略 |
| `--input` | 文件或目录路径 | 覆盖 `session_sources` |
| `--output-dir` | 目录路径 | 覆盖 `output.target_dir` |
| `--conflict` | `rename`、`skip`、`overwrite`、`merge`、`fail` | 覆盖 `output.conflict_strategy` |
| `--preserve-raw` | flag | 开启后保留会话原文 |

### 子命令参数

| 子命令 | 参数 | 说明 |
| --- | --- | --- |
| `analyze` | `--json-lines` | 输出紧凑 JSON，便于脚本解析 |
| `generate` | `--name` | 指定生成的技能名称 |
| `config` | 无 | 输出合并配置和适配信息 |
| `validate-config` | 无 | 校验配置并输出结果 |
| `diagnose` | 无 | 诊断运行环境和会话来源 |

### 环境变量

#### CLI 运行时变量

| 变量 | 影响配置 | 说明 |
| --- | --- | --- |
| `ESG_AGENT` | `agent` | `auto`、`openclaw` 或 `generic` |
| `ESG_OUTPUT_DIR` | `output.target_dir` | 默认输出目录 |
| `ESG_SESSION_DIR` | `session_sources` | 默认会话来源目录 |
| `ESG_CONFLICT_STRATEGY` | `output.conflict_strategy` | 默认冲突策略 |
| `ESG_MIN_SCORE` | `analysis.min_score` | 评分阈值，必须是整数 |
| `ESG_PRESERVE_RAW` | `security.preserve_raw` | 是否保留原文 |
| `ESG_SKILL_DIR` | adapter `skill_dir` | 覆盖目标技能目录 |
| `ESG_CONFIG_DIR` | adapter `config_dir` | 覆盖目标配置目录 |

#### 安装脚本变量

| 变量 | 说明 |
| --- | --- |
| `PYTHON_BIN` | 指定 Python 可执行文件，默认 `python3` |
| `ESG_AGENT` | 安装策略：`auto`、`openclaw`、`generic` |
| `ESG_INSTALL_MODE` | `auto` 或 `copy-only` |
| `ESG_NON_INTERACTIVE` | `1` 或 `true` 时跳过确认 |
| `ESG_SKILL_DIR` | 安装目标技能目录 |
| `ESG_CONFIG_DIR` | 安装目标配置目录 |
| `ESG_BIN_DIR` | 命令入口目录，默认 `$HOME/.local/bin` |
| `ESG_EXAMPLES_DIR` | 示例会话目录 |
| `ESG_PROJECT_DIR` | CLI 源码所在项目目录 |

### JSON 配置示例

```json
{
  "agent": "auto",
  "compatibility_mode": true,
  "session_sources": [
    {
      "type": "generic",
      "path": "./sessions",
      "patterns": ["*.json", "*.jsonl", "*.md", "*.txt"]
    }
  ],
  "output": {
    "target_dir": "./generated_skills",
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

### 配置项说明

#### `agent`

| 值 | 行为 |
| --- | --- |
| `auto` | 自动检测 OpenClaw，否则回退到 generic |
| `openclaw` | 使用 OpenClaw 适配策略 |
| `generic` | 使用通用目录策略 |

#### `session_sources`

每项包含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `type` | string | `openclaw`、`generic`、`custom` 或 `cli` |
| `path` | string | 会话文件或目录 |
| `patterns` | string[] | 目录扫描文件模式 |

#### `output`

| 字段 | 可选值 | 说明 |
| --- | --- | --- |
| `target_dir` | 路径 | 技能输出目录 |
| `format` | `markdown` | 当前生成 Markdown |
| `conflict_strategy` | `rename`、`skip`、`overwrite`、`merge`、`fail` | 冲突策略 |
| `metadata_format` | `generic`、`openclaw`、`json` | metadata 渲染格式 |

#### `analysis`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `min_score` | `50` | 预留评分阈值 |
| `max_chars` | `120000` | 单次分析最大字符数 |
| `chunk_chars` | `30000` | 长会话分段大小 |
| `confidence_threshold` | `0.55` | 低于该值时标记需要人工审核 |

#### `security`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `redact_sensitive` | `true` | 是否脱敏敏感信息 |
| `preserve_raw` | `false` | 是否保留会话原文 |

#### `templates`

| 字段 | 可选值 | 说明 |
| --- | --- | --- |
| `skill` | `standard`、`compact`、`checklist` | 生成模板 |
| `include_sources` | `true`、`false` | 是否在结果中包含来源文件信息 |

#### `adapters`

用于扩展新 agent：

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

### 校验配置

```bash
experience-to-skill-generator --config ./config.json validate-config
```

成功输出：

```json
{
  "valid": true,
  "agent": "generic",
  "adapter_strategy": "explicit:generic",
  "config_path": "/path/to/config.json"
}
```