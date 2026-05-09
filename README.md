# Experience-to-Skill Generator

> [中文](README_CN.md)

Turn your AI conversation logs into reusable skill documents — with a single command.

## 1. What is this?

Experience-to-Skill Generator is a CLI tool that **automatically analyzes your AI conversation history**, extracts valuable workflows, technical solutions, and best practices, then generates a structured `SKILL.md` skill document.

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

# ② Analyze session
python3 python-scripts/universal_skill_generator.py --input ./sessions/session.json analyze

# ③ Generate skill document
python3 python-scripts/universal_skill_generator.py \
  --input ./sessions/session.json \
  --output-dir ./generated_skills \
  generate --name my-first-skill
```

### Option B: Install as a local command (recommended for daily use)

```bash
# One-step install (ESG_NON_INTERACTIVE=1 skips interactive confirmation)
ESG_NON_INTERACTIVE=1 ./skills/experience-to-skill-generator/install.sh

# After installation, use the short command directly
experience-to-skill-generator --input ./sessions/session.json analyze
experience-to-skill-generator --input ./sessions/session.json --output-dir ./generated_skills generate --name my-skill
```

> 💡 The install script auto-detects your environment: if OpenClaw is detected, it installs as a native skill; otherwise it uses generic mode. No manual selection needed.

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

1. **Paste at conversation start**: Paste `SKILL.md` content before your question when starting a new chat
2. **Project-level config files**: Write key points into `CLAUDE.md` (Claude Code) or `.cursorrules` (Cursor) — these agents auto-load these files
3. **System prompt**: Add `SKILL.md` content to your agent's custom system prompt

> 💡 **In a nutshell**: OpenClaw uses "auto-injection", other agents use "manual feeding" — the end result is similar, just the delivery method differs.

## 6. CLI Reference

| Command | Description | Example |
| --- | --- | --- |
| `diagnose` | Diagnose runtime environment | `experience-to-skill-generator --input ./sessions diagnose` |
| `analyze` | Analyze session and output JSON | `experience-to-skill-generator --input ./sessions/session.json analyze --json-lines` |
| `generate` | Generate SKILL.md | `experience-to-skill-generator --input ./sessions/session.json --output-dir ./generated_skills generate --name my-skill` |
| `config` | Print merged configuration | `experience-to-skill-generator config` |
| `validate-config` | Validate configuration | `experience-to-skill-generator validate-config` |

| Flag | Description |
| --- | --- |
| `--input` | Session file or directory path (required) |
| `--output-dir` | Output directory for generated skills |
| `--conflict` | Conflict strategy: `rename` / `skip` / `overwrite` / `merge` / `fail` |
| `--preserve-raw` | Preserve raw content (⚠️ may expose sensitive data) |
| `--config` | JSON configuration file path |

### Exit Codes

| Exit Code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | Configuration or runtime error |
| `130` | User interrupt (Ctrl+C) |

> 📋 For full configuration reference (environment variables, JSON config options, adapters, etc.), see [doc/CONFIGURATION.md](doc/CONFIGURATION.md).

## 7. Configuration

Configuration precedence (low to high): built-in defaults → `--config` file → `ESG_*` environment variables → CLI flags.

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

## 9. Automation Example

Add skill generation to CI/CD so that new conversation files automatically generate skill documents:

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

Key points: `--conflict rename` ensures incremental safety; `paths: sessions/**` avoids unnecessary triggers.

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

Session content is too short or lacks enough interaction turns. Make sure it includes multiple rounds of user/assistant dialogue with clear problem descriptions and solution steps.

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