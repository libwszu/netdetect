"""Shared language selection for the GUI, CLI and background monitor."""

import argparse
import sys

from translations import EN_MESSAGES


LANGUAGES = ("en", "zh-CN")
LANGUAGE_LABELS = {"en": "English", "zh-CN": "简体中文"}
_language = "en"


def resolve_language(argument=None, saved=None):
    """An explicit CLI language wins over a saved preference."""
    language = argument if argument is not None else saved
    return language if language in LANGUAGES else "en"


def set_language(language):
    global _language
    _language = resolve_language(language)
    return _language


def get_language():
    return _language


def ui_font():
    return "Microsoft YaHei UI" if _language == "zh-CN" else "Segoe UI"


def tr(message, *values):
    """Translate a complete message before inserting dynamic values."""
    text = EN_MESSAGES.get(message, message) if _language == "en" else message
    return text.format(*values) if values else text


def parse_language_args(argv=None, *, daemon=False, description="SZU Network Monitor"):
    # Redirected Windows terminals may use an encoding without emoji support.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--lang", choices=LANGUAGES, help="Interface language; overrides the saved preference")
    if daemon:
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--daemon", action="store_true", help="Run the background monitor without a window")
        mode.add_argument("--daemon-once", action="store_true", help="Run one real network check without a window")
    return parser.parse_args(argv)
