#!/usr/bin/env python3
"""estimate_context.py — 估算子智能体 prompt 的 token 数。

主智能体在组装子智能体 prompt 时应该调用此脚本检查总 token 数，
避免超过子智能体的上下文窗口。

Usage:
    python estimate_context.py <FILE_OR_DIR> [<FILE_OR_DIR> ...]
    python estimate_context.py --prompt "{prompt_string}"
    echo "{prompt}" | python estimate_context.py --stdin

估算规则（粗略）：
- 英文 / 数字 / 标点：约 4 字符 = 1 token
- 中文 / 日文 / 韩文：约 1.5 字符 = 1 token
- 实际 GPT/Claude tokenizer 更精确，但粗估够用

退出码：始终 0（仅估算）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# 中日韩 Unicode 范围（CJK 基本 + 扩展 A）
CJK_RE = re.compile(r"[\u3000-\u9fff\uf900-\ufaff]")


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数。

    规则：
    - CJK 字符：每 1.5 字符 ≈ 1 token（向上取整）
    - 其他字符：每 4 字符 ≈ 1 token（向上取整）
    """
    cjk_chars = len(CJK_RE.findall(text))
    other_chars = len(text) - cjk_chars
    cjk_tokens = (cjk_chars * 2 + 2) // 3  # ceil(cjk / 1.5)
    other_tokens = (other_chars + 3) // 4    # ceil(other / 4)
    return cjk_tokens + other_tokens


def estimate_file(path: Path) -> tuple[int, int, int]:
    """返回 (字符数, token 数, 路径)。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    return len(text), estimate_tokens(text), 0  # 0 是占位


def main() -> int:
    parser = argparse.ArgumentParser(description="估算 token 数")
    parser.add_argument(
        "targets",
        nargs="*",
        type=Path,
        help="文件或目录路径",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="直接传 prompt 字符串",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="从 stdin 读取",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=8000,
        help="token 预算（默认 8000，超过会警告）",
    )
    args = parser.parse_args()

    items: list[tuple[str, int, int]] = []  # (label, chars, tokens)

    if args.prompt is not None:
        text = args.prompt
        items.append(("--prompt", len(text), estimate_tokens(text)))
    elif args.stdin:
        text = sys.stdin.read()
        if text:
            items.append(("--stdin", len(text), estimate_tokens(text)))
    elif args.targets:
        for t in args.targets:
            if t.is_file():
                chars, tokens, _ = estimate_file(t)
                items.append((str(t), chars, tokens))
            elif t.is_dir():
                for f in sorted(t.rglob("*.md")):
                    chars, tokens, _ = estimate_file(f)
                    items.append((str(f), chars, tokens))
                for f in sorted(t.rglob("*.py")):
                    chars, tokens, _ = estimate_file(f)
                    items.append((str(f), chars, tokens))
            else:
                print(f"WARN: {t} 不存在或不是文件/目录", file=sys.stderr)
    else:
        print("ERROR: 必须提供 targets / --prompt / --stdin 其中之一", file=sys.stderr)
        return 1

    if not items:
        print("无内容可估算")
        return 0

    total_chars = sum(c for _, c, _ in items)
    total_tokens = sum(t for _, _, t in items)

    print(f"{'PATH':<60} {'CHARS':>8} {'TOKENS':>8}")
    print("-" * 80)
    for label, chars, tokens in items:
        # 截断过长的路径显示
        display = label if len(label) <= 60 else "..." + label[-57:]
        print(f"{display:<60} {chars:>8} {tokens:>8}")
    print("-" * 80)
    print(f"{'TOTAL':<60} {total_chars:>8} {total_tokens:>8}")
    print()

    if total_tokens > args.budget:
        print(
            f"[WARN]  警告：总 token {total_tokens} 超过预算 {args.budget}",
            file=sys.stderr,
        )
        print(
            "   建议：精简必读文件列表、把大文件改成路径不传内容",
            file=sys.stderr,
        )
        return 0
    print(f"[OK] 在预算 {args.budget} 内（使用率 {total_tokens * 100 // args.budget}%）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
