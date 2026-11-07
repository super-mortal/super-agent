#!/usr/bin/env python3
"""检查提交身份是否被 IDE / Agent 覆盖，并记录用户选择。

问题背景：部分 IDE 会在进程级注入身份环境变量，例如 Trae 注入
`GIT_COMMITTER_NAME=trae-solo-agent`。它不改 `.gitconfig`，所以
`git config user.name` 看着正常，但实际 commit 的作者是工具名。

检测方式（不做关键词猜测）：

    配置身份  = git config user.name / user.email
    实际身份  = git var GIT_COMMITTER_IDENT（受环境变量影响）
    两者不一致  = 有东西在覆盖，需要问用户

用法：

    # 检查：加载技能时跑一次，首行即结论
    python {skill_root}/scripts/git_identity.py --repo {project_root}

    # 记录用户的持久选择（A = ide，C = user）；B「仅本轮」不写这里
    python {skill_root}/scripts/git_identity.py --set user
    python {skill_root}/scripts/git_identity.py --set ide

    # 清空已记录的偏好，下次重新询问
    python {skill_root}/scripts/git_identity.py --clear

输出（首行即结论）：

    OK: 无需询问（{原因}）      没有冲突，或已有记录
    ASK: 提交身份存在冲突       需要询问用户三选一
    SKIP: 不是 git 仓库

偏好文件：`{project_root}/.super-agent/preferences.json` —— **项目级**，不写用户主目录。
同一台机器上不同项目可以有不同选择；想换回来用 `--clear` 清掉记录。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

IDENTITY_ENV_VARS = (
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
)
MODES = ("user", "ide")


def now_iso() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    except Exception:
        return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def prefs_path(repo: Path) -> Path:
    """偏好文件按项目存放，不用全局家目录。"""
    base = os.environ.get("SUPER_AGENT_HOME")
    root = Path(base) if base else repo / ".super-agent"
    return root / "preferences.json"


def load_prefs(repo: Path) -> dict:
    path = prefs_path(repo)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_prefs(repo: Path, data: dict) -> Path:
    path = prefs_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def saved_mode(repo: Path) -> dict:
    """返回本项目已记录的 identity 偏好（可能为空 dict）。"""
    return load_prefs(repo).get("identity") or {}


def run_git(repo: Path, *args: str, clean: bool = False) -> subprocess.CompletedProcess:
    """执行 git。clean=True 时剔除身份环境变量（检测时要保留它们）。"""
    env = dict(os.environ)
    env["GIT_PAGER"] = "cat"
    if clean:
        for key in IDENTITY_ENV_VARS:
            env.pop(key, None)
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, env=env)


def text(raw: bytes) -> str:
    return raw.decode("utf-8", "replace").strip()


def parse_ident(raw: str) -> tuple[str, str]:
    """把 "Name <email> 1699... +0800" 解析成 (name, email)。"""
    match = re.match(r"^(?P<name>.*?)\s*<(?P<email>[^>]*)>", raw or "")
    if not match:
        return "", ""
    return match.group("name").strip(), match.group("email").strip()


def detect(repo: Path) -> dict:
    """对比配置身份与真实生效身份，判断是否需要询问。"""
    cfg_name = text(run_git(repo, "config", "--get", "user.name").stdout)
    cfg_email = text(run_git(repo, "config", "--get", "user.email").stdout)

    var = run_git(repo, "var", "GIT_COMMITTER_IDENT")
    eff_name, eff_email = parse_ident(text(var.stdout)) if var.returncode == 0 else ("", "")

    conflict = bool(eff_name or eff_email) and (eff_name, eff_email) != (cfg_name, cfg_email)
    return {
        "config": {"name": cfg_name, "email": cfg_email},
        "effective": {"name": eff_name, "email": eff_email},
        "conflict": conflict,
        "env_overrides": {k: v for k, v in ((k, os.environ.get(k)) for k in IDENTITY_ENV_VARS) if v},
        "policy": saved_mode(repo),
        "prefs_path": str(prefs_path(repo)),
    }


def describe(info: dict) -> list[str]:
    cfg, eff = info["config"], info["effective"]
    lines = [
        f"  配置身份：{cfg['name']} <{cfg['email']}>" if cfg["name"] else "  配置身份：未设置",
        f"  实际提交：{eff['name']} <{eff['email']}>" if eff["name"] else "  实际提交：无法解析",
    ]
    envs = info.get("env_overrides") or {}
    if envs:
        lines.append("  环境变量：" + "，".join(f"{k}={v}" for k, v in envs.items()))
    policy = info.get("policy") or {}
    if policy:
        lines.append(f"  已记录偏好：{policy.get('mode')}（{policy.get('decided_at', '未知时间')}）")
    else:
        lines.append("  已记录偏好：无")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="检查提交身份是否被 IDE / Agent 覆盖")
    parser.add_argument("--repo", default=".", help="目标项目根目录，默认当前目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--set", choices=MODES, help="记录本项目偏好：user=以后都用我的，ide=用 IDE 默认")
    parser.add_argument("--clear", action="store_true", help="清除已记录的偏好")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    path = prefs_path(repo)

    if args.clear:
        data = load_prefs(repo)
        data.pop("identity", None)
        if data:
            save_prefs(repo, data)
        elif path.is_file():
            path.unlink()  # 没有其他偏好时直接删掉文件，不留空壳
        print(f"OK: 已清除本项目的身份偏好（{path}）")
        return 0

    if args.set:
        if run_git(repo, "rev-parse", "--git-dir").returncode != 0:
            print("SKIP: 当前目录不是 git 仓库，没有可记录的身份策略")
            return 0
        info = detect(repo)
        data = load_prefs(repo)
        data["identity"] = {
            "mode": args.set,
            "silent": True,
            "decided_at": now_iso(),
            "detected": info.get("effective", {}).get("name", ""),
            "config": info.get("config", {}).get("name", ""),
        }
        save_prefs(repo, data)
        print(f"OK: 已记录本项目身份偏好 = {args.set}（本项目下次不再询问）")
        print(f"  {path}")
        return 0

    if run_git(repo, "rev-parse", "--git-dir").returncode != 0:
        print("SKIP: 当前目录不是 git 仓库")
        return 0

    info = detect(repo)

    if args.json:
        info["need_ask"] = bool(info["conflict"]) and not info["policy"]
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0

    policy = info["policy"]
    if policy:
        mode = policy.get("mode")
        label = "用你自己的身份" if mode == "user" else "用 IDE 默认身份"
        print(f"OK: 已记录偏好 = {mode}（{label}），跳过询问")
        for line in describe(info):
            print(line)
        return 0

    if not info["conflict"]:
        print("OK: 无需询问（配置身份与实际提交身份一致）")
        for line in describe(info):
            print(line)
        return 0

    print("ASK: 提交身份存在冲突，需要询问用户")
    for line in describe(info):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
