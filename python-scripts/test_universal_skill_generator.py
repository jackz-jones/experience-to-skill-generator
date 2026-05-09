#!/usr/bin/env python3
"""通用 SKILL 生成器核心测试。"""

import argparse
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(os.path.dirname(__file__))

import universal_skill_generator as usg


class UniversalSkillGeneratorTest(unittest.TestCase):
    def make_args(self, **overrides):
        defaults = {
            "config": None,
            "input": None,
            "output_dir": None,
            "conflict": None,
            "preserve_raw": False,
            "name": None,
            "json_lines": False,
        }
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def make_context(self, tmpdir, **config_overrides):
        config = usg.deep_merge(usg.DEFAULT_CONFIG, {
            "agent": "generic",
            "session_sources": [
                {"type": "cli", "path": str(Path(tmpdir) / "session.json"), "patterns": ["*.json"]}
            ],
            "output": {
                "target_dir": str(Path(tmpdir) / "skills"),
                "conflict_strategy": "rename",
                "metadata_format": "generic",
            },
            "analysis": {
                "min_score": 50,
                "max_chars": 2000,
                "chunk_chars": 120,
                "confidence_threshold": 0.75,
            },
        })
        config = usg.deep_merge(config, config_overrides)
        usg.validate_config(config)
        return usg.RuntimeContext(
            config=config,
            adapter=usg.KNOWN_AGENT_ADAPTERS["generic"],
            adapter_name="generic",
            config_path=None,
            adapter_strategy="test:generic",
        )

    def write_session(self, tmpdir, messages):
        session_path = Path(tmpdir) / "session.json"
        session_path.write_text(json.dumps({"messages": messages}, ensure_ascii=False), encoding="utf-8")
        return session_path

    def test_validate_config_rejects_invalid_values(self):
        config = usg.deep_merge(usg.DEFAULT_CONFIG, {
            "output": {"conflict_strategy": "invalid"},
        })

        with self.assertRaises(usg.UserFacingError):
            usg.validate_config(config)

    def test_configured_adapter_is_registered_and_selected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps({
                "agent": "custom-agent",
                "session_sources": [
                    {"type": "custom", "path": str(Path(tmpdir) / "sessions"), "patterns": ["*.json"]}
                ],
                "output": {"target_dir": str(Path(tmpdir) / "skills"), "conflict_strategy": "rename", "metadata_format": "json"},
                "adapters": {
                    "custom-agent": {
                        "skill_dir": str(Path(tmpdir) / "custom-skills"),
                        "config_dir": str(Path(tmpdir) / "custom-config"),
                        "session_dir": str(Path(tmpdir) / "sessions"),
                        "metadata_format": "json",
                    }
                },
            }), encoding="utf-8")

            context = usg.build_context(self.make_args(config=str(config_path)))

            self.assertEqual(context.adapter_name, "custom-agent")
            self.assertEqual(context.adapter_strategy, "explicit:custom-agent")
            self.assertEqual(context.adapter["metadata_format"], "json")

    def test_load_sessions_redacts_sensitive_data_and_chunks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_session(tmpdir, [
                {"role": "user", "content": "请分析 api_key=abcdef1234567890 和 /Users/alice/project 的问题"},
                {"role": "assistant", "content": "1. 检查配置\n2. 修复 token=secret-value\n3. 验证结果"},
                {"role": "assistant", "content": "补充一段较长内容用于触发分段。" * 20},
            ])
            context = self.make_context(tmpdir)

            messages = usg.load_sessions(context)
            combined = "\n".join(message["content"] for message in messages)

            self.assertIn("<REDACTED>", combined)
            self.assertIn("/Users/<USER>", combined)
            self.assertGreaterEqual(max(message.get("chunk", 1) for message in messages), 2)

    def test_generate_skill_document_contains_required_sections_and_review_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = self.make_context(tmpdir)
            analysis = {
                "tasks": ["请实现通用安装脚本并避免覆盖已有技能"],
                "key_steps": ["检查运行依赖", "识别 agent 环境", "生成结构化 SKILL"],
                "constraints": ["必须避免静默覆盖已有文件"],
                "keywords": ["agent", "skill", "install"],
                "summary": {"source_files": ["/tmp/session.json"]},
                "confidence": 0.4,
                "requires_review": True,
            }

            skill_name, content = usg.generate_skill_document(analysis, context, "install-flow")

            self.assertEqual(skill_name, "install-flow")
            self.assertIn("## 适用场景", content)
            self.assertIn("## 触发条件", content)
            self.assertIn("## 执行步骤", content)
            self.assertIn("## 注意事项", content)
            self.assertIn("## 示例用法", content)
            self.assertIn("分析置信度不足", content)

    def test_write_skill_conflict_strategies(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = self.make_context(tmpdir)
            first = usg.write_skill(context, "agent-install-flow", "# first")
            self.assertEqual(first["action"], "created")

            renamed = usg.write_skill(context, "agent-install-flow", "# renamed")
            self.assertEqual(renamed["action"], "renamed")
            self.assertTrue(renamed["path"].endswith("agent-install-flow-2/SKILL.md"))

            skip_context = self.make_context(tmpdir, output={"conflict_strategy": "skip"})
            skipped = usg.write_skill(skip_context, "agent-install-flow", "# skipped")
            self.assertEqual(skipped["action"], "skipped")

            merge_context = self.make_context(tmpdir, output={"conflict_strategy": "merge"})
            merged = usg.write_skill(merge_context, "agent-install-flow", "# merged")
            self.assertEqual(merged["action"], "merged")
            self.assertIn("合并的新分析结果", Path(merged["path"]).read_text(encoding="utf-8"))

            overwrite_context = self.make_context(tmpdir, output={"conflict_strategy": "overwrite"})
            overwritten = usg.write_skill(overwrite_context, "agent-install-flow", "# overwritten")
            self.assertEqual(overwritten["action"], "overwritten")
            self.assertTrue(Path(overwritten["path"]).with_suffix(".md.bak").exists())

            fail_context = self.make_context(tmpdir, output={"conflict_strategy": "fail"})
            with self.assertRaises(usg.UserFacingError):
                usg.write_skill(fail_context, "agent-install-flow", "# fail")

    def test_cli_invalid_input_returns_non_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing.json"
            exit_code = usg.main(["--input", str(missing), "analyze", "--json-lines"])
            self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
