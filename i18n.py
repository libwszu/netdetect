"""Fixed-language presentation helpers for this standalone edition."""

import argparse
import sys

DEFAULT_LANGUAGE = 'zh-CN'


def ui_font():
    return 'Microsoft YaHei UI'


def tr(message, *values):
    text = message
    return text.format(*values) if values else text


def parse_cli_args(argv=None, *, daemon=False, description=None):
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=description or tr("深大校园网断网自动重连工具"), add_help=False)
    parser._optionals.title = tr("选项")
    parser.add_argument("-h", "--help", action="help", help=tr("显示帮助信息并退出"))
    if daemon:
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--daemon", action="store_true", help=tr("在后台运行，不显示窗口"))
        mode.add_argument("--daemon-once", action="store_true", help=tr("仅执行一次实际网络检测"))
    return parser.parse_args(argv)
