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

提交身份：按技能加载时用户选定的偏好执行（`--identity auto` 读
`{project_root}/.super-agent/preferences.json`，没记录时默认用户本人）。

    user  -> 剔除 IDE/Agent 注入的 GIT_AUTHOR_* / GIT_COMMITTER_*，
             用 git config 里的身份 + `-c` / `--author` 强制写入
    ide   -> 保留注入，commit 署名为 IDE（如 trae-solo-agent）

提交后会回读 `%an/%ae/%cn/%ce`：用户身份模式下不符则打 `WARN`；
IDE 模式下打一行 `NOTE` 说明本次署名为工具。

`.super-agent/` 是本 skill 的过程产物目录，`.gitignore` 由 init_workspace.py 在初始化时
生成或追加；两者都不属于任何任务、也永不入库，因此不计入 WARN 统计 —— 否则每个任务
都会亮一次一字不差的警告，真正漏文件时反而被淹没。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from git_identity import IDENTITY_ENV_VARS, saved_mode  # noqa: E402

STATUS_CHOICES = ("pass", "warn", "unknown")
IDENTITY_CHOICES = ("auto", "user", "ide")
STATUS_MARKERS = {
    "pass": "",
    "warn": " [未通过]",
    "unknown": " [未能判定]",
}
# 这些路径属于「提交流程自己造的已知产物」，不计入遗漏提醒
EXEMPT_PATHS = (".super-agent/", ".gitignore")


def run_git(
    repo: Path, *args: str, stdin: str | None = None, clean_identity: bool = True
) -> subprocess.CompletedProcess:
    """执行 git 命令。消息按 UTF-8 字节传入，避免受本机 locale 影响。

    clean_identity=True 时剔除 IDE / Agent 注入的身份环境变量
    （如 Trae 的 GIT_COMMITTER_NAME=trae-solo-agent）。
    用户选择「用 IDE 身份」时要传 False，让注入保持生效。
    """
    env = dict(os.environ)
    env.setdefault("GIT_PAGER", "cat")
    if clean_identity:
        for key in IDENTITY_ENV_VARS:
            env.pop(key, None)
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
    parser.add_argument("--identity", choices=IDENTITY_CHOICES, default="auto",
                        help="提交身份：auto=按已记录偏好（默认 user）/ user=用户本人 / ide=沿用 IDE 注入")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()

    # 任务号校验：只接受 taskN；task0 是 planner 的前置工作，不进循环也不入库
    m = re.fullmatch(r"task(\d+)", args.task.strip())
    if not m:
        return fail(f"--task 必须是 taskN 形式（如 task1），收到：{args.task}")
    if int(m.group(1)) == 0:
        return fail("task0 是 planner 的前置工作（规划文档 / 脚手架），不参与提交；"
                    "若有需要入库的骨架代码，请划入 task1")

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

    # 提交身份：按已记录偏好决定，缺省用用户本人
    mode = args.identity
    if mode == "auto":
        mode = (saved_mode(repo) or {}).get("mode") or "user"

    author_name = author_email = ""
    if mode == "user":
        author_name = text(run_git(repo, "config", "--get", "user.name").stdout)
        author_email = text(run_git(repo, "config", "--get", "user.email").stdout)
        if not author_name or not author_email:
            return fail("选择了用户身份，但仓库没有配置 user.name / user.email")

    if args.dry_run:
        print("DRY-RUN: 未执行提交，消息如下")
        print(message, end="")
        if mode == "user":
            print(f"  身份：{author_name} <{author_email}>（用户本人）")
        else:
            effective = text(run_git(repo, "var", "GIT_COMMITTER_IDENT").stdout)
            print(f"  身份：沿用 IDE / 环境（{effective}）")
        return 0

    added = run_git(repo, "add", "-A", "--", *args.path)
    if added.returncode != 0:
        return fail(text(added.stderr) or "git add 失败")

    if mode == "user":
        committed = run_git(
            repo,
            "-c", f"user.name={author_name}",
            "-c", f"user.email={author_email}",
            "commit", "-F", "-", "--author", f"{author_name} <{author_email}>",
            stdin=message,
        )
    else:
        # 保留 IDE 注入的身份环境变量，按用户选择让 IDE 署名
        committed = run_git(repo, "commit", "-F", "-", stdin=message, clean_identity=False)
    if committed.returncode != 0:
        return fail(text(committed.stderr) or text(committed.stdout) or "git commit 失败")

    sha = run_git(repo, "rev-parse", "--short", "HEAD")
    short_hash = text(sha.stdout) if sha.returncode == 0 else "unknown"

    print(f"OK: {short_hash}")

    # 回读实际落库的身份
    actual = text(run_git(repo, "log", "-1", "--format=%an\t%ae\t%cn\t%ce").stdout).split("\t")
    if len(actual) == 4:
        an, ae, cn, ce = actual
        if mode == "user" and ((an, ae) != (author_name, author_email)
                               or (cn, ce) != (author_name, author_email)):
            print(f"WARN: 实际提交身份与预期不符：author {an} <{ae}> / committer {cn} <{ce}>")
            print(f"  预期：{author_name} <{author_email}>")
        elif mode == "ide":
            print(f"NOTE: 按已记录偏好，本次使用 IDE / 环境身份 {an} <{ae}>")

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
