#!/usr/bin/env python3
"""在 dev-spec.md 的错误码登记表中分配并登记新的错误码。

Usage:
    python register_error_code.py <DEV_SPEC> \
        --prefix APP \
        --module AUTH \
        --http 401 \
        --meaning "用户未登录" \
        --location "middleware/auth.py:42"
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


CODE_RE = re.compile(r"^(?P<prefix>[A-Z][A-Z0-9]*)-(?P<module>[A-Z]{2,6})-(?P<number>\d{4})$")
SECTION_RE = re.compile(r"^#{2,3}\s*错误码登记\s*$")
TABLE_HEADER_RE = re.compile(r"^\|\s*错误码\s*\|\s*模块\s*\|\s*HTTP\s*\|\s*含义\s*\|\s*抛出位置\s*\|\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\|(?:\s*:?-+:?\s*\|){5}$")
PLACEHOLDER_VALUES = {"...", "…", "待填"}


def clean_cell(value: str) -> str:
    return value.strip().strip("`")


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [clean_cell(cell) for cell in stripped[1:-1].split("|")]


def find_table(text: str) -> tuple[list[str], int, list[tuple[int, str]]]:
    lines = text.splitlines()
    heading_index = next((i for i, line in enumerate(lines) if SECTION_RE.match(line)), None)
    if heading_index is None:
        raise ValueError("dev-spec.md 中未找到“错误码登记”章节")

    header_index = next(
        (i for i in range(heading_index + 1, len(lines)) if TABLE_HEADER_RE.match(lines[i])),
        None,
    )
    if header_index is None:
        raise ValueError("“错误码登记”章节中未找到标准表头")

    separator_index = header_index + 1
    if separator_index >= len(lines) or not TABLE_SEPARATOR_RE.match(lines[separator_index]):
        raise ValueError("“错误码登记”表头后缺少 Markdown 分隔行")

    existing: list[tuple[int, str]] = []
    last_table_row = separator_index
    insertion_index = separator_index + 1
    for index in range(separator_index + 1, len(lines)):
        cells = split_table_row(lines[index])
        if not cells:
            break
        last_table_row = index
        code = cells[0] if cells else ""
        if PLACEHOLDER_VALUES.intersection(cells):
            insertion_index = index
            break
        if CODE_RE.fullmatch(code):
            existing.append((index, code))
    else:
        insertion_index = last_table_row + 1

    return lines, insertion_index, existing


def next_error_code(existing: list[tuple[int, str]], prefix: str, module: str) -> str:
    used: set[int] = set()
    for _, code in existing:
        match = CODE_RE.fullmatch(code)
        if match and match.group("prefix") == prefix and match.group("module") == module:
            used.add(int(match.group("number")))

    number = 1
    while number in used:
        number += 1
    if number > 9999:
        raise ValueError(f"{prefix}-{module} 的 4 位错误码已用尽")
    return f"{prefix}-{module}-{number:04d}"


def atomic_write(path: Path, content: str) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="登记新的项目错误码")
    parser.add_argument("dev_spec", type=Path, help="dev-spec.md 路径")
    parser.add_argument("--prefix", required=True, help="错误码前缀，例如 APP")
    parser.add_argument("--module", required=True, help="模块代码，2~6 个大写字母")
    parser.add_argument("--http", required=True, help="HTTP 状态码，例如 401")
    parser.add_argument("--meaning", required=True, help="用户可读的错误含义")
    parser.add_argument("--location", default="待填", help="抛出位置，例如 middleware/auth.py:42")
    parser.add_argument("--code", help="显式指定错误码；不传时自动分配下一个编号")
    args = parser.parse_args()

    dev_spec = args.dev_spec.resolve()
    if not dev_spec.is_file():
        print(f"ERROR: dev-spec.md 不存在: {dev_spec}", file=sys.stderr)
        return 2

    prefix = args.prefix.strip().upper()
    module = args.module.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]*", prefix):
        print("ERROR: prefix 必须以字母开头，且只能包含大写字母和数字", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[A-Z]{2,6}", module):
        print("ERROR: module 必须是 2~6 个大写字母", file=sys.stderr)
        return 2
    if not re.fullmatch(r"\d{3}", str(args.http).strip()):
        print("ERROR: http 必须是三位数字状态码", file=sys.stderr)
        return 2

    try:
        lines, insertion_index, existing = find_table(dev_spec.read_text(encoding="utf-8"))
        if args.code:
            code = args.code.strip().upper()
            code_match = CODE_RE.fullmatch(code)
            if not code_match:
                raise ValueError("--code 必须符合 {PREFIX}-{MODULE}-{NNNN} 格式")
            if code_match.group("prefix") != prefix or code_match.group("module") != module:
                raise ValueError("--code 的前缀和模块必须与 --prefix / --module 一致")
        else:
            code = next_error_code(existing, prefix, module)

        if any(existing_code == code for _, existing_code in existing):
            raise ValueError(f"错误码已存在: {code}")

        row = f"| {code} | {module.lower()} | {args.http} | {args.meaning.strip()} | {args.location.strip()} |"
        lines.insert(insertion_index, row)
        atomic_write(dev_spec, "\n".join(lines) + "\n")
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"REGISTERED_ERROR_CODE={code}")
    print(f"DEV_SPEC={dev_spec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
