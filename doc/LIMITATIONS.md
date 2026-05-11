# Early Version Limitations Analysis

> [中文](LIMITATIONS_CN.md)

This document records the design flaws and limitations of the early version (v0.1.x, pure rule engine) of `Experience-to-Skill Generator`, serving as a cautionary reference for future iterations.

> ✅ **The current version (v0.2.0) has resolved most of the issues described below**: through the full `extract` + agent LLM analysis + `generate --analysis` workflow, semantic analysis is delegated to the agent's LLM, and the tool only acts as a data pipeline. The built-in rule engine is retained as a fallback.

---

## 1. Core Issue: No AI Reasoning Capability

The early version's entire analysis pipeline in `universal_skill_generator.py` was **100% hard-coded rules** with zero LLM / AI model integration.

**Evidence:**

- All imports are Python standard library only (`re`, `json`, `os`, `pathlib`, etc.) — no `requests`, `openai`, `anthropic`, or any external dependencies.
- No HTTP requests, API calls, or model inference code anywhere.
- All "analysis" is essentially regex matching + string manipulation.

---

## 2. Limitations of Each Core Function

### 2.1 Task Extraction — `extract_tasks`

```python
# Actual logic: match sentences containing specific Chinese keywords
if any(marker in line for marker in ["请", "需要", "帮我", "实现", "修复", "分析", "生成", "如何", "怎么"]):
    tasks.append(line[:160])
```

| Problem | Description |
| --- | --- |
| Extremely narrow keyword coverage | Only 7–8 Chinese keywords; English conversations are almost entirely missed |
| No semantic understanding | "请问今天天气如何" (asking about weather) would be extracted as a task |
| Fails on non-imperative dialogue | Implicit tasks in exploratory or discussion-style conversations are completely undetectable |

### 2.2 Step Extraction — `extract_steps`

```python
# Actual logic: regex for numbered lists + specific Chinese prefix words
pattern = re.compile(r"(?:^|\n)\s*(?:\d+[.、)]|-|\*)\s*([^\n]{8,180})")
# + matches sentences starting with "首先/然后/接着/最后/验证/检查/运行"
```

| Problem | Description |
| --- | --- |
| Only captures formatted steps | Must be `1. xxx` numbered lists or specific prefix words |
| Natural language steps are lost | Colloquial descriptions like "change the config first, then restart" cannot be extracted |
| No understanding of logical relationships | Extracted sentences are isolated; dependencies between steps are unknown |

### 2.3 Keyword Extraction — `extract_keywords`

```python
# Actual logic: regex extraction + frequency counting
candidates = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}|[\u4e00-\u9fff]{2,}", text)
```

| Problem | Description |
| --- | --- |
| Pure frequency counting, no semantic weighting | High-frequency but meaningless words may rank above core concepts |
| Extremely small stopword list | Only ~15 stopwords; filtering is minimal |
| Cannot identify technical terms or phrases | "machine learning" would be split into two independent words |

### 2.4 Constraint Extraction — `extract_constraints`

```python
# Actual logic: match sentences containing specific Chinese keywords
if any(marker in clean for marker in ["不要", "必须", "禁止", "注意", "约束", "只能", "避免", "请勿"]):
```

| Problem | Description |
| --- | --- |
| Only 8 Chinese keywords | English constraints ("must not", "do not", "avoid") are completely missed |
| Cannot detect implicit constraints | "This API has a concurrency limit" contains no keywords but is clearly a constraint |
| False positives | "注意这个功能很好用" (note this feature works well) would be extracted as a constraint |

### 2.5 Confidence Calculation — `calculate_confidence`

```python
# Actual logic: simple additive scoring
score = 0.2
if len(messages) >= 4:  score += 0.2
if tasks:               score += 0.2
if len(steps) >= 3:     score += 0.2
if any(role == "assistant"): score += 0.1
if any(role == "user"):      score += 0.1
```

| Problem | Description |
| --- | --- |
| Completely unrelated to content quality | Only checks "does it exist", not "is it good" |
| Easily inflated | 4 meaningless messages + 3 false-positive steps = 0.8 high confidence |
| Does not reflect actual skill usability | High confidence ≠ the generated skill is actually useful |

---

## 3. Architectural Flaws

### 3.1 One-Shot Generation with No Self-Verification

```
Input session → Regex extraction → Template filling → Output SKILL.md (done)
```

- No "post-generation check" step exists.
- Never verifies whether the generated skill accurately covers the session's key points.
- Never validates whether extraction results are reasonable (e.g., whether tasks and steps are coherent).

### 3.2 Full Analysis but Non-Incremental Generation

- Every run re-analyzes all session files from scratch.
- Generated skills are completely independent from previous runs — no incremental update capability.
- Conflict strategies (e.g., `rename`) only prevent file overwrites; they do not implement content-level incremental merging.

### 3.3 Severe Language Bias

- All extraction rules are primarily based on Chinese keywords.
- Extraction quality for English conversations is extremely poor — nearly random.
- No multi-language adaptation mechanism exists.

---

## 4. Fundamental Positioning Gap

| Expected Positioning | Actual Positioning |
| --- | --- |
| Intelligent analyzer: understands arbitrary conversation semantics, accurately distills reusable experience | Template filler: uses regex to extract key sentences and stuffs them into fixed templates |
| Works with any input | Only works with Chinese, well-formatted conversations containing explicit imperative keywords and numbered steps |
| Generates high-quality, directly reusable skills | Generates skill drafts requiring extensive manual review and modification |

---

## 5. Improvement Directions

> ✅ The following improvement directions have been implemented in v0.2.0. The current version supports the full `extract` + agent LLM analysis + `generate --analysis` workflow, with the built-in rule engine retained as a fallback.

### 5.1 Integrate LLM for Semantic Analysis ✅ Implemented

Replace hard-coded regex with AI models for true semantic understanding:

```
Conversation text → LLM analysis (understand intent / extract tasks / identify steps / discover constraints) → Structured output
```

### 5.2 Introduce ReAct Self-Verification Loop ✅ Implemented

Let AI self-check after generation, iterating until satisfied:

```
Generate SKILL draft → AI self-check (accurately covers key points?) → Unsatisfied → Adjust and regenerate → Satisfied → Output
```

### 5.3 Incremental Analysis Capability ⚠️ Pending

- Track hashes of previously analyzed session files.
- Only perform incremental analysis on new/changed sessions.
- Support intelligent merging of new analysis results into existing skills.

### 5.4 Multi-Language Support ✅ Implemented

- Extraction rules should not hard-code language-specific keywords. → Solved via LLM analysis mode; LLM automatically adapts to input language.
- Let LLM automatically adapt to input language. → Implemented.
- Make output language configurable. → Implemented via `ESG_LANG` environment variable supporting Chinese/English switching.

---

## 6. Summary

The core lesson from the early version:

> **Do not use hard-coded rules for tasks that require semantic understanding.** Regular expressions can handle "format" but not "meaning". When the input is natural language, hard-coded rules will always have limited coverage, and maintenance cost grows exponentially with the number of rules.

This version served as an MVP to validate the "conversation → skill" pathway. The current version (v0.2.0) has introduced agent LLM semantic analysis + ReAct self-check loop, with the built-in rule engine retained as a fallback.
