#!/usr/bin/env python3
"""grep_judgement.py — 从测试报告 grep 提取 PASS/FAIL 判定。

Usage:
    python grep_judgement.py <REPORT_PATH>
    python grep_judgement.py <REPORT_DIR>           # 批量处理目录下所有 .md
    python grep_judgement.py <REPORT_PATH> --strict # 只认最新测试段的独立判定标题行

退出码：
    0  表示至少找到一个 PASS
    1  表示所有报告都是 FAIL 或无判定
    2  表示文件/目录不存在
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 普通模式允许判定标题出现在任意位置
JUDGEMENT_RE = re.compile(r"###\s*判定[：:]\s*(PASS|FAIL)", re.IGNORECASE)
# 严格模式只接受内容为 `### 判定：PASS/FAIL` 的独立标题行
STRICT_JUDGEMENT_RE = re.compile(
    r"###[ \t]*判定[：:][ \t]*(PASS|FAIL)[ \t]*",
    re.IGNORECASE,
)
FENCE_RE = re.compile(r"^[ \t]*(```|~~~)")
# 匹配 tester 报告中的轮次标题，例如 `## 第 2 次测试（重测）`
ROUND_HEADING_RE = re.compile(
    r"^##[ \t]*第[ \t]+(\d+)[ \t]*次[^\r\n]*$",
    re.IGNORECASE,
)


def extract_strict_sections(text: str) -> list[list[str]]:
    """按测试轮次提取严格判定，返回每个测试段内的判定列表。"""
    sections: list[list[str]] = []
    current_section: list[str] | None = None
    in_fence = False

    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        stripped = line.strip()
        if ROUND_HEADING_RE.fullmatch(stripped):
            current_section = []
            sections.append(current_section)
            continue

        match = STRICT_JUDGEMENT_RE.fullmatch(stripped)
        if match and current_section is not None:
            current_section.append(match.group(1).upper())

    return sections


def extract_judgements(text: str, strict: bool) -> list[str]:
    """提取测试判定；严格模式只认测试段内的独立判定标题行。"""
    if not strict:
        return [match.upper() for match in JUDGEMENT_RE.findall(text)]

    return [judgement for section in extract_strict_sections(text) for judgement in section]


def extract_from_file(path: Path, strict: bool) -> dict:
    """从单个测试报告提取判定信息。"""
    text = path.read_text(encoding="utf-8")
    if strict:
        sections = extract_strict_sections(text)
        matches = [judgement for section in sections for judgement in section]
        final = sections[-1][-1] if sections and sections[-1] else None
        round_count = len(sections)
    else:
        matches = extract_judgements(text, strict=False)
        final = matches[-1] if matches else None
        round_count = len(matches)

    if final is None:
        return {
            "path": str(path),
            "status": "UNKNOWN",
            "rounds": matches,
            "round_count": round_count,
        }

    return {
        "path": str(path),
        "status": final,
        "rounds": matches,
        "round_count": round_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="从测试报告 grep 提取 PASS/FAIL"
    )
    parser.add_argument(
        "target",
        type=Path,
        help="测试报告路径或目录",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式（只认最新测试段的独立 ### 判定：PASS/FAIL，忽略代码块）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出",
    )
    args = parser.parse_args()

    target: Path = args.target
    if not target.exists():
        print(f"ERROR: 路径不存在: {target}", file=sys.stderr)
        return 2

    files: list[Path]
    if target.is_file():
        files = [target]
    else:
        files = sorted(target.glob("*.md"))

    if not files:
        print(f"ERROR: 没有找到 .md 报告文件: {target}", file=sys.stderr)
        return 2

    results = [extract_from_file(f, args.strict) for f in files]

    if args.json:
        import json
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            mark = {
                "PASS": "[OK]",
                "FAIL": "[ERR]",
                "UNKNOWN": "?",
            }.get(r["status"], "?")
            rounds_count = r.get("round_count", 0)
            rounds_str = f" ({rounds_count} 轮)" if rounds_count > 0 else ""
            print(f"{mark} {r['status']:<8} {r['path']}{rounds_str}")

    # 退出码：至少一个 PASS 返回 0，否则 1
    if any(r["status"] == "PASS" for r in results):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
