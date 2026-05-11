# Configuration Reference

> [中文](CONFIGURATION_CN.md)

### 1. Precedence

Runtime configuration is merged in this order. Later sources override earlier ones:

1. Built-in `DEFAULT_CONFIG`
2. JSON file passed by `--config`
3. `ESG_*` environment variables
4. CLI flags such as `--input`, `--output-dir`, and `--conflict`

---

### 2. Default Configuration (DEFAULT_CONFIG)

The built-in default configuration:

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

#### Config key descriptions

| Section | Field | Default | Description |
| --- | --- | --- | --- |
| `session_sources` | `type` | `openclaw` | Session source type: `openclaw`, `generic`, `custom`, or `cli` |
| `session_sources` | `path` | `~/.openclaw/workspace/memory`, `~/.openclaw/agents` | Session file or directory path |
| `session_sources` | `patterns` | `["*.json", "*.jsonl", "*.md", "*.txt"]` | File glob patterns for directory scanning |
| `output` | `target_dir` | `generated_skills` | Skill output directory |
| `output` | `format` | `markdown` | Currently generates Markdown only |
| `output` | `conflict_strategy` | `rename` | Conflict strategy: `rename` / `skip` / `overwrite` / `merge` / `fail` |
| `output` | `metadata_format` | `generic` | Metadata rendering format: `generic` / `openclaw` / `json` |
| `analysis` | `min_score` | `50` | Reserved score threshold |
| `analysis` | `max_chars` | `120000` | Max characters per analysis |
| `analysis` | `chunk_chars` | `30000` | Chunk size for long sessions |
| `analysis` | `confidence_threshold` | `0.55` | Below this value, mark for human review |
| `security` | `redact_sensitive` | `true` | Whether to redact sensitive information |
| `security` | `preserve_raw` | `false` | Whether to preserve raw session content |
| `templates` | `skill` | `standard` | Generation template: `standard` / `compact` / `checklist` |
| `templates` | `include_sources` | `true` | Whether to include source file info in results |

---

### 3. JSON Configuration File (--config)

The JSON config file overrides the default configuration:

```bash
experience-to-skill-generator --config ./config.json ...
```

Example config file:

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

> Note: The `agent` config key is fixed to `auto`. The installer and CLI auto-detect the runtime environment — no manual setting needed.

---

### 4. Environment Variables (ESG_*)

Environment variables override both the default config and the JSON config file.

#### CLI runtime variables

| Variable | Config key | Description |
| --- | --- | --- |
| `ESG_OUTPUT_DIR` | `output.target_dir` | Default output directory |
| `ESG_SESSION_DIR` | `session_sources` | Default session source directory; **also read by `install.sh` to set the adapter's `session_dir` at install time** |
| `ESG_CONFLICT_STRATEGY` | `output.conflict_strategy` | Default conflict strategy |
| `ESG_MIN_SCORE` | `analysis.min_score` | Score threshold; must be an integer |
| `ESG_PRESERVE_RAW` | `security.preserve_raw` | Whether to preserve raw content |
| `ESG_SKILL_DIR` | adapter `skill_dir` | Overrides the auto-detected adapter's skill output directory; **read by both `install.sh` (install target) and the CLI (runtime adapter override)** |
| `ESG_CONFIG_DIR` | adapter `config_dir` | Overrides the auto-detected adapter's config directory; **read by both `install.sh` (install target) and the CLI (runtime adapter override)** |

#### Installer-only variables

| Variable | Description |
| --- | --- |
| `PYTHON_BIN` | Python executable, defaults to `python3` |
| `ESG_INSTALL_MODE` | `auto` or `copy-only` |
| `ESG_NON_INTERACTIVE` | Set to `1` or `true` to skip confirmation |
| `ESG_LANG` | CLI help text language: `zh` (Chinese) or `en` (English). During interactive install, the user is prompted to choose; in non-interactive mode, auto-detected from system `LANG`. The chosen value is baked into the command wrapper script |
| `ESG_BIN_DIR` | Command entry directory, defaults to `$HOME/.local/bin` |
| `ESG_EXAMPLES_DIR` | Sample session directory |
| `ESG_PROJECT_DIR` | CLI source project directory |

> 💡 `ESG_SKILL_DIR`, `ESG_CONFIG_DIR`, `ESG_SESSION_DIR` are read by both `install.sh` (to decide install paths) **and** the CLI at runtime (to override the auto-detected adapter). If you set them in your shell profile, both phases will pick them up consistently.

---

### 5. CLI Flags

CLI flags have the highest precedence and override all other configuration sources.

| Flag | Values | Description |
| --- | --- | --- |
| `--config` | file path | JSON configuration file |
| `--input` | file or directory | Overrides `session_sources` |
| `--output-dir` | directory | Overrides `output.target_dir` |
| `--conflict` | `rename`, `skip`, `overwrite`, `merge`, `fail` | Overrides `output.conflict_strategy` |
| `--preserve-raw` | flag | Preserves raw session content |

#### Subcommand flags

| Subcommand | Flag | Description |
| --- | --- | --- |
| `analyze` | `--json-lines` | Outputs compact JSON for script parsing |
| `generate` | `--name` | Specifies the skill name to generate |
| `config` | none | Prints merged config and adapter info |
| `validate-config` | none | Validates config and prints result |
| `diagnose` | none | Diagnoses runtime environment and session sources |

---

### 6. Agent Auto-Detection

#### Detection Logic

The install script and CLI auto-detect the runtime environment and determine the install mode and working directories. The detection flow is:

1. If `~/.openclaw` directory or `openclaw` command is detected → **OpenClaw native mode**
2. Otherwise → **Generic mode**

| Detection Condition | Install Mode | Skill Directory | Config Directory |
| --- | --- | --- | --- |
| `~/.openclaw` directory or `openclaw` command exists | OpenClaw native skill | `~/.openclaw/skills/experience-to-skill-generator` | `~/.openclaw/config/skills/experience-to-skill-generator` |
| OpenClaw not detected | Generic mode | `~/.experience-to-skill-generator/skills/experience-to-skill-generator` | `~/.experience-to-skill-generator/config` |

#### Differences Between Modes

| | OpenClaw Native Mode | Generic Mode |
| --- | --- | --- |
| **Who uses it** | Users with OpenClaw installed locally | Users of other AI agents (Claude Code, Cursor, etc.) |
| **Session source** | Automatically reads from `~/.openclaw/agents/` | Manually place conversation files in `./sessions/` or specify with `--input` |
| **Skill output** | Auto-installs to OpenClaw skill directory | Outputs to `./generated_skills/`, requires manual integration with agent |
| **Agent auto-loading** | ✅ OpenClaw automatically recognizes skills in its skill directory | ❌ Generated SKILL.md is not automatically recognized by other agents; manual integration required |
| **Metadata format** | `openclaw` format | `generic` format |

> 💡 **Key point**: The "auto-detection" only determines where files are placed and what format is used. **Only OpenClaw has native skill-loading capability**. Other agents (Claude Code, Cursor, etc.) will not automatically recognize generated skill files — you need to manually integrate them (e.g., paste SKILL.md content at the start of a conversation, or write it into the project's `CLAUDE.md` / `.cursorrules` file).

#### Adapters Configuration

The `adapters` config extends this tool's recognition of new agent directory structures. Two adapters are built-in: `openclaw` and `generic`.

**What it does**: Tells the tool where a new agent's skill directory, config directory, and session directory are, so that:
- During auto-detection, the `markers` field is used to check if the agent exists
- SKILL.md is output to the agent's corresponding directory

**Limitations**: `adapters` only tells **this tool** about directory layouts — it does **not** make the agent automatically load skills. Whether an agent recognizes and uses skills depends on the agent's own capabilities.

Configuration example:

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

Field descriptions:

| Field | Type | Description |
| --- | --- | --- |
| `markers` | `string[]` | File or directory markers used to detect if the agent exists. During detection, these markers are looked up in the user's home directory |
| `skill_dir` | `string` | Skill output directory; the tool writes generated SKILL.md files here |
| `config_dir` | `string` | The tool's own config directory, used for storing config.json etc. |
| `session_dir` | `string` | The agent's session file directory; the tool reads sessions from here in `auto` mode |
| `metadata_format` | `string` | Metadata rendering format in SKILL.md. Options: `generic`, `openclaw`, `json` |

---

### 7. Validate Configuration

```bash
experience-to-skill-generator --config ./config.json validate-config
```

Success output:

```json
{
  "valid": true,
  "adapter_strategy": "auto:generic-fallback",
  "config_path": "/path/to/config.json"
}
```

Validation failure example:

```json
{
  "valid": false,
  "error": "配置项 output.conflict_strategy 只能是 rename、skip、overwrite、merge 或 fail"
}
```

#### Exit Codes

| Exit Code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | Configuration or runtime error (e.g., session file not found, invalid config value, conflict strategy set to `fail` and a same-name skill already exists) |
| `130` | User interrupt (Ctrl+C) |

> 💡 Exit code `2` corresponds to the `UserFacingError` exception in the code. All user-facing errors (config validation failure, session file issues, conflict handling failure, etc.) return this exit code, making it easy to script error detection.