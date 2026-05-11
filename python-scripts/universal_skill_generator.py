#!/usr/bin/env python3
"""通用会话经验到 SKILL 生成工具。"""

from __future__ import annotations

import argparse
import copy
import fnmatch
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

DEFAULT_CONFIG: Dict[str, Any] = {
    "agent": "auto",
    "compatibility_mode": True,
    "session_sources": [
        {"type": "openclaw", "path": "~/.openclaw/workspace/memory", "patterns": ["*.json", "*.jsonl", "*.md", "*.txt"]},
        {"type": "openclaw", "path": "~/.openclaw/agents", "patterns": ["*.jsonl", "*.json"]},
    ],
    "output": {
        "target_dir": "generated_skills",
        "format": "markdown",
        "conflict_strategy": "rename",
        "metadata_format": "generic",
    },
    "analysis": {
        "min_score": 50,
        "max_chars": 120000,
        "chunk_chars": 30000,
        "confidence_threshold": 0.55,
    },
    "security": {
        "redact_sensitive": True,
        "preserve_raw": False,
    },
    "templates": {
        "skill": "standard",
        "include_sources": True,
    },
    "adapters": {},
}

KNOWN_AGENT_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "openclaw": {
        "markers": [".openclaw"],
        "skill_dir": "~/.openclaw/skills",
        "config_dir": "~/.openclaw/config/skills/experience-to-skill-generator",
        "session_dir": "~/.openclaw/agents",
        "metadata_format": "openclaw",
    },
    "generic": {
        "markers": [],
        "skill_dir": "./generated_skills",
        "config_dir": "./.experience-to-skill-generator",
        "session_dir": "./sessions",
        "metadata_format": "generic",
    },
}

SENSITIVE_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|access[_-]?token)\s*[:=]\s*['\"]?[^'\"\s,}]+"), r"\1=<REDACTED>"),
    (re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"), "Bearer <REDACTED>"),
    (re.compile(r"sk-[A-Za-z0-9]{16,}"), "sk-<REDACTED>"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS_KEY_<REDACTED>"),
    (re.compile(r"(?i)ghp_[A-Za-z0-9_]{20,}"), "ghp_<REDACTED>"),
    (re.compile(r"(?i)xox[baprs]-[A-Za-z0-9\-]{10,}"), "xox-<REDACTED>"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "<PRIVATE_KEY_REDACTED>"),
    (re.compile(r"(?i)(ssh-rsa|ssh-ed25519)\s+[A-Za-z0-9+/=]{40,}"), "<SSH_KEY_REDACTED>"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "<EMAIL_REDACTED>"),
    (re.compile(r"/Users/[^/\s]+"), "/Users/<USER>"),
    (re.compile(r"/home/[^/\s]+"), "/home/<USER>"),
    (re.compile(r"/root/[^\s]*"), "/root/<REDACTED_PATH>"),
    (re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+"), r"C:\\Users\\<USER>"),
]

ALLOWED_METADATA_FORMATS = {"generic", "openclaw", "json"}
ALLOWED_TEMPLATE_NAMES = {"standard", "compact", "checklist"}
ALLOWED_SOURCE_TYPES = {"openclaw", "generic", "custom", "cli"}


class UserFacingError(Exception):
    """可直接展示给用户的错误。"""


@dataclass
class RuntimeContext:
    config: Dict[str, Any]
    adapter: Dict[str, Any]
    adapter_name: str
    config_path: Optional[Path]
    adapter_strategy: str


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def expand_path(value: str, base_dir: Optional[Path] = None) -> Path:
    expanded = Path(os.path.expandvars(os.path.expanduser(value)))
    if not expanded.is_absolute() and base_dir:
        return (base_dir / expanded).resolve()
    return expanded.resolve()


def load_json_file(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise UserFacingError(f"配置文件不存在: {path}")
    except json.JSONDecodeError as exc:
        raise UserFacingError(f"配置文件 JSON 格式无效: {path} ({exc})")
    if not isinstance(data, dict):
        raise UserFacingError("配置文件根节点必须是对象")
    return data


def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    env_map = {
        "ESG_OUTPUT_DIR": ("output", "target_dir"),
        "ESG_SESSION_DIR": ("session_sources",),
        "ESG_CONFLICT_STRATEGY": ("output", "conflict_strategy"),
        "ESG_MIN_SCORE": ("analysis", "min_score"),
        "ESG_PRESERVE_RAW": ("security", "preserve_raw"),
    }
    result = copy.deepcopy(config)
    for env_name, path in env_map.items():
        raw_value = os.environ.get(env_name)
        if raw_value is None or raw_value == "":
            continue
        if path == ("session_sources",):
            result["session_sources"] = [{"type": "custom", "path": raw_value, "patterns": ["*.json", "*.jsonl", "*.md", "*.txt"]}]
            continue
        value: Any = raw_value
        if env_name == "ESG_MIN_SCORE":
            try:
                value = int(raw_value)
            except ValueError as exc:
                raise UserFacingError("环境变量 ESG_MIN_SCORE 必须是整数") from exc
        elif env_name == "ESG_PRESERVE_RAW":
            value = parse_bool(raw_value, "ESG_PRESERVE_RAW")
        cursor = result
        for part in path[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[path[-1]] = value
    return result


def parse_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise UserFacingError(f"配置项 {name} 必须是布尔值")


def ensure_number(value: Any, name: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise UserFacingError(f"配置项 {name} 必须是数字")
    if value < minimum or value > maximum:
        raise UserFacingError(f"配置项 {name} 必须位于 {minimum} 到 {maximum} 之间")
    return float(value)


def ensure_positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise UserFacingError(f"配置项 {name} 必须是正整数")
    return value


def validate_adapters(config: Dict[str, Any]) -> None:
    adapters = config.get("adapters", {})
    if adapters is None:
        config["adapters"] = {}
        return
    if not isinstance(adapters, dict):
        raise UserFacingError("配置项 adapters 必须是对象")
    for name, adapter in adapters.items():
        if name in {"auto", ""} or not isinstance(name, str):
            raise UserFacingError("配置项 adapters 的键必须是有效 agent 名称")
        if not isinstance(adapter, dict):
            raise UserFacingError(f"配置项 adapters.{name} 必须是对象")
        for key in ["skill_dir", "config_dir", "session_dir"]:
            if key in adapter and not isinstance(adapter[key], str):
                raise UserFacingError(f"配置项 adapters.{name}.{key} 必须是字符串")
        if "metadata_format" in adapter and adapter["metadata_format"] not in ALLOWED_METADATA_FORMATS:
            raise UserFacingError(f"配置项 adapters.{name}.metadata_format 无效")


def register_configured_adapters(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    adapters = copy.deepcopy(KNOWN_AGENT_ADAPTERS)
    for name, adapter in config.get("adapters", {}).items():
        base = adapters.get(name, {})
        adapters[name] = deep_merge(base, adapter)
    return adapters


def validate_config(config: Dict[str, Any]) -> None:
    agent = config.get("agent", "auto")
    if not isinstance(agent, str) or not agent:
        raise UserFacingError("配置项 agent 必须是字符串")

    compatibility_mode = config.get("compatibility_mode", True)
    config["compatibility_mode"] = parse_bool(compatibility_mode, "compatibility_mode")

    if not isinstance(config.get("session_sources"), list):
        raise UserFacingError("配置项 session_sources 必须是数组")
    if not config["session_sources"]:
        raise UserFacingError("配置项 session_sources 不能为空")
    for index, source in enumerate(config["session_sources"]):
        if not isinstance(source, dict) or not source.get("path"):
            raise UserFacingError(f"配置项 session_sources[{index}] 必须包含 path")
        if not isinstance(source["path"], str):
            raise UserFacingError(f"配置项 session_sources[{index}].path 必须是字符串")
        source_type = source.get("type", "custom")
        if source_type not in ALLOWED_SOURCE_TYPES:
            raise UserFacingError(f"配置项 session_sources[{index}].type 无效")
        patterns = source.get("patterns", ["*"])
        if not isinstance(patterns, list) or not patterns or not all(isinstance(item, str) and item for item in patterns):
            raise UserFacingError(f"配置项 session_sources[{index}].patterns 必须是非空字符串数组")

    output = config.setdefault("output", {})
    if not isinstance(output, dict):
        raise UserFacingError("配置项 output 必须是对象")
    if output.get("conflict_strategy") not in {"rename", "skip", "overwrite", "merge", "fail"}:
        raise UserFacingError("配置项 output.conflict_strategy 只能是 rename、skip、overwrite、merge 或 fail")
    if output.get("metadata_format") not in ALLOWED_METADATA_FORMATS:
        raise UserFacingError("配置项 output.metadata_format 只能是 generic、openclaw 或 json")
    if "target_dir" in output and output["target_dir"] is not None and not isinstance(output["target_dir"], str):
        raise UserFacingError("配置项 output.target_dir 必须是字符串")

    analysis = config.setdefault("analysis", {})
    if not isinstance(analysis, dict):
        raise UserFacingError("配置项 analysis 必须是对象")
    ensure_number(analysis.get("min_score", 0), "analysis.min_score", 0, 100)
    ensure_positive_int(analysis.get("max_chars", 120000), "analysis.max_chars")
    ensure_positive_int(analysis.get("chunk_chars", 30000), "analysis.chunk_chars")
    ensure_number(analysis.get("confidence_threshold", 0.55), "analysis.confidence_threshold", 0, 1)
    if analysis.get("chunk_chars", 30000) > analysis.get("max_chars", 120000):
        raise UserFacingError("配置项 analysis.chunk_chars 不能大于 analysis.max_chars")

    security = config.setdefault("security", {})
    if not isinstance(security, dict):
        raise UserFacingError("配置项 security 必须是对象")
    security["redact_sensitive"] = parse_bool(security.get("redact_sensitive", True), "security.redact_sensitive")
    security["preserve_raw"] = parse_bool(security.get("preserve_raw", False), "security.preserve_raw")

    templates = config.setdefault("templates", {})
    if not isinstance(templates, dict):
        raise UserFacingError("配置项 templates 必须是对象")
    if templates.get("skill", "standard") not in ALLOWED_TEMPLATE_NAMES:
        raise UserFacingError("配置项 templates.skill 只能是 standard、compact 或 checklist")
    templates["include_sources"] = parse_bool(templates.get("include_sources", True), "templates.include_sources")

    validate_adapters(config)

    if security.get("preserve_raw"):
        print("⚠️ 已启用保留原文模式，请确认会话内容不会泄露令牌、私有路径或账号信息。", file=sys.stderr)
    if security.get("preserve_raw") and security.get("redact_sensitive") is False:
        print("⚠️ 已启用保留原文且关闭脱敏，生成结果可能包含敏感信息。", file=sys.stderr)


def detect_agent(explicit_agent: str = "auto", adapters: Optional[Dict[str, Dict[str, Any]]] = None) -> Tuple[str, Dict[str, Any]]:
    available_adapters = adapters or KNOWN_AGENT_ADAPTERS
    if explicit_agent and explicit_agent != "auto":
        if explicit_agent not in available_adapters:
            raise UserFacingError(f"未知 agent 类型: {explicit_agent}")
        return explicit_agent, copy.deepcopy(available_adapters[explicit_agent])

    home = Path.home()
    if "openclaw" in available_adapters and ((home / ".openclaw").exists() or shutil.which("openclaw")):
        return "openclaw", copy.deepcopy(available_adapters["openclaw"])
    return "generic", copy.deepcopy(available_adapters.get("generic", KNOWN_AGENT_ADAPTERS["generic"]))


def describe_adapter_strategy(config: Dict[str, Any], adapter_name: str) -> str:
    if config.get("agent") and config.get("agent") != "auto":
        return f"explicit:{adapter_name}"
    if adapter_name == "openclaw":
        return "auto:openclaw-marker-or-command"
    return "auto:generic-fallback"


def apply_compatibility_fallback(config: Dict[str, Any], adapter: Dict[str, Any]) -> None:
    output = config.setdefault("output", {})
    if output.get("target_dir"):
        return
    if config.get("compatibility_mode", True):
        output["target_dir"] = adapter.get("skill_dir") or "generated_skills"
    else:
        output["target_dir"] = "generated_skills"


def build_context(args: argparse.Namespace) -> RuntimeContext:
    config_path = Path(args.config).expanduser().resolve() if getattr(args, "config", None) else None
    file_config = load_json_file(config_path) if config_path else {}
    config = apply_env_overrides(deep_merge(DEFAULT_CONFIG, file_config))

    if getattr(args, "input", None):
        config["session_sources"] = [{"type": "cli", "path": args.input, "patterns": ["*.json", "*.jsonl", "*.md", "*.txt"]}]
    if getattr(args, "output_dir", None):
        config.setdefault("output", {})["target_dir"] = args.output_dir
    if getattr(args, "conflict", None):
        config.setdefault("output", {})["conflict_strategy"] = args.conflict
    if getattr(args, "preserve_raw", False):
        config.setdefault("security", {})["preserve_raw"] = True

    validate_config(config)
    configured_adapters = register_configured_adapters(config)
    adapter_name, adapter = detect_agent(config.get("agent", "auto"), configured_adapters)

    if os.environ.get("ESG_SKILL_DIR"):
        adapter["skill_dir"] = os.environ["ESG_SKILL_DIR"]
    if os.environ.get("ESG_CONFIG_DIR"):
        adapter["config_dir"] = os.environ["ESG_CONFIG_DIR"]
    if os.environ.get("ESG_SESSION_DIR"):
        adapter["session_dir"] = os.environ["ESG_SESSION_DIR"]

    config.setdefault("output", {})["metadata_format"] = config.get("output", {}).get("metadata_format") or adapter.get("metadata_format", "generic")
    apply_compatibility_fallback(config, adapter)
    adapter_strategy = describe_adapter_strategy(config, adapter_name)
    return RuntimeContext(config=config, adapter=adapter, adapter_name=adapter_name, config_path=config_path, adapter_strategy=adapter_strategy)


def redact_text(text: str, enabled: bool = True) -> str:
    if not enabled:
        return text
    redacted = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_path(path: Any, enabled: bool = True) -> str:
    """脱敏用于输出、日志和生成文档的来源路径。"""
    return redact_text(str(path), enabled)


def safe_stderr(message: str, redact_enabled: bool = True) -> None:
    """输出已脱敏的错误或诊断信息，避免日志泄露敏感上下文。"""
    print(redact_text(message, redact_enabled), file=sys.stderr)


def normalize_message(role: str, content: Any, timestamp: str = "") -> Dict[str, str]:
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif item.get("type") in {"toolCall", "tool_use"}:
                    parts.append(f"[工具调用:{item.get('name') or item.get('toolName') or 'unknown'}]")
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        text = "\n".join(part for part in parts if part)
    elif isinstance(content, dict):
        text = json.dumps(content, ensure_ascii=False)
    else:
        text = str(content or "")
    return {"role": role or "unknown", "content": text.strip(), "timestamp": timestamp}


def parse_json_session(data: Any) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if isinstance(data, dict):
        if isinstance(data.get("messages"), list):
            iterable = data["messages"]
        elif isinstance(data.get("conversation"), list):
            iterable = data["conversation"]
        elif data.get("message"):
            iterable = [data]
        else:
            iterable = []
    elif isinstance(data, list):
        iterable = data
    else:
        iterable = []

    for item in iterable:
        if not isinstance(item, dict):
            continue
        if "message" in item and isinstance(item["message"], dict):
            message = item["message"]
            role = message.get("role") or item.get("role") or item.get("type")
            content = message.get("content", item.get("content", ""))
        else:
            role = item.get("role") or item.get("type")
            content = item.get("content") or item.get("text") or item.get("message")
        messages.append(normalize_message(str(role or "unknown"), content, str(item.get("timestamp", ""))))
    return [msg for msg in messages if msg["content"]]


def validate_session_messages(messages: List[Dict[str, str]], path: Path) -> None:
    """校验单个会话文件的解析结果，避免静默接受无意义内容。"""
    if not messages:
        raise UserFacingError(f"会话文件没有可分析消息: {path}")
    if not any(message.get("role") in {"user", "assistant", "text", "unknown"} for message in messages):
        raise UserFacingError(f"会话文件缺少可识别的消息角色: {path}")


def read_session_file(path: Path) -> List[Dict[str, str]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    if not raw.strip():
        return []

    if path.suffix.lower() == ".jsonl":
        messages: List[Dict[str, str]] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                messages.extend(parse_json_session(json.loads(line)))
            except json.JSONDecodeError:
                messages.append(normalize_message("unknown", line))
        validate_session_messages(messages, path)
        return messages

    if path.suffix.lower() == ".json":
        try:
            messages = parse_json_session(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise UserFacingError(f"会话 JSON 格式无效: {path} ({exc})")
        validate_session_messages(messages, path)
        return messages

    messages = [normalize_message("text", raw, "")]
    validate_session_messages(messages, path)
    return messages


def iter_session_files(source_path: Path, patterns: Iterable[str]) -> List[Path]:
    if source_path.is_file():
        return [source_path]
    if not source_path.exists():
        return []
    files: List[Path] = []
    for root, _, filenames in os.walk(source_path):
        for filename in filenames:
            if any(fnmatch.fnmatch(filename, pattern) for pattern in patterns):
                files.append(Path(root) / filename)
    return sorted(files)


def load_sessions(context: RuntimeContext) -> List[Dict[str, str]]:
    base_dir = context.config_path.parent if context.config_path else Path.cwd()
    max_chars = int(context.config.get("analysis", {}).get("max_chars", 120000))
    redact_enabled = context.config.get("security", {}).get("redact_sensitive", True)
    preserve_raw = context.config.get("security", {}).get("preserve_raw", False)

    all_messages: List[Dict[str, str]] = []
    for source in context.config.get("session_sources", []):
        source_path = expand_path(source["path"], base_dir)
        patterns = source.get("patterns", ["*"])
        for file_path in iter_session_files(source_path, patterns):
            try:
                for message in read_session_file(file_path):
                    content = message["content"] if preserve_raw else redact_text(message["content"], redact_enabled)
                    safe_source = redact_path(file_path, redact_enabled)
                    all_messages.append({**message, "content": content, "source": safe_source})
            except UserFacingError:
                raise
            except Exception as exc:
                safe_stderr(f"⚠️ 跳过无法读取的会话文件 {file_path}: {exc}", redact_enabled)

    if not all_messages:
        raise UserFacingError("没有读取到可分析的会话数据，请检查 session_sources 或 --input")

    total_chars = 0
    limited_messages: List[Dict[str, str]] = []
    for message in all_messages:
        total_chars += len(message.get("content", ""))
        if total_chars <= max_chars:
            limited_messages.append(message)
        else:
            remaining = max_chars - (total_chars - len(message.get("content", "")))
            if remaining > 0:
                limited_messages.append({**message, "content": message["content"][:remaining] + "\n[内容已按 max_chars 截断]"})
            break
    return chunk_messages(limited_messages, int(context.config.get("analysis", {}).get("chunk_chars", 30000)))


def chunk_messages(messages: List[Dict[str, str]], chunk_chars: int) -> List[Dict[str, str]]:
    """为长会话增加分段标记，便于后续摘要稳定处理。"""
    if not messages:
        return []
    chunk_index = 1
    current_size = 0
    chunked: List[Dict[str, str]] = []
    for message in messages:
        content_size = len(message.get("content", ""))
        if current_size and current_size + content_size > chunk_chars:
            chunk_index += 1
            current_size = 0
        chunked.append({**message, "chunk": chunk_index})
        current_size += content_size
    return chunked


def build_chunk_summaries(messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """按分段生成轻量摘要，便于诊断长会话是否被稳定处理。"""
    summaries: List[Dict[str, Any]] = []
    by_chunk: Dict[int, List[Dict[str, str]]] = {}
    for message in messages:
        by_chunk.setdefault(int(message.get("chunk", 1)), []).append(message)
    for chunk, chunk_messages in sorted(by_chunk.items()):
        combined = "\n".join(message.get("content", "") for message in chunk_messages)
        summaries.append({
            "chunk": chunk,
            "messages": len(chunk_messages),
            "chars": len(combined),
            "keywords": extract_keywords(combined, limit=5),
        })
    return summaries


def summarize_messages(messages: List[Dict[str, str]], confidence_threshold: float = 0.55) -> Dict[str, Any]:
    user_messages = [msg["content"] for msg in messages if msg.get("role") == "user"]
    assistant_messages = [msg["content"] for msg in messages if msg.get("role") == "assistant"]
    combined = "\n".join(msg.get("content", "") for msg in messages)

    keywords = extract_keywords(combined)
    tasks = extract_tasks(user_messages or [combined])
    steps = extract_steps(assistant_messages or [combined])
    constraints = extract_constraints(combined)
    confidence = calculate_confidence(messages, tasks, steps)
    threshold = confidence_threshold

    return {
        "summary": {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "source_files": sorted({msg.get("source", "") for msg in messages if msg.get("source")}),
            "chunks": sorted({msg.get("chunk", 1) for msg in messages}),
            "chunk_summaries": build_chunk_summaries(messages),
            "analysis_time": datetime.now().isoformat(),
        },
        "tasks": tasks,
        "key_steps": steps,
        "constraints": constraints,
        "keywords": keywords,
        "confidence": confidence,
        "requires_review": confidence < threshold,
    }


def extract_keywords(text: str, limit: int = 12) -> List[str]:
    candidates = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}|[\u4e00-\u9fff]{2,}", text)
    stopwords = {"the", "and", "for", "with", "this", "that", "进行", "这个", "一个", "可以", "需要", "然后", "我们"}
    counts: Dict[str, int] = {}
    for word in candidates:
        normalized = word.lower() if re.match(r"^[A-Za-z]", word) else word
        if normalized in stopwords:
            continue
        counts[normalized] = counts.get(normalized, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def extract_tasks(messages: List[str], limit: int = 5) -> List[str]:
    tasks: List[str] = []
    for message in messages:
        for line in re.split(r"[\n。！？!?]", message):
            line = line.strip(" -#\t")
            if len(line) < 8:
                continue
            if any(marker in line for marker in ["请", "需要", "帮我", "实现", "修复", "分析", "生成", "如何", "怎么"]):
                tasks.append(line[:160])
    return dedupe(tasks)[:limit] or ["从会话中沉淀可复用的任务处理经验"]


def extract_steps(messages: List[str], limit: int = 8) -> List[str]:
    steps: List[str] = []
    pattern = re.compile(r"(?:^|\n)\s*(?:\d+[.、)]|-|\*)\s*([^\n]{8,180})")
    for message in messages:
        steps.extend(match.strip() for match in pattern.findall(message))
        for line in message.splitlines():
            clean = line.strip()
            if any(clean.startswith(prefix) for prefix in ["首先", "然后", "接着", "最后", "验证", "检查", "运行"]):
                steps.append(clean[:180])
    return dedupe(steps)[:limit] or ["识别任务目标", "收集必要上下文", "分步骤执行改动", "验证结果并总结可复用经验"]


def extract_constraints(text: str, limit: int = 6) -> List[str]:
    constraints: List[str] = []
    for line in re.split(r"[\n。！？!?]", text):
        clean = line.strip(" -#\t")
        if any(marker in clean for marker in ["不要", "必须", "禁止", "注意", "约束", "只能", "避免", "请勿"]):
            if len(clean) >= 6:
                constraints.append(clean[:180])
    return dedupe(constraints)[:limit]


def dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        normalized = re.sub(r"\s+", " ", item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def calculate_confidence(messages: List[Dict[str, str]], tasks: List[str], steps: List[str]) -> float:
    score = 0.2
    if len(messages) >= 4:
        score += 0.2
    if tasks:
        score += 0.2
    if len(steps) >= 3:
        score += 0.2
    if any(msg.get("role") == "assistant" for msg in messages):
        score += 0.1
    if any(msg.get("role") == "user" for msg in messages):
        score += 0.1
    return round(min(score, 1.0), 2)


def slugify(value: str) -> str:
    ascii_words = re.findall(r"[A-Za-z0-9]+", value.lower())
    if ascii_words:
        return "-".join(ascii_words[:8])
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    return f"generated-skill-{digest}"


def build_skill_metadata(skill_name: str, description: str, analysis: Dict[str, Any], context: RuntimeContext) -> Dict[str, Any]:
    tasks = analysis.get("tasks") or ["从会话中沉淀可复用经验"]
    steps = analysis.get("key_steps") or ["识别任务目标", "收集上下文", "执行并验证结果"]
    constraints = analysis.get("constraints") or ["复用前确认当前环境与原会话前提一致。"]
    keywords = analysis.get("keywords") or []
    return {
        "name": skill_name,
        "description": description,
        "generated_at": datetime.now().isoformat(),
        "agent": context.adapter_name,
        "confidence": analysis.get("confidence", 0),
        "requires_review": analysis.get("requires_review", True),
        "usage_scenarios": [description, "相似任务、相似约束或相似工具链下的经验复用。"],
        "trigger_conditions": tasks,
        "execution_steps": steps,
        "cautions": constraints,
        "example_usage": f"当遇到“{tasks[0][:60]}”这类任务时，按本 SKILL 的步骤执行并验证结果。",
        "keywords": keywords[:10],
    }


def render_metadata(metadata_format: str, metadata: Dict[str, Any]) -> str:
    if metadata_format == "openclaw":
        return "---\n" + "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items()) + "\n---"
    if metadata_format == "json":
        return json.dumps({"metadata": metadata}, ensure_ascii=False, indent=2)
    return "<!-- metadata: " + json.dumps(metadata, ensure_ascii=False) + " -->"


def generate_skill_document(analysis: Dict[str, Any], context: RuntimeContext, name: Optional[str] = None) -> Tuple[str, str]:
    tasks = analysis.get("tasks") or ["会话经验沉淀"]
    keywords = analysis.get("keywords") or []
    skill_name = name or slugify(" ".join(keywords[:4]) or tasks[0])
    description = f"根据会话经验总结的可复用流程：{tasks[0][:80]}"
    review_note = "\n> ⚠️ 分析置信度不足，请人工审核后再发布。\n" if analysis.get("requires_review") else ""
    metadata_format = context.config.get("output", {}).get("metadata_format", "generic")
    template_name = context.config.get("templates", {}).get("skill", "standard")
    include_sources = context.config.get("templates", {}).get("include_sources", True)
    metadata = build_skill_metadata(skill_name, description, analysis, context)
    front_matter = render_metadata(metadata_format, metadata)

    steps = metadata["execution_steps"]
    constraints = metadata["cautions"]
    sources = analysis.get("summary", {}).get("source_files", [])

    content = render_skill_template(
        template_name=template_name,
        front_matter=front_matter,
        skill_name=skill_name,
        review_note=review_note,
        description=description,
        tasks=tasks,
        steps=steps,
        constraints=constraints,
        keywords=keywords,
        sources=sources if include_sources else [],
        analysis=analysis,
    )
    return skill_name, content


def render_skill_template(
    template_name: str,
    front_matter: str,
    skill_name: str,
    review_note: str,
    description: str,
    tasks: List[str],
    steps: List[str],
    constraints: List[str],
    keywords: List[str],
    sources: List[str],
    analysis: Dict[str, Any],
) -> str:
    if template_name == "compact":
        return f"""{front_matter}

# {skill_name}
{review_note}
## 场景

{description}

## 步骤

{format_numbered(steps)}

## 注意

{format_bullets(constraints or ["复用前确认当前上下文与原会话一致。"])}

## 质量

- **置信度**：{analysis.get('confidence', 0)}
- **需要人工确认**：{'是' if analysis.get('requires_review') else '否'}
"""
    if template_name == "checklist":
        checklist = "\n".join(f"- [ ] {step}" for step in steps) if steps else "- [ ] 收集上下文\n- [ ] 执行任务\n- [ ] 验证结果"
        return f"""{front_matter}

# {skill_name}
{review_note}
## 使用清单

{checklist}

## 触发条件

{format_bullets(tasks)}

## 风险与约束

{format_bullets(constraints or ["不要直接复用会话中的私有路径、令牌或临时信息。"])}

## 质量

- **置信度**：{analysis.get('confidence', 0)}
- **关键词**：{', '.join(keywords[:10]) if keywords else '无'}
"""

    source_line = f"- **来源文件数量**：{len(sources)}" if sources else "- **来源文件数量**：已隐藏或无"
    return f"""{front_matter}

# {skill_name}
{review_note}
## 适用场景

- {description}
- 适合在相似任务、相似约束或相似工具链下复用。

## 触发条件

{format_bullets(tasks)}

## 执行步骤

{format_numbered(steps)}

## 注意事项

{format_bullets(constraints or ["执行前确认当前环境与会话中的前提条件一致。", "涉及文件、配置或命令时先做好备份或可回滚方案。"])}

## 示例用法

```text
当遇到“{tasks[0][:60]}”这类任务时，先按本 SKILL 的执行步骤收集上下文、实施改动并验证结果。
```

## 质量与来源

- **置信度**：{analysis.get('confidence', 0)}
- **是否需要人工确认**：{'是' if analysis.get('requires_review') else '否'}
- **关键词**：{', '.join(keywords[:10]) if keywords else '无'}
{source_line}

---
自动生成：Experience-to-Skill Generator
"""


def format_bullets(items: List[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 暂无"


def format_numbered(items: List[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1)) if items else "1. 暂无"


def resolve_output_dir(context: RuntimeContext) -> Path:
    base_dir = context.config_path.parent if context.config_path else Path.cwd()
    return expand_path(context.config.get("output", {}).get("target_dir", "generated_skills"), base_dir)


def resolve_output_path(context: RuntimeContext, skill_name: str) -> Path:
    return resolve_output_dir(context) / skill_name / "SKILL.md"


def normalize_skill_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def token_set(value: str) -> Set[str]:
    return {token for token in normalize_skill_name(value).split("-") if token}


def similarity_score(left: str, right: str) -> float:
    left_tokens = token_set(left)
    right_tokens = token_set(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    return overlap / max(len(left_tokens), len(right_tokens))


def find_similar_skill(target_dir: Path, skill_name: str, threshold: float = 0.8) -> Optional[Path]:
    if not target_dir.exists():
        return None
    normalized = normalize_skill_name(skill_name)
    for child in sorted(target_dir.iterdir()):
        if not child.is_dir():
            continue
        candidate = child / "SKILL.md"
        if not candidate.exists():
            continue
        candidate_name = normalize_skill_name(child.name)
        if candidate_name == normalized or similarity_score(candidate_name, normalized) >= threshold:
            return candidate
    return None


def next_available_target(target_dir: Path, skill_name: str) -> Path:
    index = 2
    while True:
        candidate = target_dir / f"{skill_name}-{index}" / "SKILL.md"
        if not candidate.exists():
            return candidate
        index += 1


def apply_conflict_strategy(target: Path, strategy: str, skill_name: str, content: str) -> Tuple[Path, str, str, str]:
    if strategy == "skip":
        return target, content, "skipped", "target_exists"
    if strategy == "fail":
        raise UserFacingError(f"目标 SKILL 已存在或存在相似技能: {target}")
    if strategy == "rename":
        return next_available_target(target.parent.parent, skill_name), content, "renamed", "target_exists_or_similar"
    if strategy == "merge":
        existing = target.read_text(encoding="utf-8")
        merged = existing.rstrip() + "\n\n---\n\n## 合并的新分析结果\n\n" + content
        return target, merged, "merged", "target_exists_or_similar"
    if strategy == "overwrite":
        backup = target.with_suffix(".md.bak")
        shutil.copy2(target, backup)
        return target, content, "overwritten", "target_exists_or_similar"
    raise UserFacingError(f"未知冲突处理策略: {strategy}")


def write_skill(context: RuntimeContext, skill_name: str, content: str) -> Dict[str, Any]:
    target_dir = resolve_output_dir(context)
    target = target_dir / skill_name / "SKILL.md"
    strategy = context.config.get("output", {}).get("conflict_strategy", "rename")
    final_target = target
    action = "created"
    reason = "new_skill"
    conflict_target: Optional[Path] = target if target.exists() else find_similar_skill(target_dir, skill_name)

    if conflict_target:
        final_target, content, action, reason = apply_conflict_strategy(conflict_target, strategy, skill_name, content)
        if action == "skipped":
            return {"path": str(conflict_target), "action": action, "reason": reason, "conflict_path": str(conflict_target)}

    final_target.parent.mkdir(parents=True, exist_ok=True)
    temp_target = final_target.with_suffix(".tmp")
    temp_target.write_text(content, encoding="utf-8")
    temp_target.replace(final_target)
    result = {"path": str(final_target), "action": action, "reason": reason}
    if conflict_target:
        result["conflict_path"] = str(conflict_target)
    return result


def command_analyze(args: argparse.Namespace) -> int:
    context = build_context(args)
    messages = load_sessions(context)
    analysis = summarize_messages(messages, float(context.config.get("analysis", {}).get("confidence_threshold", 0.55)))
    print(json.dumps(analysis, ensure_ascii=False, indent=2 if not args.json_lines else None))
    return 0


def command_generate(args: argparse.Namespace) -> int:
    context = build_context(args)
    messages = load_sessions(context)
    analysis = summarize_messages(messages, float(context.config.get("analysis", {}).get("confidence_threshold", 0.55)))
    skill_name, content = generate_skill_document(analysis, context, args.name or None)
    result = write_skill(context, skill_name, content)
    payload = {"skill_name": skill_name, "write_result": result, "confidence": analysis.get("confidence"), "requires_review": analysis.get("requires_review")}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_config(args: argparse.Namespace) -> int:
    context = build_context(args)
    payload = {"config": context.config, "adapter": context.adapter, "adapter_name": context.adapter_name, "adapter_strategy": context.adapter_strategy, "config_path": str(context.config_path) if context.config_path else None}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_diagnose(args: argparse.Namespace) -> int:
    context = build_context(args)
    diagnostics = {
        "python": sys.version.split()[0],
        "agent": context.adapter_name,
        "adapter_strategy": context.adapter_strategy,
        "openclaw_available": shutil.which("openclaw") is not None,
        "adapter": context.adapter,
        "session_sources": [],
    }
    base_dir = context.config_path.parent if context.config_path else Path.cwd()
    for source in context.config.get("session_sources", []):
        source_path = expand_path(source["path"], base_dir)
        files = iter_session_files(source_path, source.get("patterns", ["*"]))
        redact_enabled = context.config.get("security", {}).get("redact_sensitive", True)
        diagnostics["session_sources"].append({"path": redact_path(source_path, redact_enabled), "exists": source_path.exists(), "matched_files": len(files)})
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    return 0


def command_validate_config(args: argparse.Namespace) -> int:
    context = build_context(args)
    payload = {
        "valid": True,
        "agent": context.adapter_name,
        "adapter_strategy": context.adapter_strategy,
        "config_path": str(context.config_path) if context.config_path else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _get_cli_lang() -> str:
    """根据环境变量决定 CLI 帮助文本语言，支持 zh（中文）和 en（英文）。"""
    lang = os.environ.get("ESG_LANG", "").strip().lower()
    if lang in ("zh", "en"):
        return lang
    # 未显式设置时，根据系统 LANG 环境变量推断
    sys_lang = os.environ.get("LANG", "").lower()
    if sys_lang.startswith("zh"):
        return "zh"
    return "en"


# CLI 帮助文本国际化
_CLI_MESSAGES: Dict[str, Dict[str, str]] = {
    "description": {
        "zh": "自动分析 agent 会话并生成可复用 SKILL",
        "en": "Automatically analyze agent conversations and generate reusable SKILLs",
    },
    "config": {
        "zh": "配置文件路径，JSON 格式",
        "en": "Path to config file (JSON format)",
    },
    "input": {
        "zh": "会话文件或目录路径",
        "en": "Path to conversation file or directory",
    },
    "output_dir": {
        "zh": "SKILL 输出目录",
        "en": "Output directory for generated SKILLs",
    },
    "conflict": {
        "zh": "同名 SKILL 冲突处理策略",
        "en": "Strategy for handling SKILL name conflicts",
    },
    "preserve_raw": {
        "zh": "保留原文内容；启用前请确认不会泄露敏感信息",
        "en": "Preserve raw content; ensure no sensitive data is exposed before enabling",
    },
    "commands_title": {
        "zh": "可用命令",
        "en": "commands",
    },
    "analyze": {
        "zh": "读取并分析会话",
        "en": "Read and analyze conversations",
    },
    "json_lines": {
        "zh": "紧凑 JSON 输出，便于脚本解析",
        "en": "Compact JSON output for scripting",
    },
    "generate": {
        "zh": "分析会话并写入 SKILL",
        "en": "Analyze conversations and write SKILLs",
    },
    "name": {
        "zh": "生成的 SKILL 名称",
        "en": "Name of the generated SKILL",
    },
    "config_cmd": {
        "zh": "显示合并后的配置和适配策略",
        "en": "Show merged configuration and adapter strategy",
    },
    "validate_config": {
        "zh": "校验配置文件、环境变量和 CLI 覆盖项",
        "en": "Validate config file, environment variables and CLI overrides",
    },
    "diagnose": {
        "zh": "诊断运行环境和会话来源",
        "en": "Diagnose runtime environment and conversation sources",
    },
    "options_title": {
        "zh": "选项",
        "en": "options",
    },
    "help_option": {
        "zh": "显示帮助信息并退出",
        "en": "show this help message and exit",
    },
}


def _msg(key: str) -> str:
    """获取当前语言对应的 CLI 帮助文本。"""
    lang = _get_cli_lang()
    return _CLI_MESSAGES[key][lang]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="experience-to-skill-generator",
        description=_msg("description"),
        add_help=False,
    )
    parser._optionals.title = _msg("options_title")
    parser.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help=_msg("help_option"))
    parser.add_argument("--config", help=_msg("config"))
    parser.add_argument("--input", help=_msg("input"))
    parser.add_argument("--output-dir", help=_msg("output_dir"))
    parser.add_argument("--conflict", choices=["rename", "skip", "overwrite", "merge", "fail"], help=_msg("conflict"))
    parser.add_argument("--preserve-raw", action="store_true", help=_msg("preserve_raw"))
    subparsers = parser.add_subparsers(dest="command", required=True, title=_msg("commands_title"), metavar="<command>")

    def _sub(name: str, **kwargs: Any) -> argparse.ArgumentParser:
        """创建子命令 parser，统一国际化 options 标题和 -h/--help 文本。"""
        sp = subparsers.add_parser(name, add_help=False, **kwargs)
        sp._optionals.title = _msg("options_title")
        sp.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help=_msg("help_option"))
        return sp

    analyze = _sub("analyze", help=_msg("analyze"))
    analyze.add_argument("--json-lines", action="store_true", help=_msg("json_lines"))
    analyze.set_defaults(func=command_analyze)

    generate = _sub("generate", help=_msg("generate"))
    generate.add_argument("--name", help=_msg("name"))
    generate.set_defaults(func=command_generate)

    config = _sub("config", help=_msg("config_cmd"))
    config.set_defaults(func=command_config)

    validate = _sub("validate-config", help=_msg("validate_config"))
    validate.set_defaults(func=command_validate_config)

    diagnose = _sub("diagnose", help=_msg("diagnose"))
    diagnose.set_defaults(func=command_diagnose)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UserFacingError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())