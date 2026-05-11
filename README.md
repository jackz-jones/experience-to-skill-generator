# Experience-to-Skill Generator

> [中文](README_CN.md)

Turn your AI conversation logs into reusable skill documents — with a single command.

## 1. What is this?

Experience-to-Skill Generator is a CLI tool that **automatically analyzes your AI conversation history**, extracts valuable workflows, technical solutions, and best practices, then generates a structured `SKILL.md` skill document.

**Core design philosophy**: The tool acts as a "data pipeline" (read → preprocess → template rendering → write). Semantic analysis is delegated to the agent's own LLM. No extra LLM API Key configuration needed.

The generated `SKILL.md` can be used by AI agents as a skill. OpenClaw loads it automatically; other agents (Claude Code, Cursor, etc.) require manual integration (paste at conversation start, write into `CLAUDE.md` / `.cursorrules`, etc.).

## 2. What can I do with it?

| Scenario | Description | Who is it for |
| --- | --- | --- |
| 🏢 **Team Knowledge Capture** | Turn code reviews, technical discussions, and team conversations into standardized skill documents | Tech team leads |
| 👨‍💻 **Developer Toolkit** | Distill your AI conversations into reusable workflows | Developers |
| 🤖 **OpenClaw Skill Integration** | Use as an OpenClaw skill package, invoked automatically by the agent | OpenClaw users |
| 🏭 **Automation / CI Integration** | Integrate with automation pipelines using JSON output and stable exit codes | DevOps / SRE |

## 3. Quick Start

### Prerequisites

Python 3.8+ (no other dependencies required; `numpy` / `scikit-learn` are optional for acceleration)

### Option A: Run from source (no installation needed)

```bash
# Clone the repo
git clone https://github.com/jackz-jones/experience-to-skill-generator.git
cd experience-to-skill-generator

# Prepare session files (place in sessions/ directory; supports .json / .jsonl / .md / .txt)
mkdir sessions
cp /path/to/your/ai-conversation.json sessions/

# ① Diagnose environment (recommended first step)
python3 python-scripts/universal_skill_generator.py --input ./sessions diagnose

# ② Preprocess session (output structured text for LLM analysis)
python3 python-scripts/universal_skill_generator.py --input ./sessions/session.json extract

# ③ Analyze using built-in rule engine (fallback, no LLM required)
python3 python-scripts/universal_skill_generator.py --input ./sessions/session.json analyze

# ④ Generate skill document (with external LLM analysis result)
python3 python-scripts/universal_skill_generator.py \
  --input ./sessions/session.json \
  --output-dir ./generated_skills \
  generate --name my-first-skill \
  --analysis '{"tasks":[...],"key_steps":[...],"constraints":[...],"keywords":[...],"confidence":0.85}'

# ⑤ Generate skill document (using built-in rule engine, no --analysis)
python3 python-scripts/universal_skill_generator.py \
  --input ./sessions/session.json \
  --output-dir ./generated_skills \
  generate --name my-first-skill
```

### Option B: Install as a local command (recommended for daily use)

```bash
# Interactive install (prompts you to choose CLI language)
./skills/experience-to-skill-generator/install.sh

# Or specify language + skip interactive confirmation
ESG_LANG=en ESG_NON_INTERACTIVE=1 ./skills/experience-to-skill-generator/install.sh

# After installation, use the short command directly (help text uses the language chosen during install)
experience-to-skill-generator --input ./sessions/session.json analyze
experience-to-skill-generator --input ./sessions/session.json --output-dir ./generated_skills generate --name my-skill
```

> 💡 The install script auto-detects your environment: if OpenClaw is detected, it installs as a native skill; otherwise it uses generic mode. No manual selection needed.
>
> 💡 During installation, you choose the CLI help text language (Chinese/English). The choice is baked into the command wrapper — no need to set environment variables afterwards. To temporarily switch: `ESG_LANG=zh experience-to-skill-generator --help`

### Session File Format

Supports `.json`, `.jsonl`, `.md`, and `.txt` formats. Recommended JSON format:

```json
{
  "messages": [
    {"role": "user", "content": "Implement a universal install script; must not overwrite existing skills"},
    {"role": "assistant", "content": "1. Check dependencies\n2. Detect agent environment\n3. Write skill and handle conflicts"}
  ]
}
```

<details>
<summary>👉 Where to Find Agent Conversation Files</summary>

#### 🟣 OpenClaw

```bash
~/.openclaw/agents/           # Conversation file directory
~/.openclaw/workspace/memory/ # Workspace memory directory
```

OpenClaw automatically saves each agent conversation under `~/.openclaw/agents/`.

#### 🟢 Claude Code (CLI)

```bash
~/.claude/projects/<project-path>/*.jsonl  # Per-project archived conversations (JSONL format)
~/.claude/history.jsonl                     # Global history log
```

```bash
# Copy a project session to the sessions directory
cp ~/.claude/projects/-Users-zx-Desktop-ai-myproject/<session-id>.jsonl ./sessions/
```

#### 🟡 Hermes

```bash
~/.hermes/sessions/          # Session file directory (*.jsonl, *.json)
~/.hermes/.hermes_history    # Conversation history file
```

#### 🔵 Cursor

```bash
~/Library/Application Support/Cursor/Session Storage/  # LevelDB database, not plain JSON files
```

Cursor uses browser-style storage. We recommend manually copying conversation content from the editor.

#### ⚪ ChatGPT (Desktop App)

No standard export function. Copy conversation content from the web interface and save as `.json` or `.md` files.

</details>

## 4. What's in the Generated SKILL.md?

| Section | Description |
| --- | --- |
| `metadata` | Metadata (skill name, version, source, etc.) |
| `Usage Scenarios` | When to use this skill |
| `Trigger Conditions` | What triggers it |
| `Execution Steps` | Step-by-step instructions |
| `Cautions` | What to watch out for |
| `Example Usage` | Real-world examples |
| `Quality & Source` | Confidence score and source info |

## 5. OpenClaw Mode vs Generic Mode

| | OpenClaw Native Mode | Generic Mode |
| --- | --- | --- |
| **Trigger** | `~/.openclaw` directory or `openclaw` command detected | OpenClaw not detected |
| **Skill Directory** | `~/.openclaw/skills/experience-to-skill-generator` | `~/.experience-to-skill-generator/skills/experience-to-skill-generator` |
| **Session Source** | Automatically reads from `~/.openclaw/agents/` | Manually place in `./sessions/` or specify with `--input` |
| **Agent Auto-loading** | ✅ Registered via `openclaw skills install` during installation (requires the OpenClaw runtime to be installed and started) | ❌ Manual integration required |

### How to Use Generated Skills with Non-OpenClaw Agents?

1. **One-command setup (recommended)**: Run `setup-agent` to auto-generate the agent's config file, teaching it the full extract → LLM analysis → generate workflow

```bash
experience-to-skill-generator setup-agent claude-code   # Generates CLAUDE.md
experience-to-skill-generator setup-agent cursor         # Generates .cursorrules
experience-to-skill-generator setup-agent windsurf       # Generates .windsurfrules
```

2. **Paste at conversation start**: Paste `SKILL.md` content before your question when starting a new chat
3. **Project-level config files**: Write key points into `CLAUDE.md` (Claude Code) or `.cursorrules` (Cursor) — these agents auto-load these files
4. **System prompt**: Add `SKILL.md` content to your agent's custom system prompt

> 💡 **In a nutshell**: OpenClaw uses "auto-injection", other agents use `setup-agent` for "semi-auto injection" (one-time setup, permanent effect) — the end result is similar, just the delivery method differs.

## 6. CLI Reference

| Command | Description | Example |
| --- | --- | --- |
| `extract` | Preprocess session, output structured text for LLM analysis | `experience-to-skill-generator --input ./sessions/session.json extract` |
| `analyze` | Analyze using built-in rule engine (fallback) | `experience-to-skill-generator --input ./sessions/session.json analyze --json-lines` |
| `generate` | Generate SKILL.md | `experience-to-skill-generator --input ./sessions/session.json --output-dir ./generated_skills generate --name my-skill` |
| `diagnose` | Diagnose runtime environment | `experience-to-skill-generator --input ./sessions diagnose` |
| `config` | Print merged configuration | `experience-to-skill-generator config` |
| `validate-config` | Validate configuration | `experience-to-skill-generator validate-config` |
| `setup-agent` | Generate project-level workflow guide for a specific agent | `experience-to-skill-generator setup-agent claude-code` |

| Flag | Description |
| --- | --- |
| `--input` | Session file or directory path (required) |
| `--output-dir` | Output directory for generated skills |
| `--conflict` | Conflict strategy: `rename` / `skip` / `overwrite` / `merge` / `fail` |
| `--preserve-raw` | Preserve raw content (⚠️ may expose sensitive data) |
| `--config` | JSON configuration file path |
| `--analysis` | (generate subcommand) External LLM analysis result JSON |
| `--analysis-stdin` | (generate subcommand) Read external analysis JSON from stdin |

### Environment Variables

| Variable | Description |
| --- | --- |
| `ESG_LANG` | CLI help text language: `zh` (Chinese) or `en` (English). Automatically baked into the command wrapper during installation |
| `ESG_NON_INTERACTIVE` | Set to `1` to skip all interactive prompts |
| `ESG_SKILL_DIR` | Custom skill installation directory |
| `ESG_CONFIG_DIR` | Custom configuration directory |
| `ESG_OUTPUT_DIR` | Custom output directory |
| `ESG_SESSION_DIR` | Custom session directory |

### Exit Codes

| Exit Code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | Configuration or runtime error |
| `130` | User interrupt (Ctrl+C) |

> 📋 For full configuration reference (environment variables, JSON config options, adapters, etc.), see [doc/CONFIGURATION.md](doc/CONFIGURATION.md).

## 7. Configuration

Configuration precedence (low to high): built-in defaults → `--config` file → `ESG_*` environment variables → CLI flags.

> 💡 `ESG_LANG` is written into the command wrapper at install time, effectively making it a permanent setting. To override, simply set it before running a command.

> 📋 For full configuration reference, see [doc/CONFIGURATION.md](doc/CONFIGURATION.md).

## 8. Security & Redaction

- **Redaction enabled by default**: tokens, secrets, emails, and private paths are automatically cleaned from results
- **Atomic writes**: writes to a temporary file first, then replaces the target
- **Conflict control**: same-name or similar skills are handled by the `--conflict` strategy

To preserve raw content:

```bash
experience-to-skill-generator --preserve-raw --input ./sessions analyze
```

> ⚠️ Make sure session content does not expose sensitive information before enabling this option.

## 9. Advanced: CI/CD Automation

> 💡 **When to use**: Teams managing sanitized session files in a **private repository** who want skill documents generated automatically on each push. For individual users, running the command locally is sufficient — no CI/CD needed.

<details>
<summary>👉 Expand to see GitHub Actions example</summary>

```yaml
# .github/workflows/skill-generator.yml
name: Auto Generate Skills
on:
  push:
    paths: ['sessions/**']    # Trigger only when conversation files change

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

**Important notes:**

- `--conflict rename` prevents overwriting existing skill files; each run writes to a new directory
- `paths: sessions/**` avoids triggering the workflow on unrelated commits
- Each run reads **all** files under sessions/ and performs a fresh analysis — it is not incremental
- Session files often contain private information; make sure they are sanitized before committing

</details>

## 10. Troubleshooting

### ❓ `command not found: experience-to-skill-generator`

The executable is not in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"   # Add to ~/.bashrc or ~/.zshrc
```

### ❓ `Session file not found`

Verify the `--input` path and file format (`.json` / `.jsonl` / `.md` / `.txt`):

```bash
ls ./sessions/session.json
python3 -c "import json; json.load(open('./sessions/session.json')); print('OK')"
```

### ❓ Generated SKILL.md is low quality

Recommend using the full `extract` + agent LLM analysis + `generate --analysis` workflow instead of relying solely on the built-in rule engine. If using the built-in rule engine, make sure the session includes multiple rounds of user/assistant dialogue with clear problem descriptions and solution steps.

### ❓ How to undo an installation

```bash
rm -rf ~/.local/bin/experience-to-skill-generator
rm -rf ~/.experience-to-skill-generator                              # Generic mode (skill files live under skills/experience-to-skill-generator/)
rm -rf ~/.openclaw/skills/experience-to-skill-generator              # OpenClaw mode
rm -rf ~/.openclaw/config/skills/experience-to-skill-generator      # OpenClaw mode (config dir)
```

## 11. Verification

```bash
python3 -m unittest python-scripts/test_universal_skill_generator.py
python3 python-scripts/e2e_validate_universal_skill_generator.py
```

## 12. License

Apache License 2.0. See [LICENSE](LICENSE).