# Technical Design

> [中文](TECHNICAL_DESIGN_CN.md)

### 1. Architecture goals

`Experience-to-Skill Generator` upgrades a focused OpenClaw session analyzer into a universal agent SKILL generator. The core principles are:

- **Generic by default**: no hard dependency on one agent layout or command.
- **Configurable**: defaults, config files, environment variables, and CLI flags can override behavior.
- **Safe defaults**: redaction is enabled, raw preservation is disabled, and writes avoid damaging existing files.
- **Script-friendly**: core commands provide JSON output and non-zero exit codes for errors.
- **Extensible**: adapters and templates support new agents and output styles.

### 2. Data flow

The tool uses a "data pipeline" architecture where semantic analysis is delegated to the agent's own LLM:

```mermaid
flowchart TD
    subgraph "Tool (deterministic operations)"
        A["CLI / Installer"] --> B["Build Runtime Context"]
        B --> C["Load and Validate Config"]
        C --> D["Detect Agent Adapter"]
        D --> E["Load Session Files"]
        E --> F["Normalize and Redact Messages"]
        F --> G["Chunk and Output Structured Text (extract)"]
        I["Receive Analysis JSON"] --> J["Render SKILL Template"]
        J --> K["Detect Existing or Similar Skill"]
        K --> L["Apply Conflict Strategy"]
        L --> M["Atomic Write SKILL.md"]
    end

    subgraph "Agent LLM (semantic understanding)"
        G -->|"stdout"| H["Agent LLM reads session text"]
        H --> H2["Understand intent / Extract tasks / Identify steps"]
        H2 --> H3["Output structured analysis JSON"]
        H3 -->|"--analysis flag"| I
        M -->|"stdout"| N["Agent LLM self-checks quality"]
        N --> O{"Satisfied?"}
        O -->|"No"| H
        O -->|"Yes"| P["Done"]
    end
```

### 2.1 Fallback data flow (no LLM dependency)

When the tool is used standalone or the agent doesn't support multi-step calls, the built-in rule engine can be used directly:

```mermaid
flowchart TD
    A[CLI] --> B[Build Runtime Context]
    B --> C[Load and Validate Config]
    C --> D[Detect Agent Adapter]
    D --> E[Load Session Files]
    E --> F[Normalize and Redact Messages]
    F --> G[Chunk and Summarize]
    G --> H[Extract Tasks Steps Constraints]
    H --> I[Render SKILL Template]
    I --> J[Detect Existing or Similar Skill]
    J --> K[Apply Conflict Strategy]
    K --> L[Atomic Write SKILL.md]
```

### 3. Agent adapter strategy

Built-in adapters (must match `KNOWN_AGENT_ADAPTERS` in [universal_skill_generator.py](../python-scripts/universal_skill_generator.py)):

| Adapter | `markers` | `skill_dir` | `config_dir` | `session_dir` | `metadata_format` |
| --- | --- | --- | --- | --- | --- |
| `openclaw` | `[".openclaw"]` | `~/.openclaw/skills` | `~/.openclaw/config/skills/experience-to-skill-generator` | `~/.openclaw/agents` | `openclaw` |
| `generic` | `[]` | `./generated_skills` | `./.experience-to-skill-generator` | `./sessions` | `generic` |

The `auto` strategy detects OpenClaw markers or the `openclaw` command first; otherwise it falls back to `generic`. No manual selection needed.

Custom adapters can be added via the `adapters` config:

```json
{
  "adapters": {
    "custom-agent": {
      "skill_dir": "~/.custom-agent/skills",
      "config_dir": "~/.custom-agent/config/experience-to-skill-generator",
      "session_dir": "~/.custom-agent/sessions",
      "metadata_format": "generic"
    }
  }
}
```

### 4. Session analysis strategy

#### 4.1 Recommended mode: Agent LLM-driven

The tool uses a "data pipeline" architecture where semantic analysis is delegated to the agent's own LLM:

| Capability | Responsible | Reason |
| --- | --- | --- |
| Session file reading, parsing, normalization | **Tool** | I/O operations, not the agent's strength |
| Semantic analysis (understanding intent, extracting tasks) | **Agent's LLM** | The agent already has this capability |
| Structured output (generating SKILL.md) | **Tool** | Template rendering and file writing are deterministic |
| Self-check loop (ReAct) | **Agent itself** | Agents are naturally ReAct architectures |

Workflow:

1. Agent calls `extract` to get preprocessed session text
2. Agent's LLM analyzes the content based on the returned `prompt_hint`
3. Agent passes the analysis result (JSON) to `generate --analysis`
4. Agent checks the generated SKILL.md quality; if unsatisfied, adjusts and regenerates

Advantages of this design:
- **Zero configuration**: No need to configure LLM API keys in the tool; reuses the agent's LLM
- **No extra dependencies**: Tool remains pure standard library implementation
- **Single token consumption**: Avoids double consumption from tool calling LLM + agent calling LLM
- **Natural self-check loop**: Agents are inherently ReAct architectures

#### 4.2 Fallback mode: Built-in rule engine

When the tool is used standalone or the agent doesn't support multi-step calls, `generate` without `--analysis` uses the built-in rule engine:

- Extracts task sentences from user messages using markers like "please, need, help me, implement, fix, analyze, generate".
- Extracts numbered lists, bullet points, and step-like sentences from assistant messages.
- Extracts constraint sentences using markers like "must, must not, caution, only, avoid".
- Extracts keywords using English and Chinese morphological rules.
- Computes confidence based on message count, tasks, steps, and role coverage.

When `confidence` falls below `analysis.confidence_threshold`, the generated document flags the need for human review.

### 5. Templates and metadata

Supported templates:

| Template | Description |
| --- | --- |
| `standard` | Default template with full sections |
| `compact` | Concise template for quick internal capture |
| `checklist` | Checklist template for execution-oriented flows |

Supported metadata formats:

| Format | Behavior |
| --- | --- |
| `generic` | Stores JSON metadata in HTML comments |
| `openclaw` | Stores metadata in YAML-like front matter |
| `json` | Outputs a JSON metadata block |

### 6. Writing and conflict handling

Write flow:

1. Resolve target directory.
2. Check for same-name `SKILL.md`.
3. Check for similar skill directory names (default similarity threshold `0.8`).
4. Apply conflict strategy.
5. Write to a temporary file.
6. Atomically replace the final `SKILL.md`.

Conflict strategies:

- `rename`: writes to a new directory.
- `skip`: returns the existing path without writing.
- `overwrite`: creates `.bak` backup first.
- `merge`: appends new analysis results.
- `fail`: raises a user-readable error and returns a non-zero exit code.

### 7. Installer design

`skills/experience-to-skill-generator/install.sh` is responsible for:

- Checking Python 3.8+.
- Checking optional dependencies `numpy` and `sklearn`.
- Auto-detecting OpenClaw or falling back to generic install.
- Copying the skill package and config files.
- Creating an `experience-to-skill-generator` command entry in `ESG_BIN_DIR`.
- Optionally running `openclaw skills install/update`.
- Creating sample session data.
- Cleaning up temporary files on install failure.

#### 7.1 Command entry script internals

The installer generates a **thin Shell wrapper script** (not a compiled binary) as the CLI command entry point using Here Document syntax:

```bash
cat > "$cli_path" <<EOF
#!/usr/bin/env bash
export ESG_LANG="${CLI_LANG}"
exec "$PYTHON_BIN" "$PROJECT_DIR/python-scripts/universal_skill_generator.py" "\$@"
EOF
chmod +x "$cli_path"
```

Key elements:

| Element | Explanation |
| --- | --- |
| `cat > ... <<EOF` | Shell Here Document syntax — writes multi-line text into the target file |
| `#!/usr/bin/env bash` | Shebang line declaring the script should be executed with bash |
| `export ESG_LANG="..."` | Bakes the language choice (selected during install) into the wrapper, so CLI help text displays in the correct language without manual env setup |
| `exec` | **Replaces** the current shell process with the Python process, avoiding an extra parent process |
| `"$PYTHON_BIN"` / `"$PROJECT_DIR/..."` | Expanded to absolute paths at install time and hard-coded into the script |
| `"\$@"` | The `$` is escaped during generation; at runtime it becomes `"$@"`, forwarding all user arguments |
| `chmod +x` | Grants execute permission |

Example of the generated file:

```bash
#!/usr/bin/env bash
exec "/usr/bin/python3" "/home/user/experience-to-skill-generator/python-scripts/universal_skill_generator.py" "$@"
```

Characteristics of this approach:

- **Not** a compiled/packaged binary (unlike PyInstaller or similar tools) — no build step required.
- **Is** a thin shell script acting as a "shortcut" — changes to the `.py` source take effect immediately.
- Depends on a Python interpreter already installed on the system.

### 8. Validation strategy

- **Unit tests**: `python3 -m unittest python-scripts/test_universal_skill_generator.py`
- **End-to-end validation**: `python3 python-scripts/e2e_validate_universal_skill_generator.py`
- **Compile check**: `python3 -m py_compile python-scripts/universal_skill_generator.py`

E2E validation covers:

- `generic` agent flow.
- `openclaw` agent flow.
- `extract`, `analyze`, `generate`, `diagnose` commands.
- `setup-agent` command (covering `claude-code`, `cursor`, `windsurf` agent types).
- Required sections and metadata in generated documents.

### 9. Module layout

`python-scripts/` contains exactly three files:

| File | Role |
| --- | --- |
| `universal_skill_generator.py` | Main CLI entry; implements all 7 subcommands (`extract` / `analyze` / `generate` / `diagnose` / `config` / `validate-config` / `setup-agent`), config merging, adapter detection, session preprocessing, rule-based analysis, external analysis reception, template rendering, atomic writes, and agent workflow guide generation |
| `test_universal_skill_generator.py` | Unit tests for the main CLI |
| `e2e_validate_universal_skill_generator.py` | End-to-end validation covering both `generic` and `openclaw` adapter flows |

### 10. Known Limitations

The built-in rule engine serves as a fallback and has known flaws including narrow coverage, no semantic understanding, and no self-verification mechanism. The recommended approach is to use the full `extract` + agent LLM analysis + `generate --analysis` workflow. See [Early Version Limitations Analysis](LIMITATIONS.md) for details.