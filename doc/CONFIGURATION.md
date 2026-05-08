# Configuration Reference

> [中文](CONFIGURATION_CN.md)

### Precedence

Runtime configuration is merged in this order. Later sources override earlier ones:

1. Built-in `DEFAULT_CONFIG`
2. JSON file passed by `--config`
3. `ESG_*` environment variables
4. CLI flags such as `--input`, `--output-dir`, and `--conflict`

### Global CLI flags

| Flag | Values | Description |
| --- | --- | --- |
| `--config` | file path | JSON configuration file |
| `--agent` | `auto`, `openclaw`, `generic` | Agent adapter strategy |
| `--input` | file or directory | Overrides `session_sources` |
| `--output-dir` | directory | Overrides `output.target_dir` |
| `--conflict` | `rename`, `skip`, `overwrite`, `merge`, `fail` | Overrides `output.conflict_strategy` |
| `--preserve-raw` | flag | Preserves raw session content |

### Subcommand flags

| Subcommand | Flag | Description |
| --- | --- | --- |
| `analyze` | `--json-lines` | Outputs compact JSON for script parsing |
| `generate` | `--name` | Specifies the skill name to generate |
| `config` | none | Prints merged config and adapter info |
| `validate-config` | none | Validates config and prints result |
| `diagnose` | none | Diagnoses runtime environment and session sources |

### Environment variables

#### CLI runtime variables

| Variable | Config key | Description |
| --- | --- | --- |
| `ESG_AGENT` | `agent` | `auto`, `openclaw`, or `generic` |
| `ESG_OUTPUT_DIR` | `output.target_dir` | Default output directory |
| `ESG_SESSION_DIR` | `session_sources` | Default session source directory |
| `ESG_CONFLICT_STRATEGY` | `output.conflict_strategy` | Default conflict strategy |
| `ESG_MIN_SCORE` | `analysis.min_score` | Score threshold; must be an integer |
| `ESG_PRESERVE_RAW` | `security.preserve_raw` | Whether to preserve raw content |
| `ESG_SKILL_DIR` | adapter `skill_dir` | Override target skill directory |
| `ESG_CONFIG_DIR` | adapter `config_dir` | Override target config directory |

#### Installer variables

| Variable | Description |
| --- | --- |
| `PYTHON_BIN` | Python executable, defaults to `python3` |
| `ESG_AGENT` | Install strategy: `auto`, `openclaw`, `generic` |
| `ESG_INSTALL_MODE` | `auto` or `copy-only` |
| `ESG_NON_INTERACTIVE` | Set to `1` or `true` to skip confirmation |
| `ESG_SKILL_DIR` | Target skill directory for installation |
| `ESG_CONFIG_DIR` | Target config directory for installation |
| `ESG_BIN_DIR` | Command entry directory, defaults to `$HOME/.local/bin` |
| `ESG_EXAMPLES_DIR` | Sample session directory |
| `ESG_PROJECT_DIR` | CLI source project directory |

### Example config

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

### Config key reference

#### `agent`

| Value | Behavior |
| --- | --- |
| `auto` | Auto-detect OpenClaw; fall back to generic |
| `openclaw` | Use OpenClaw adapter strategy |
| `generic` | Use generic directory strategy |

#### `session_sources`

Each entry contains:

| Field | Type | Description |
| --- | --- | --- |
| `type` | string | `openclaw`, `generic`, `custom`, or `cli` |
| `path` | string | Session file or directory |
| `patterns` | string[] | File glob patterns for directory scanning |

#### `output`

| Field | Values | Description |
| --- | --- | --- |
| `target_dir` | path | Skill output directory |
| `format` | `markdown` | Currently generates Markdown |
| `conflict_strategy` | `rename`, `skip`, `overwrite`, `merge`, `fail` | Conflict strategy |
| `metadata_format` | `generic`, `openclaw`, `json` | Metadata rendering format |

#### `analysis`

| Field | Default | Description |
| --- | --- | --- |
| `min_score` | `50` | Reserved score threshold |
| `max_chars` | `120000` | Max characters per analysis |
| `chunk_chars` | `30000` | Chunk size for long sessions |
| `confidence_threshold` | `0.55` | Below this value, mark for human review |

#### `security`

| Field | Default | Description |
| --- | --- | --- |
| `redact_sensitive` | `true` | Whether to redact sensitive information |
| `preserve_raw` | `false` | Whether to preserve raw session content |

#### `templates`

| Field | Values | Description |
| --- | --- | --- |
| `skill` | `standard`, `compact`, `checklist` | Generation template |
| `include_sources` | `true`, `false` | Whether to include source file info in results |

#### `adapters`

Used to extend new agents:

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

### Validate config

```bash
experience-to-skill-generator --config ./config.json validate-config
```

Success output:

```json
{
  "valid": true,
  "agent": "generic",
  "adapter_strategy": "explicit:generic",
  "config_path": "/path/to/config.json"
}
```