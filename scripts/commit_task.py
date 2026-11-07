#!/usr/bin/env python3
"""按统一格式提交单个任务的改动。

用法：
    python {skill_root}/scripts/commit_task.py \
      --task task7 \
      --title "历史记录封面持久化" \
      --status pass \
      --path src/history.py \
      --path src/migrations/ \
提交消息由 status 决定标记：

    pass     -> task7: 历史记录封面持久化
    warn     -> task7 [未通过]: 历史记录封面持久化
    unknown  -> task7 [未能判定]: 历史记录封面持久化

其中 warn 对应 dev-plan 里的 ⚠️「未通过（已放行）」状态，提交消息里短写为 [未通过]。

**提交消息只有一行标题，不写正文。** `--rounds` / `--report` / `--run` 为兼容旧调用
保留，接受但不写入消息 —— 测试轮次和报告路径在 final-report.md 与
test-reports/ 里本来就有，不必在 git log 里重复一遍。

提交范围**只包含显式传入的 --path**（应来自 developer 返回的修改文件列表），
不使用全量 add，因此 .super-agent/ 过程产物不会进入仓库。

输出（首行即结论，供主智能体判断）：

    OK: {short_hash}    提交成功
    SKIP: {原因}        不是 git 仓库 / 没有配置远端，本次不执行任何 git 操作
    ERROR: {原因}       提交失败
    WARN: ...           提交成功之后的补充说明：工作区仍有未纳入本次提交的变更

无远端即视为「不启用 git」：没有远端就没有任何代码会离开本机，本地 commit 也失去
存档之外的意义，因此默认跳过。确实想只留本地历史时，显式加 `--allow-no-remote`。

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
    parser.add_argument("--rounds", help="（兼容保留）测试轮次；不再写入提交消息")
    parser.add_argument("--report", help="（兼容保留）测试报告路径；不再写入提交消息")
    parser.add_argument("--run", help="（兼容保留）批次 run_id；不再写入提交消息")
    parser.add_argument("--dry-run", action="store_true", help="只打印提交消息，不执行提交")
    parser.add_argument("--allow-no-remote", action="store_true",
                        help="没有配置远端时仍然本地提交（默认跳过整套 git 动作）")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()

    if run_git(repo, "rev-parse", "--git-dir").returncode != 0:
        print("SKIP: 当前目录不是 git 仓库，本次不执行任何 git 操作")
        return 0

    if not args.allow_no_remote:
        remotes = [r for r in text(run_git(repo, "remote").stdout).splitlines() if r.strip()]
        if not remotes:
            print("SKIP: 项目没有配置远端，跳过提交与推送；"
                  "如需只留本地历史，加 --allow-no-remote")
            return 0

    changed = run_git(repo, "status", "--porcelain", "--", *args.path)
    if changed.returncode != 0:
        return fail(text(changed.stderr) or "无法读取工作区状态")
    if not text(changed.stdout):
        return fail("指定路径没有变更，无需提交")

    # 提交消息只保留一行标题；测试轮次 / 报告路径 / run_id 不再重复写入 git log
    message = f"{args.task}{STATUS_MARKERS[args.status]}: {args.title}\n"

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
