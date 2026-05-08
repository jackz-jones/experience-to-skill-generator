# Experience-to-Skill Generator

> [中文](README_CN.md)

Experience-to-Skill Generator is a universal SKILL generator for agent conversations. It reads OpenClaw or generic session logs, extracts task goals, key steps, constraints, and reusable practices, then writes a structured `SKILL.md` for knowledge reuse and human review.

### What it does

- **Agent adaptation**: supports `auto`, `openclaw`, and `generic`, with extension points for custom agents.
- **Session ingestion**: reads `json`, `jsonl`, `md`, and `txt` files from a single file or directory.
- **Long-session handling**: chunks long conversations and applies controlled truncation.
- **Sensitive data redaction**: redacts tokens, secrets, emails, and private paths by default.
- **Structured SKILL output**: includes usage scenarios, trigger conditions, execution steps, cautions, examples, and metadata.
- **Conflict-safe writing**: supports `rename`, `skip`, `overwrite`, `merge`, and `fail`.
- **Scriptable CLI**: provides JSON output, stable exit codes, config inspection, diagnostics, and end-to-end validation.

### Use cases

- **OpenClaw session review**: read conversation records from OpenClaw workspaces or agent directories.
- **Generic agent compatibility**: generate skills from any `json`, `jsonl`, `md`, or `txt` session directory.
- **Automation integration**: use JSON output, stable exit codes, and conflict strategies in CI or scheduled jobs.
- **Human review workflow**: mark generated skills for review when confidence is low.
- **Enterprise knowledge management**: automatically turn team discussions into standardized skill documents.
- **Developer toolkit**: automate workflow capture and script recording for personal productivity.

### Documentation

- **Technical Design**: [doc/TECHNICAL_DESIGN.md](doc/TECHNICAL_DESIGN.md)
- **Configuration Reference**: [doc/CONFIGURATION.md](doc/CONFIGURATION.md)
- **OpenClaw Skill Definition**: [skills/experience-to-skill-generator/SKILL.md](skills/experience-to-skill-generator/SKILL.md)

### Directory structure

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
│   ├── universal_skill_generator.py       # Core CLI entry point
│   ├── analyze_conversation.py            # Session analysis module
│   ├── generate_skill.py                  # SKILL rendering module
│   ├── vector_skill_optimizer.py          # Vector similarity engine (numpy optional)
│   ├── e2e_validate_universal_skill_generator.py
│   └── test_universal_skill_generator.py
└── skills/
    └── experience-to-skill-generator/
        ├── SKILL.md
        ├── config.json
        └── install.sh
```

### Quick start

#### 1. Run from source

```bash
python3 python-scripts/universal_skill_generator.py \
  --agent generic \
  --input ./sessions/session.json \
  --output-dir ./generated_skills \
  --conflict rename \
  generate --name reusable-flow
```

The generated file is written to:

```text
./generated_skills/reusable-flow/SKILL.md
```

#### 2. Install as a local command

```bash
ESG_AGENT=generic ESG_NON_INTERACTIVE=1 \
./skills/experience-to-skill-generator/install.sh
```

Then run:

```bash
experience-to-skill-generator --agent generic --input ./sessions diagnose
experience-to-skill-generator --agent generic --input ./sessions/session.json analyze --json-lines
experience-to-skill-generator --agent generic --input ./sessions/session.json --output-dir ./generated_skills generate --name reusable-flow
```

#### 3. Install for OpenClaw

```bash
ESG_AGENT=openclaw ESG_NON_INTERACTIVE=1 \
./skills/experience-to-skill-generator/install.sh
```

If the `openclaw` command is unavailable, the installer falls back to copy-only behavior so the universal CLI remains usable.

#### 4. Custom install paths

```bash
ESG_AGENT=generic \
ESG_SKILL_DIR="$HOME/.agent/skills/experience-to-skill-generator" \
ESG_CONFIG_DIR="$HOME/.agent/config/experience-to-skill-generator" \
ESG_BIN_DIR="$HOME/.local/bin" \
ESG_NON_INTERACTIVE=1 \
./skills/experience-to-skill-generator/install.sh
```

### Commands

```bash
python3 python-scripts/universal_skill_generator.py [global options] <command> [command options]
```

After installation:

```bash
experience-to-skill-generator [global options] <command> [command options]
```

| Command | Description |
| --- | --- |
| `diagnose` | Inspect Python, adapter strategy, and session sources |
| `analyze` | Read sessions and print structured analysis JSON |
| `generate` | Analyze sessions and write a structured `SKILL.md` |
| `config` | Print merged configuration and adapter details |
| `validate-config` | Validate config files, environment variables, and CLI overrides |

Common global flags:

| Flag | Description |
| --- | --- |
| `--config` | JSON configuration file path |
| `--agent` | `auto`, `openclaw`, or `generic` |
| `--input` | Session file or directory path |
| `--output-dir` | Output directory for generated skills |
| `--conflict` | `rename`, `skip`, `overwrite`, `merge`, or `fail` |
| `--preserve-raw` | Preserve raw content; make sure no sensitive data is exposed |

#### Analyze output

The `analyze` command outputs structured JSON containing:

- `summary`: message count, source file, chunk info, and analysis time.
- `tasks`: main tasks extracted from user messages.
- `key_steps`: key steps extracted from assistant messages.
- `constraints`: requirements, prohibitions, and cautions.
- `keywords`: extracted keywords.
- `confidence`: analysis confidence score.
- `requires_review`: whether human review is recommended.

#### Generate example

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

### Supported inputs

| Format | Behavior |
| --- | --- |
| `.json` | Reads `messages`, `conversation`, or a single `message` object |
| `.jsonl` | Reads one JSON object per line; invalid lines are treated as text |
| `.md` | Uses the whole file as one text message |
| `.txt` | Uses the whole file as one text message |

Recommended JSON example:

```json
{
  "messages": [
    {"role": "user", "content": "Implement a universal install script; must not overwrite existing skills"},
    {"role": "assistant", "content": "1. Check dependencies\n2. Detect agent environment\n3. Write skill and handle conflicts"}
  ]
}
```

### Output structure

Each skill is written to:

```text
<output-dir>/<skill-name>/SKILL.md
```

Standard template sections:

- `metadata`
- `Usage Scenarios`
- `Trigger Conditions`
- `Execution Steps`
- `Cautions`
- `Example Usage`
- `Quality & Source`

### Configuration

Configuration precedence (low to high):

1. Built-in defaults in `python-scripts/universal_skill_generator.py`
2. JSON file specified by `--config`
3. `ESG_*` environment variables
4. CLI flags

Common environment variables:

| Variable | Description |
| --- | --- |
| `ESG_AGENT` | `auto`, `openclaw`, or `generic` |
| `ESG_SESSION_DIR` | Default session source directory |
| `ESG_OUTPUT_DIR` | Default skill output directory |
| `ESG_CONFLICT_STRATEGY` | Default conflict strategy |
| `ESG_MIN_SCORE` | Analysis score threshold |
| `ESG_PRESERVE_RAW` | Whether to preserve raw session content |
| `ESG_SKILL_DIR` | Installer target skill directory |
| `ESG_CONFIG_DIR` | Installer target config directory |
| `ESG_BIN_DIR` | Installer command entry directory |
| `ESG_NON_INTERACTIVE` | Set to `1` to skip install confirmation |
| `ESG_INSTALL_MODE` | Set to `copy-only` to skip agent registration |

See [doc/CONFIGURATION.md](doc/CONFIGURATION.md) for full reference.

### Security and conflict handling

Defaults:

- **Redaction enabled**: tokens, secrets, emails, and private paths are cleaned from analysis, generated docs, and diagnostics.
- **Atomic writes**: writes to a temporary file first, then replaces the target `SKILL.md`.
- **Conflict control**: same-name or similar skills are handled by the `--conflict` strategy.

Conflict strategies:

| Strategy | Behavior | Use case |
| --- | --- | --- |
| `rename` | Auto-generates `name-2`, `name-3`, etc. | Recommended default; preserves history |
| `skip` | Keeps existing skill, writes nothing | Batch jobs to avoid duplicates |
| `overwrite` | Creates `.bak` backup before replacing | Explicit refresh of a same-name skill |
| `merge` | Appends new content to existing `SKILL.md` | Accumulate multiple sessions into one skill |
| `fail` | Returns non-zero exit code on conflict | CI or strict automation pipelines |

Redaction covers:

- API key, token, secret, password
- Bearer token, OpenAI key, AWS key, GitHub token, Slack token
- Private keys, SSH public key fragments
- Email addresses
- Private paths such as `/Users/<name>`, `/home/<name>`, `/root/...`

To preserve raw content:

```bash
experience-to-skill-generator --preserve-raw --input ./sessions analyze
```

Make sure the session content does not expose sensitive information before enabling this option.

### Automation example

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

### Deliverables

| Category | Files |
| --- | --- |
| Core CLI | `universal_skill_generator.py`, `analyze_conversation.py`, `generate_skill.py`, `vector_skill_optimizer.py` |
| Testing | `test_universal_skill_generator.py`, `e2e_validate_universal_skill_generator.py` |
| OpenClaw skill | `skills/experience-to-skill-generator/SKILL.md`, `skills/experience-to-skill-generator/config.json`, `skills/experience-to-skill-generator/install.sh` |
| Documentation | `README.md`, `README_CN.md`, `doc/TECHNICAL_DESIGN.md`, `doc/TECHNICAL_DESIGN_CN.md`, `doc/CONFIGURATION.md`, `doc/CONFIGURATION_CN.md` |

### Verification checklist

- ✅ **Feature completeness** — all CLI subcommands implemented and tested
- ✅ **Multi-agent adaptation** — supports `openclaw` and `generic` adapter modes
- ✅ **Integration maturity** — complete OpenClaw skill adaptation + universal CLI
- ✅ **Code quality** — Python scripts pass unit tests and end-to-end validation
- ✅ **Documentation completeness** — bilingual technical design and configuration reference

### Validation

Unit tests:

```bash
python3 -m unittest python-scripts/test_universal_skill_generator.py
```

End-to-end validation:

```bash
python3 python-scripts/e2e_validate_universal_skill_generator.py
```

The e2e validation covers both `generic` and `openclaw` adapters and confirms that `diagnose`, `analyze`, and `generate` produce valid `SKILL.md` files.

### Contact

Developed by jackz-jones — https://github.com/jackz-jones/experience-to-skill-generator

### License

Apache License 2.0. See [LICENSE](LICENSE).