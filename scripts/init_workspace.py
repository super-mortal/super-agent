#!/usr/bin/env python3
"""init_workspace.py — 创建新的 .super-agent 运行批次。

批次目录：
    .super-agent/runs/{project-name}-{YYYY-MM-DD}--{NN}

Usage:
    python init_workspace.py <PROJECT_ROOT> [options]

Options:
    --project-name NAME       项目名（字母、数字和连字符）
    --error-prefix PREFIX     错误码前缀（默认 PN）
    --gitignore               同时更新项目根的 .gitignore
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_ROOT / "assets"


def now_beijing() -> datetime:
    """返回北京时间；系统缺少 tzdata 时退回固定 UTC+8。"""
    try:
        return datetime.now(ZoneInfo("Asia/Shanghai"))
    except ZoneInfoNotFoundError:
        return datetime.now(timezone(timedelta(hours=8)))


def now_iso() -> str:
    return now_beijing().isoformat(timespec="seconds")


def slugify(value: str, default: str = "project") -> str:
    """把项目名转换为可用于目录名的 slug。"""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or default


def identifier_prefix(value: str, default: str = "project") -> str:
    """把项目名转换为可用于代码和数据库的 snake_case 标识符。"""
    prefix = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    prefix = prefix or default
    if prefix[0].isdigit():
        prefix = f"p_{prefix}"
    return prefix


def pascal_prefix(value: str, default: str = "Project") -> str:
    """把项目名转换为 PascalCase 标识符。"""
    parts = [part for part in re.split(r"[^a-zA-Z0-9]+", value) if part]
    prefix = "".join(part[:1].upper() + part[1:] for part in parts) or default
    if prefix[0].isdigit():
        prefix = f"Project{prefix}"
    return prefix


def next_run_id(agent_dir: Path, project_name: str) -> str:
    """按当天已有批次计算下一个批次号，例如 pocketnote-2026-09-10--01。"""
    date = now_beijing().strftime("%Y-%m-%d")
    prefix = f"{slugify(project_name)}-{date}--"
    runs_dir = agent_dir / "runs"
    highest = 0
    if runs_dir.is_dir():
        for candidate in runs_dir.iterdir():
            if not candidate.is_dir() or not candidate.name.startswith(prefix):
                continue
            suffix = candidate.name[len(prefix):]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
    return f"{prefix}{highest + 1:02d}"


def resolve_vars(
    text: str,
    project_name: str,
    error_prefix: str,
    project_root: Path,
    run_root: Path,
    skill_root: Path,
) -> str:
    """替换模板中的占位符。"""
    today = now_beijing().strftime("%Y-%m-%d")
    project_slug = slugify(project_name)
    snake_prefix = identifier_prefix(project_name)
    pascal = pascal_prefix(project_name)
    return (
        text.replace("{project_name}", project_name)
        .replace("{project_slug}", project_slug)
        .replace("{snake_prefix}", snake_prefix)
        .replace("{pascal_prefix}", pascal)
        .replace("{project_name_lower}", snake_prefix)
        .replace("{ProjectName}", pascal)
        .replace("{project-name}", project_slug)
        .replace("{error_prefix}", error_prefix)
        .replace("{skill_root}", str(skill_root))
        .replace("{now_script}", str(skill_root / "scripts" / "now.py"))
        .replace("{today}", today)
        .replace("{now_iso}", now_iso())
        .replace("{project_root}", str(project_root))
        .replace("{run_root}", str(run_root))
        .replace("{run_id}", run_root.name)
    )


def write_run_metadata(run_root: Path, project_root: Path, project_name: str, error_prefix: str) -> None:
    metadata = {
        "run_id": run_root.name,
        "project_name": project_name,
        "project_slug": slugify(project_name),
        "snake_prefix": identifier_prefix(project_name),
        "pascal_prefix": pascal_prefix(project_name),
        "project_root": str(project_root),
        "error_prefix": error_prefix,
        "timezone": "Asia/Shanghai",
        "status": "running",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "completed_at": None,
        "final_report": None,
    }
    (run_root / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  WRITE {path}")


def update_gitignore(project_root: Path) -> None:
    """追加批次内运行日志和测试报告到 .gitignore。"""
    gi = project_root / ".gitignore"
    additions = [
        ".super-agent/runs/*/logs/",
        ".super-agent/runs/*/test-reports/",
    ]
    if gi.exists():
        content = gi.read_text(encoding="utf-8")
    else:
        content = ""
    lines = content.splitlines()
    to_add = [a for a in additions if a not in lines]
    if to_add:
        with gi.open("a", encoding="utf-8") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            f.write("\n# super-agent\n")
            for a in to_add:
                f.write(f"{a}\n")
        print(f"  UP    {gi} (added {len(to_add)} entries)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="创建新的 super-agent 运行批次"
    )
    parser.add_argument(
        "project_root",
        type=Path,
        help="项目根目录绝对路径",
    )
    parser.add_argument(
        "--project-name",
        default=None,
        help="项目名（字母、数字和连字符），默认从目录名推断",
    )
    parser.add_argument(
        "--error-prefix",
        default="PN",
        help="错误码前缀，默认 PN",
    )
    parser.add_argument(
        "--gitignore",
        action="store_true",
        help="同时更新 .gitignore",
    )
    args = parser.parse_args()

    project_root: Path = args.project_root.resolve()
    if not project_root.exists():
        print(f"ERROR: 项目根目录不存在: {project_root}", file=sys.stderr)
        return 1

    project_name = args.project_name or project_root.name
    error_prefix = args.error_prefix
    agent_dir = project_root / ".super-agent"
    run_id = next_run_id(agent_dir, project_name)
    run_root = agent_dir / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=False)

    plan_dir = run_root / "plan"
    logs_dir = run_root / "logs"
    reports_dir = run_root / "test-reports"

    write_run_metadata(run_root, project_root, project_name, error_prefix)

    template_map = {
        run_root / "final-report.md": ASSETS_DIR / "final-report-template.md",
        plan_dir / "dev-plan.md": ASSETS_DIR / "plan-template.md",
        plan_dir / "dev-spec.md": ASSETS_DIR / "spec-template.md",
        plan_dir / "requirements.md": ASSETS_DIR / "requirements-template.md",
        plan_dir / "lessons-learned.md": ASSETS_DIR / "lessons-template.md",
        plan_dir / "context7-record.md": ASSETS_DIR / "context7-record-template.md",
        logs_dir / "main-log.md": ASSETS_DIR / "log-template.md",
    }

    print(f"PROJECT_ROOT  = {project_root}")
    print(f"PROJECT_NAME  = {project_name}")
    print(f"ERROR_PREFIX  = {error_prefix}")
    print(f"RUN_ID        = {run_id}")
    print(f"RUN_ROOT      = {run_root}")
    print()

    for target, template in template_map.items():
        if not template.exists():
            print(f"  WARN  模板不存在: {template}", file=sys.stderr)
            continue
        content = template.read_text(encoding="utf-8")
        content = resolve_vars(
            content,
            project_name,
            error_prefix,
            project_root,
            run_root,
            SKILL_ROOT,
        )
        write_file(target, content)

    reports_dir.mkdir(parents=True, exist_ok=True)
    print(f"  DIR   {reports_dir}")

    if args.gitignore:
        update_gitignore(project_root)

    print()
    print(f"Next: 主智能体读取 {plan_dir / 'dev-plan.md'} 开始阶段循环。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
