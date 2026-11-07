#!/usr/bin/env python3
"""把当前批次的本地提交推送到远端，推送前先探活。

用法：
    # 只预览：查远端、查分支、查待推条数、检测会不会被拒（不做任何写操作）
    python {skill_root}/scripts/push_task.py --repo {project_root}

    # 真正推送（主智能体拿到用户确认后才加 --confirm）
    python {skill_root}/scripts/push_task.py --repo {project_root} --confirm

行为：

- 只推**当前分支**，命令固定为 `git push -u origin {branch}`。
  `-u` 的作用是绑定 upstream：首次推送没有它，下次裸 `git push` 会报
  "no upstream branch"，这就是历史上推不动的根因。
- 推送前先 `git ls-remote --heads origin {branch}` 判断远端分支**是否存在**，
  避免 `git log origin/{branch}..HEAD` 在远端还没有该分支时报 unknown revision。
- 再用 `git merge-base --is-ancestor` 判断远端是否已领先本地
  （non-fast-forward）：是则输出 `BLOCKED` 并**拒绝推送**，
  绝不 force、绝不自动 rebase/merge。
- 认证交互被禁用（`GIT_TERMINAL_PROMPT=0`），缺凭据时直接失败返回，不会卡住。

输出（首行即结论）：
    OK: {remote}/{branch} 已推送 {N} 条
    PREVIEW: 可推送 {N} 条 ...（未加 --confirm，未执行推送）
    SKIP: {原因}        不是 git 仓库 / 没有配置远端 / 没有待推提交
    BLOCKED: {原因}     远端领先本地或推送被拒，需要用户决定怎么处理
    ERROR: {原因}       推送失败（认证、网络、权限等）

退出码：0 = 成功/跳过/预览，2 = BLOCKED，1 = ERROR。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """执行 git 命令；禁掉交互式凭据输入，避免智能体流程被卡住。"""
    env = dict(os.environ)
    env["GIT_PAGER"] = "cat"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = env.get("GIT_ASKPASS", "echo")
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        env=env,
    )


def text(raw: bytes) -> str:
    return raw.decode("utf-8", "replace").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="把当前批次的本地提交推送到远端（推送前先探活）")
    parser.add_argument("--repo", default=".", help="目标项目根目录，默认当前目录")
    parser.add_argument("--remote", default="origin", help="远端名，默认 origin")
    parser.add_argument("--branch", default=None, help="分支名，默认当前分支")
    parser.add_argument("--confirm", action="store_true",
                        help="真正执行推送；不加此参数时只做只读预览")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()

    if run_git(repo, "rev-parse", "--is-inside-work-tree").returncode != 0:
        print("SKIP: 当前目录不是 git 仓库，不执行任何推送")
        return 0

    remotes = text(run_git(repo, "remote").stdout).splitlines()
    if args.remote not in remotes:
        names = ", ".join(remotes) if remotes else "无"
        print(f"SKIP: 没有配置远端 {args.remote}（已有远端：{names}），不执行推送")
        return 0

    if args.branch:
        branch = args.branch
    else:
        head = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        if head.returncode != 0:
            print(f"ERROR: 无法确定当前分支：{text(head.stderr)}")
            return 1
        branch = text(head.stdout)
        if branch == "HEAD":
            print("BLOCKED: 当前处于 detached HEAD，没有可推送的分支名")
            return 2

    remote_ref = f"{args.remote}/{branch}"

    # 远端是否已有该分支（ls-remote 不需要本地存在 origin/{branch} 引用）
    ls = run_git(repo, "ls-remote", "--heads", args.remote, branch)
    if ls.returncode != 0:
        print(f"ERROR: 无法访问远端 {args.remote}（认证或网络问题）：{text(ls.stderr)}")
        return 1
    remote_exists = bool(text(ls.stdout))

    pending = 0
    if remote_exists:
        # 取远端最新状态，再比较；fetch 只更新远程追踪引用，不改工作区
        fetched = run_git(repo, "fetch", args.remote, branch)
        if fetched.returncode != 0:
            print(f"ERROR: 无法拉取远端状态（认证或网络问题）：{text(fetched.stderr)}")
            return 1

        ahead = run_git(repo, "rev-list", "--count", f"{remote_ref}..HEAD")
        if ahead.returncode != 0:
            print(f"ERROR: 无法计算待推提交：{text(ahead.stderr)}")
            return 1
        pending = int(text(ahead.stdout) or 0)

        behind = run_git(repo, "rev-list", "--count", f"HEAD..{remote_ref}")
        if behind.returncode == 0 and int(text(behind.stdout) or 0) > 0:
            n = text(behind.stdout)
            print(f"BLOCKED: 远端 {remote_ref} 比本地多 {n} 条提交（non-fast-forward），"
                  f"推送会被拒绝；未执行推送，请你决定先合并还是放弃推送")
            return 2

        if pending == 0:
            print(f"SKIP: {remote_ref} 已是最新，没有待推提交")
            return 0
    else:
        all_commits = run_git(repo, "rev-list", "--count", "HEAD")
        pending = int(text(all_commits.stdout) or 0) if all_commits.returncode == 0 else 0

    first_push = not remote_exists

    if not args.confirm:
        head_note = "远端尚无该分支，将首次推送并绑定 upstream（-u）" if first_push \
            else f"{remote_ref} 已存在，推送后仍绑定 upstream（-u）"
        print(f"PREVIEW: 可推送 {pending} 条到 {remote_ref}")
        print(f"  分支：{branch}（{head_note}）")
        print("  未加 --confirm，未执行推送。")
        return 0

    pushed = run_git(repo, "push", "-u", args.remote, branch)
    if pushed.returncode != 0:
        err = text(pushed.stderr) or text(pushed.stdout)
        lowered = err.lower()
        if "non-fast-forward" in lowered or "fetch first" in lowered or "rejected" in lowered:
            print(f"BLOCKED: 远端 {remote_ref} 拒绝了本次推送（non-fast-forward）；"
                  f"未执行 force，请你决定怎么处理")
            print(err)
            return 2
        print(f"ERROR: 推送失败：{err}")
        return 1

    print(f"OK: {remote_ref} 已推送 {pending} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
