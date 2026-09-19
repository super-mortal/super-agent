#!/usr/bin/env python3
"""输出统一的北京时间。

默认输出日志格式：
    YYYY-MM-DD HH.MM

使用 --iso 输出带时区的 ISO 8601 时间：
    YYYY-MM-DDTHH:MM:SS+08:00
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def now_beijing() -> datetime:
    """返回北京时间；系统缺少 tzdata 时退回固定 UTC+8。"""
    try:
        return datetime.now(ZoneInfo("Asia/Shanghai"))
    except ZoneInfoNotFoundError:
        return datetime.now(timezone(timedelta(hours=8)))


def main() -> None:
    parser = argparse.ArgumentParser(description="输出 super-agent 统一时间")
    parser.add_argument(
        "--iso",
        action="store_true",
        help="输出带时区的 ISO 8601 时间，用于 run.json 等元数据",
    )
    args = parser.parse_args()

    current = now_beijing()
    if args.iso:
        print(current.isoformat(timespec="seconds"))
    else:
        print(current.strftime("%Y-%m-%d %H.%M"))


if __name__ == "__main__":
    main()
