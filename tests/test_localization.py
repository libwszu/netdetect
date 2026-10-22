"""Offline localization and protocol regression checks; no real credentials are used."""

import ast
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import string
import tempfile
import unittest
from unittest.mock import patch

import i18n
import net_monitor as cli
import net_monitor_gui as gui
import setup_config
from translations import EN_MESSAGES


ROOT = Path(__file__).resolve().parents[1]
EMPTY_CONFIG = {
    "language": "en", "username": "", "password": "", "check_interval": 600,
    "auto_login_enabled": True, "reconnect_retries": 3,
    "reconnect_wait_seconds": 20, "prevent_sleep_enabled": True,
}


def contains_chinese(text):
    return any("\u4e00" <= char <= "\u9fff" for char in text)


class LocalizationTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_catalog_has_matching_format_fields_and_no_untranslated_english(self):
        formatter = string.Formatter()
        for original, english in EN_MESSAGES.items():
            with self.subTest(message=original):
                fields = lambda text: sorted(field for _, field, _, _ in formatter.parse(text) if field is not None)
                self.assertEqual(fields(original), fields(english))
                self.assertFalse(contains_chinese(english))

    def test_every_literal_message_in_the_app_has_an_english_translation(self):
        for filename in ("net_monitor_gui.py", "net_monitor.py", "setup_config.py"):
            tree = ast.parse((ROOT / filename).read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        self.assertIn(node.args[0].value, EN_MESSAGES, (filename, node.lineno))

    def test_explicit_language_overrides_saved_preference(self):
        self.assertEqual(i18n.resolve_language("en", "zh-CN"), "en")
        self.assertEqual(i18n.resolve_language(None, "zh-CN"), "zh-CN")
        self.assertEqual(i18n.resolve_language(None, "invalid"), "en")
        i18n.set_language("en")
        self.assertEqual(i18n.tr("检测间隔"), "Check interval")
        i18n.set_language("zh-CN")
        self.assertEqual(i18n.tr("检测间隔"), "检测间隔")

    def test_interpolated_server_messages_are_not_reformatted(self):
        i18n.set_language("en")
        server_message = '{"error": "test-only"}'
        self.assertEqual(i18n.tr("❌ Token异常: {0}", server_message), "❌ Authentication challenge error: " + server_message)

    def test_legacy_config_fields_and_credentials_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config.json"
            original = {"username": "test-account", "password": "synthetic-test-password", "custom_field": 42}
            config.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(gui, "CONFIG_FILE", str(config)):
                loaded = gui.load_config()
                self.assertEqual(loaded["language"], "en")
                self.assertEqual(loaded["username"], original["username"])
                loaded["language"] = "zh-CN"
                self.assertTrue(gui.save_config(loaded))
                saved = json.loads(config.read_text(encoding="utf-8"))
                self.assertEqual(saved["password"], original["password"])
                self.assertEqual(saved["custom_field"], 42)

    def test_wizard_hides_password_and_saves_language_and_valid_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config.json"
            output = io.StringIO()
            with patch.object(setup_config, "CONFIG_FILE", str(config)), \
                 patch("builtins.input", side_effect=["test-account", "y", "1", "0", "1"]), \
                 patch.object(setup_config.getpass, "getpass", return_value="synthetic-test-password"), \
                 redirect_stdout(output):
                self.assertEqual(setup_config.main(["--lang", "en"]), 0)
            saved = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(saved["language"], "en")
            self.assertEqual((saved["check_interval"], saved["reconnect_retries"], saved["reconnect_wait_seconds"]), (30, 1, 5))
            self.assertNotIn("synthetic-test-password", output.getvalue())
            self.assertFalse(contains_chinese(output.getvalue()))

    def test_srun_payload_is_identical_in_both_languages_and_both_clients(self):
        payloads = []
        for language in ("en", "zh-CN"):
            i18n.set_language(language)
            for module, builder in ((gui, "build_params"), (cli, "build_login_params")):
                client = module.SZUSrunClient.__new__(module.SZUSrunClient)
                client.token = "0123456789abcdef"
                client.auth_username = "test-account@hlw"
                client.password = "synthetic-test-password"
                client.ip = "192.0.2.1"
                with patch.object(module.time, "time", return_value=1234567890):
                    payloads.append(getattr(client, builder)())
        self.assertTrue(all(payload == payloads[0] for payload in payloads))
        self.assertEqual(payloads[0]["ac_id"], "12")

    def test_daemon_uses_saved_language_and_cli_override_without_real_requests(self):
        for argument, expected in ((None, "zh-CN"), ("en", "en")):
            config = {**EMPTY_CONFIG, "language": "zh-CN", "prevent_sleep_enabled": False}
            with patch.object(gui, "load_config", return_value=config), \
                 patch.object(gui, "_clear_daemon_stop_signal"), \
                 patch.object(gui, "_daemon_stop_requested", return_value=False), \
                 patch.object(gui, "check_network", return_value=True), \
                 patch.object(gui, "write_log") as logger:
                self.assertEqual(gui.run_daemon_monitor(run_once=True, language=argument), 0)
                self.assertEqual(i18n.get_language(), expected)
                text = " ".join(call.args[0] for call in logger.call_args_list)
                self.assertEqual(contains_chinese(text), expected == "zh-CN")

    def test_cli_uses_english_without_authenticating(self):
        output = io.StringIO()
        config = {**EMPTY_CONFIG, "language": "zh-CN", "prevent_sleep_enabled": False}
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli, "check_network", side_effect=KeyboardInterrupt), \
             patch.object(cli, "log", side_effect=print), \
             redirect_stdout(output):
            cli.main(["--lang", "en"])
        self.assertIn("SZU Network Monitor", output.getvalue())
        self.assertFalse(contains_chinese(output.getvalue()))


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.patches = ExitStack()
        self.patches.enter_context(patch.object(gui, "load_config", return_value=dict(EMPTY_CONFIG)))
        self.patches.enter_context(patch.object(gui, "get_local_ip", return_value="192.0.2.1"))
        self.patches.enter_context(patch.object(gui, "detect_vpn", return_value=(False, [])))
        self.patches.enter_context(patch.object(gui, "get_background_task_install_mode", return_value="none"))
        self.patches.enter_context(patch.object(gui.NetMonitorApp, "_load_existing_log"))
        try:
            self.app = gui.NetMonitorApp(language="en")
            self.app.withdraw()
        except gui.tk.TclError as error:
            self.patches.close()
            self.skipTest(str(error))

    def tearDown(self):
        if hasattr(self, "app"):
            self.app.update_idletasks()
            self.app.destroy()
        self.patches.close()
        i18n.set_language("en")

    def test_english_widgets_and_missing_credentials_dialog(self):
        self.assertEqual(self.app.title(), "SZU Network Monitor v4.7")
        self.assertEqual(self.app.language_var.get(), "English")
        todo = list(self.app.winfo_children())
        while todo:
            widget = todo.pop()
            todo.extend(widget.winfo_children())
            if "text" in widget.keys():
                self.assertFalse(contains_chinese(str(widget.cget("text"))), str(widget))
        with patch.object(gui.messagebox, "showwarning") as warning, patch.object(gui, "SZUSrunClient") as client:
            self.app._manual_login()
            self.assertIn("Settings", warning.call_args.args[1])
            client.assert_not_called()

    def test_saving_language_keeps_credentials_and_requires_restart(self):
        self.app.entry_user.insert(0, "test-account")
        self.app.entry_pwd.insert(0, "synthetic-test-password")
        self.app.language_var.set(i18n.LANGUAGE_LABELS["zh-CN"])
        with patch.object(gui, "save_config", return_value=True) as save, patch.object(gui.messagebox, "showinfo") as info:
            self.app._save_settings()
            saved = save.call_args.args[0]
            self.assertEqual(saved["language"], "zh-CN")
            self.assertEqual(saved["password"], "synthetic-test-password")
            self.assertIn("Restart", info.call_args.args[1])
            self.assertEqual(i18n.get_language(), "en")

    def test_chinese_gui_remains_available(self):
        self.app.update_idletasks()
        self.app.destroy()
        self.app = gui.NetMonitorApp(language="zh-CN")
        self.app.withdraw()
        self.assertIn("深大", self.app.title())
        self.assertEqual(self.app.language_var.get(), "简体中文")
        self.assertEqual(self.app.start_btn.cget("text"), "▶ 启动监控")


if __name__ == "__main__":
    unittest.main()
