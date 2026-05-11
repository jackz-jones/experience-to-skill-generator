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

    def test_command_extract_outputs_structured_chunks(self):
        """extract 命令应输出预处理后的分段会话文本和 prompt_hint。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_session(tmpdir, [
                {"role": "user", "content": "请实现一个通用安装脚本"},
                {"role": "assistant", "content": "1. 检查依赖\n2. 识别环境\n3. 生成 SKILL"},
            ])
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = usg.main(["--input", str(Path(tmpdir) / "session.json"), "extract"])
            self.assertEqual(exit_code, 0)
            payload = json.loads(buf.getvalue())
            self.assertIn("chunks", payload)
            self.assertIn("prompt_hint", payload)
            self.assertGreater(payload["total_messages"], 0)
            self.assertGreater(len(payload["chunks"]), 0)
            # 每个 chunk 应包含 messages
            for chunk in payload["chunks"]:
                self.assertIn("chunk_id", chunk)
                self.assertIn("messages", chunk)
                self.assertGreater(len(chunk["messages"]), 0)

    def test_parse_external_analysis_valid(self):
        """_parse_external_analysis 应正确解析合法的外部分析 JSON。"""
        raw = json.dumps({
            "tasks": ["开发监控 API"],
            "key_steps": ["定义接口", "实现适配器"],
            "constraints": ["支持多链"],
            "keywords": ["blockchain", "API"],
            "confidence": 0.9,
        })
        result = usg._parse_external_analysis(raw)
        self.assertEqual(result["tasks"], ["开发监控 API"])
        self.assertEqual(result["confidence"], 0.9)
        self.assertFalse(result["requires_review"])
        self.assertEqual(result["summary"]["analysis_mode"], "external_llm")

    def test_parse_external_analysis_rejects_missing_fields(self):
        """_parse_external_analysis 应拒绝缺少必要字段的 JSON。"""
        raw = json.dumps({"keywords": ["test"]})
        with self.assertRaises(usg.UserFacingError):
            usg._parse_external_analysis(raw)

    def test_parse_external_analysis_rejects_invalid_json(self):
        """_parse_external_analysis 应拒绝无效 JSON。"""
        with self.assertRaises(usg.UserFacingError):
            usg._parse_external_analysis("not json")

    def test_generate_with_external_analysis(self):
        """generate --analysis 应使用外部分析结果生成 SKILL。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_session(tmpdir, [
                {"role": "user", "content": "请实现区块链监控"},
                {"role": "assistant", "content": "1. 定义接口\n2. 实现适配器"},
            ])
            analysis_json = json.dumps({
                "tasks": ["开发区块链监控 API"],
                "key_steps": ["定义 REST 接口", "抽象适配器", "添加测试"],
                "constraints": ["支持多链扩展"],
                "keywords": ["blockchain", "API"],
                "confidence": 0.88,
            })
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = usg.main([
                    "--input", str(Path(tmpdir) / "session.json"),
                    "--output-dir", str(Path(tmpdir) / "skills"),
                    "generate",
                    "--name", "blockchain-monitor",
                    "--analysis", analysis_json,
                ])
            self.assertEqual(exit_code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["analysis_mode"], "external_llm")
            self.assertEqual(payload["confidence"], 0.88)
            # 验证生成的 SKILL 文件包含外部分析的内容
            skill_path = Path(payload["write_result"]["path"])
            content = skill_path.read_text(encoding="utf-8")
            self.assertIn("定义 REST 接口", content)
            self.assertIn("支持多链扩展", content)

    def test_generate_without_analysis_uses_builtin_rules(self):
        """generate 不传 --analysis 时应使用内置规则引擎。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_session(tmpdir, [
                {"role": "user", "content": "请帮我实现一个通用安装脚本"},
                {"role": "assistant", "content": "1. 检查依赖\n2. 识别环境\n3. 生成 SKILL"},
            ])
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = usg.main([
                    "--input", str(Path(tmpdir) / "session.json"),
                    "--output-dir", str(Path(tmpdir) / "skills"),
                    "generate",
                    "--name", "install-flow",
                ])
            self.assertEqual(exit_code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["analysis_mode"], "builtin_rules")

    def test_setup_agent_creates_claude_md(self):
        """setup-agent claude-code 应在指定目录生成 CLAUDE.md。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            import io
            from contextlib import redirect_stdout, redirect_stderr
            buf = io.StringIO()
            err_buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err_buf):
                exit_code = usg.main(["setup-agent", "claude-code", "--output", tmpdir])
            self.assertEqual(exit_code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["action"], "created")
            self.assertEqual(payload["filename"], "CLAUDE.md")
            # 验证文件已创建且包含工作流指引
            target = Path(payload["target_path"])
            self.assertTrue(target.exists())
            content = target.read_text(encoding="utf-8")
            self.assertIn("Experience-to-Skill Generator", content)
            self.assertIn("extract", content)
            self.assertIn("generate", content)

    def test_setup_agent_creates_cursorrules(self):
        """setup-agent cursor 应生成 .cursorrules 文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            import io
            from contextlib import redirect_stdout, redirect_stderr
            buf = io.StringIO()
            err_buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err_buf):
                exit_code = usg.main(["setup-agent", "cursor", "--output", tmpdir])
            self.assertEqual(exit_code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["filename"], ".cursorrules")
            target = Path(payload["target_path"])
            self.assertTrue(target.exists())

    def test_setup_agent_skips_existing_guide(self):
        """setup-agent 应跳过已包含指引的文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            import io
            from contextlib import redirect_stdout, redirect_stderr
            # 先创建一次
            buf = io.StringIO()
            err_buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err_buf):
                usg.main(["setup-agent", "claude-code", "--output", tmpdir])
            # 再次运行应跳过
            buf2 = io.StringIO()
            err_buf2 = io.StringIO()
            with redirect_stdout(buf2), redirect_stderr(err_buf2):
                exit_code = usg.main(["setup-agent", "claude-code", "--output", tmpdir])
            self.assertEqual(exit_code, 0)
            payload = json.loads(buf2.getvalue())
            self.assertEqual(payload["action"], "skipped")

    def test_setup_agent_force_overwrites(self):
        """setup-agent --force 应覆盖已存在的文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            import io
            from contextlib import redirect_stdout, redirect_stderr
            # 先创建一次
            buf = io.StringIO()
            err_buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err_buf):
                usg.main(["setup-agent", "claude-code", "--output", tmpdir])
            # 使用 --force 覆盖
            buf2 = io.StringIO()
            err_buf2 = io.StringIO()
            with redirect_stdout(buf2), redirect_stderr(err_buf2):
                exit_code = usg.main(["setup-agent", "claude-code", "--output", tmpdir, "--force"])
            self.assertEqual(exit_code, 0)
            payload = json.loads(buf2.getvalue())
            self.assertEqual(payload["action"], "overwritten")

    def test_setup_agent_dry_run(self):
        """setup-agent --dry-run 应输出内容但不写入文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = usg.main(["setup-agent", "windsurf", "--output", tmpdir, "--dry-run"])
            self.assertEqual(exit_code, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["dry_run"])
            self.assertIn("content", payload)
            self.assertIn("Experience-to-Skill Generator", payload["content"])
            # 文件不应被创建
            target = Path(tmpdir) / ".windsurfrules"
            self.assertFalse(target.exists())

    def test_setup_agent_appends_to_existing_file(self):
        """setup-agent 应追加到已存在但不包含指引的文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            import io
            from contextlib import redirect_stdout, redirect_stderr
            # 先创建一个不包含指引的 CLAUDE.md
            target = Path(tmpdir) / "CLAUDE.md"
            target.write_text("# My Project Rules\n\nSome existing rules.\n", encoding="utf-8")
            # 运行 setup-agent
            buf = io.StringIO()
            err_buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err_buf):
                exit_code = usg.main(["setup-agent", "claude-code", "--output", tmpdir])
            self.assertEqual(exit_code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["action"], "appended")
            # 验证原内容保留且新内容追加
            content = target.read_text(encoding="utf-8")
            self.assertIn("My Project Rules", content)
            self.assertIn("Experience-to-Skill Generator", content)


if __name__ == "__main__":
    unittest.main()
