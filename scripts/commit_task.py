#!/usr/bin/env python3
"""按统一格式提交单个任务的改动。

用法：
    python {skill_root}/scripts/commit_task.py \
      --task task7 \
      --title "历史记录封面持久化" \
      --status pass \
      --path src/history.py \
      --path src/migrations/ \
      --rounds 2 \
      --report test-reports/task7-p1-history-test-report.md \
      --run pocketnote-2026-09-10--01

提交消息由 status 决定标记：

    pass     -> task7: 历史记录封面持久化
    warn     -> task7 [未通过]: 历史记录封面持久化
    unknown  -> task7 [未能判定]: 历史记录封面持久化

其中 warn 对应 dev-plan 里的 ⚠️「未通过（已放行）」状态，提交消息里短写为 [未通过]。

正文只在传入对应选项时追加：

    test-rounds: 2
    test-report: test-reports/task7-p1-history-test-report.md
    run: pocketnote-2026-09-10--01

提交范围**只包含显式传入的 --path**（应来自 developer 返回的修改文件列表），
不使用全量 add，因此 .super-agent/ 过程产物不会进入仓库。

输出（首行即结论，供主智能体判断）：

    OK: {short_hash}    提交成功
    SKIP: {原因}        当前目录不是 git 仓库，本次不执行任何 git 操作
    ERROR: {原因}       提交失败
    WARN: ...           提交成功之后的补充说明：工作区仍有未纳入本次提交的变更

`.super-agent/` 是本 skill 的过程产物目录，`.gitignore` 由 init_workspace.py 在初始化时
生成或追加；两者都不属于任何任务、也永不入库，因此不计入 WARN 统计 —— 否则每个任务
都会亮一次一字不差的警告，真正漏文件时反而被淹没。
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

STATUS_CHOICES = ("pass", "warn", "unknown")
STATUS_MARKERS = {
    "pass": "",
    "warn": " [未通过]",
    "unknown": " [未能判定]",
}
# 这些路径属于「提交流程自己造的已知产物」，不计入遗漏提醒
EXEMPT_PATHS = (".super-agent/", ".gitignore")


def run_git(repo: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    """执行 git 命令。消息按 UTF-8 字节传入，避免受本机 locale 影响。"""
    env = dict(os.environ)
    env.setdefault("GIT_PAGER", "cat")
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        input=stdin.encode("utf-8") if stdin is not None else None,
        capture_output=True,
        env=env,
    )


def text(raw: bytes) -> str:
    return raw.decode("utf-8", "replace").strip()


def fail(reason: str) -> int:
    print(f"ERROR: {reason}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="按统一格式提交单个任务的改动")
    parser.add_argument("--repo", default=".", help="目标项目根目录，默认当前目录")
    parser.add_argument("--task", required=True, help="任务号，例如 task7")
    parser.add_argument("--title", required=True, help="任务标题，原样取自 dev-plan")
    parser.add_argument("--status", required=True, choices=STATUS_CHOICES,
                        help="任务判定结果：pass / warn（用尽测试轮次）/ unknown（未能判定）")
    parser.add_argument("--path", action="append", required=True, metavar="PATH",
                        help="本次提交包含的路径，可重复；应来自 developer 返回的修改文件列表")
    parser.add_argument("--rounds", help="测试轮次，例如 2")
    parser.add_argument("--report", help="测试报告相对路径")
    parser.add_argument("--run", help="批次 run_id")
    parser.add_argument("--dry-run", action="store_true", help="只打印提交消息，不执行提交")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()

    if run_git(repo, "rev-parse", "--git-dir").returncode != 0:
        print("SKIP: 当前目录不是 git 仓库，本次不执行任何 git 操作")
        return 0

    changed = run_git(repo, "status", "--porcelain", "--", *args.path)
    if changed.returncode != 0:
        return fail(text(changed.stderr) or "无法读取工作区状态")
    if not text(changed.stdout):
        return fail("指定路径没有变更，无需提交")

    subject = f"{args.task}{STATUS_MARKERS[args.status]}: {args.title}"
    body_lines = []
    if args.rounds:
        body_lines.append(f"test-rounds: {args.rounds}")
    if args.report:
        body_lines.append(f"test-report: {args.report}")
    if args.run:
        body_lines.append(f"run: {args.run}")
    message = subject + "\n" if not body_lines else f"{subject}\n\n" + "\n".join(body_lines) + "\n"

    if args.dry_run:
        print("DRY-RUN: 未执行提交，消息如下")
        print(message, end="")
        return 0

    added = run_git(repo, "add", "-A", "--", *args.path)
    if added.returncode != 0:
        return fail(text(added.stderr) or "git add 失败")

    committed = run_git(repo, "commit", "-F", "-", stdin=message)
    if committed.returncode != 0:
        return fail(text(committed.stderr) or text(committed.stdout) or "git commit 失败")

    sha = run_git(repo, "rev-parse", "--short", "HEAD")
    short_hash = text(sha.stdout) if sha.returncode == 0 else "unknown"

    print(f"OK: {short_hash}")

    leftover = run_git(repo, "-c", "core.quotepath=false", "status", "--porcelain")
    if leftover.returncode == 0:
        remaining = [
            l for l in text(leftover.stdout).splitlines()
            if l.strip() and not l[3:].startswith(EXEMPT_PATHS)
        ]
        if remaining:
            print(f"WARN: 工作区仍有 {len(remaining)} 处未纳入本次提交的变更")
            for line in remaining:
                print(f"  {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
