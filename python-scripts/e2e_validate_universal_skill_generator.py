#!/usr/bin/env python3
"""通用 SKILL 生成器端到端验证脚本。

该脚本不依赖真实 OpenClaw 命令，仅验证 CLI 在 OpenClaw 适配模式和通用兼容目录模式下，
能完成会话分析、诊断和 SKILL 产物生成。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_SCRIPT = PROJECT_ROOT / "python-scripts" / "universal_skill_generator.py"
REQUIRED_SECTIONS = ["## 适用场景", "## 触发条件", "## 执行步骤", "## 注意事项", "## 示例用法"]


def run_command(args):
    result = subprocess.run(
        [sys.executable, str(CLI_SCRIPT), *args],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "命令执行失败: {}\n退出码: {}\nSTDOUT:\n{}\nSTDERR:\n{}".format(
                " ".join(args), result.returncode, result.stdout, result.stderr
            )
        )
    return result.stdout


def write_session(base_dir, name, topic):
    session_path = base_dir / f"{name}.json"
    session_path.write_text(
        json.dumps(
            {
                "title": topic,
                "messages": [
                    {"role": "user", "content": f"请实现{topic}，要求支持配置、错误提示和避免覆盖已有 SKILL"},
                    {
                        "role": "assistant",
                        "content": "1. 识别运行环境\n2. 读取配置\n3. 分析会话\n4. 生成结构化 SKILL\n5. 验证产物并处理冲突",
                    },
                    {"role": "user", "content": "请确保可以在自动化脚本中稳定运行"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return session_path


def validate_generated_skill(skill_path):
    if not skill_path.exists():
        raise AssertionError(f"未生成 SKILL 文件: {skill_path}")
    content = skill_path.read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_SECTIONS if section not in content]
    if missing:
        raise AssertionError(f"生成的 SKILL 缺少必要章节: {missing}")
    if "<!-- metadata:" not in content:
        raise AssertionError("生成的 SKILL 缺少 metadata 元信息")


def validate_agent_flow(base_dir, agent):
    session_path = write_session(base_dir, f"{agent}-session", f"{agent} 环境通用技能生成流程")
    output_dir = base_dir / f"{agent}-generated-skills"
    skill_name = f"{agent}-universal-flow"

    diagnose_payload = json.loads(run_command(["--agent", agent, "--input", str(session_path), "diagnose"]))
    if diagnose_payload["agent"] != agent:
        raise AssertionError(f"诊断结果 agent 不匹配: {diagnose_payload['agent']} != {agent}")
    if not diagnose_payload["session_sources"] or not diagnose_payload["session_sources"][0]["exists"]:
        raise AssertionError("诊断结果未识别会话来源")

    analysis_payload = json.loads(run_command(["--agent", agent, "--input", str(session_path), "analyze", "--json-lines"]))
    if not analysis_payload.get("tasks"):
        raise AssertionError("分析结果未提取任务")
    if analysis_payload.get("confidence", 0) <= 0:
        raise AssertionError("分析结果置信度无效")

    generate_payload = json.loads(
        run_command(
            [
                "--agent",
                agent,
                "--input",
                str(session_path),
                "--output-dir",
                str(output_dir),
                "--conflict",
                "rename",
                "generate",
                "--name",
                skill_name,
            ]
        )
    )
    write_result = generate_payload.get("write_result", {})
    skill_path = Path(write_result.get("path", ""))
    if write_result.get("action") not in {"created", "renamed"}:
        raise AssertionError(f"不符合预期的写入动作: {write_result}")
    validate_generated_skill(skill_path)
    return skill_path


def main():
    with tempfile.TemporaryDirectory(prefix="esg-e2e-") as tmp:
        base_dir = Path(tmp)
        generic_skill = validate_agent_flow(base_dir, "generic")
        openclaw_skill = validate_agent_flow(base_dir, "openclaw")
        print(
            json.dumps(
                {
                    "status": "ok",
                    "generic_skill": str(generic_skill),
                    "openclaw_skill": str(openclaw_skill),
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
