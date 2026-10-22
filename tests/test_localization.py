"""Offline checks for a standalone edition; all accounts and network responses are synthetic."""

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

ROOT = Path(__file__).resolve().parents[1]
IS_ENGLISH = i18n.DEFAULT_LANGUAGE == "en"
EMPTY_CONFIG = {
    "username": "", "password": "", "check_interval": 600,
    "auto_login_enabled": True, "reconnect_retries": 3,
    "reconnect_wait_seconds": 20, "prevent_sleep_enabled": True,
}


def contains_chinese(text):
    return any("\u4e00" <= char <= "\u9fff" for char in text)


class EditionTests(unittest.TestCase):
    def test_fixed_language_and_translation_formatting(self):
        self.assertEqual(i18n.tr("检测间隔"), "Check interval" if IS_ENGLISH else "检测间隔")
        original = "❌ Token异常: {0}"
        value = '{"error":"test-only"}'
        self.assertTrue(i18n.tr(original, value).endswith(value))
        if IS_ENGLISH:
            from translations import EN_MESSAGES
            formatter = string.Formatter()
            for chinese, english in EN_MESSAGES.items():
                fields = lambda text: sorted(field for _, field, _, _ in formatter.parse(text) if field is not None)
                self.assertEqual(fields(chinese), fields(english), chinese)
                self.assertFalse(contains_chinese(english), chinese)

    def test_english_catalog_covers_all_literal_application_messages(self):
        if not IS_ENGLISH:
            self.assertFalse((ROOT / "translations.py").exists())
            return
        from translations import EN_MESSAGES
        for filename in ("net_monitor_gui.py", "net_monitor.py", "setup_config.py", "i18n.py"):
            tree = ast.parse((ROOT / filename).read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        self.assertIn(node.args[0].value, EN_MESSAGES, (filename, node.lineno))

    def test_help_matches_edition_and_has_no_language_switch(self):
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as result:
            gui.main(["--help"])
        self.assertEqual(result.exception.code, 0)
        self.assertNotIn("--lang", output.getvalue())
        self.assertIn("--daemon", output.getvalue())
        self.assertEqual(contains_chinese(output.getvalue()), not IS_ENGLISH)

    def test_legacy_configuration_preserves_credentials_and_custom_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config.json"
            original = {"username": "test-account", "password": "synthetic-test-password", "custom_field": 42,
                        "language": "zh-CN" if IS_ENGLISH else "en"}
            config.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(gui, "CONFIG_FILE", str(config)):
                loaded = gui.load_config()
                self.assertEqual(loaded["username"], original["username"])
                self.assertTrue(gui.save_config(loaded))
                saved = json.loads(config.read_text(encoding="utf-8"))
                self.assertEqual(saved["password"], original["password"])
                self.assertEqual(saved["custom_field"], 42)
            self.assertEqual(i18n.tr("检测间隔"), "Check interval" if IS_ENGLISH else "检测间隔")

    def test_setup_wizard_hides_password_and_validates_numeric_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config.json"
            output = io.StringIO()
            with patch.object(setup_config, "CONFIG_FILE", str(config)), \
                 patch("builtins.input", side_effect=["test-account", "y", "1", "0", "1"]), \
                 patch.object(setup_config.getpass, "getpass", return_value="synthetic-test-password"), \
                 redirect_stdout(output):
                self.assertEqual(setup_config.main([]), 0)
            saved = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual((saved["check_interval"], saved["reconnect_retries"], saved["reconnect_wait_seconds"]), (30, 1, 5))
            self.assertNotIn("synthetic-test-password", output.getvalue())
            self.assertEqual(contains_chinese(output.getvalue()), not IS_ENGLISH)

    def test_srun_gui_and_cli_payloads_remain_identical(self):
        payloads = []
        for module, builder in ((gui, "build_params"), (cli, "build_login_params")):
            client = module.SZUSrunClient.__new__(module.SZUSrunClient)
            client.token = "0123456789abcdef"
            client.auth_username = "test-account@hlw"
            client.password = "synthetic-test-password"
            client.ip = "192.0.2.1"
            with patch.object(module.time, "time", return_value=1234567890):
                payloads.append(getattr(client, builder)())
        self.assertEqual(payloads[0], payloads[1])
        self.assertEqual(payloads[0]["ac_id"], "12")

    def test_daemon_ignores_old_language_preference(self):
        config = {**EMPTY_CONFIG, "language": "zh-CN" if IS_ENGLISH else "en", "prevent_sleep_enabled": False}
        with patch.object(gui, "load_config", return_value=config), \
             patch.object(gui, "_clear_daemon_stop_signal"), \
             patch.object(gui, "_daemon_stop_requested", return_value=False), \
             patch.object(gui, "check_network", return_value=True), \
             patch.object(gui, "write_log") as logger:
            self.assertEqual(gui.run_daemon_monitor(run_once=True), 0)
            text = " ".join(call.args[0] for call in logger.call_args_list)
            self.assertEqual(contains_chinese(text), not IS_ENGLISH)
        expected = "SZU Net Monitor Background EN" if IS_ENGLISH else "SZU Net Monitor Background"
        self.assertEqual(gui.BACKGROUND_TASK_NAME, expected)
        self.assertEqual(gui.RUN_VALUE_NAME, expected)

    def test_cli_uses_edition_language_without_authenticating(self):
        output = io.StringIO()
        config = {**EMPTY_CONFIG, "language": "zh-CN" if IS_ENGLISH else "en", "prevent_sleep_enabled": False}
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli, "check_network", side_effect=KeyboardInterrupt), \
             patch.object(cli, "log", side_effect=print), \
             redirect_stdout(output):
            cli.main([])
        self.assertEqual(contains_chinese(output.getvalue()), not IS_ENGLISH)


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.patches = ExitStack()
        self.patches.enter_context(patch.object(gui, "load_config", return_value={**EMPTY_CONFIG, "language": "zh-CN" if IS_ENGLISH else "en"}))
        self.patches.enter_context(patch.object(gui, "get_local_ip", return_value="192.0.2.1"))
        self.patches.enter_context(patch.object(gui, "detect_vpn", return_value=(False, [])))
        self.patches.enter_context(patch.object(gui, "get_background_task_install_mode", return_value="none"))
        self.patches.enter_context(patch.object(gui.NetMonitorApp, "_load_existing_log"))
        try:
            self.app = gui.NetMonitorApp()
            self.app.withdraw()
        except gui.tk.TclError as error:
            self.patches.close()
            self.skipTest(str(error))

    def tearDown(self):
        if hasattr(self, "app"):
            self.app.update_idletasks()
            self.app.destroy()
        self.patches.close()

    def test_gui_uses_fixed_language_despite_opposite_legacy_preference(self):
        self.assertEqual(self.app.title(), "SZU Network Monitor v4.7" if IS_ENGLISH else "深大校园网自动重连工具 v4.7")
        self.assertNotIn("language_var", self.app.__dict__)
        if IS_ENGLISH:
            todo = list(self.app.winfo_children())
            while todo:
                widget = todo.pop()
                todo.extend(widget.winfo_children())
                if "text" in widget.keys():
                    self.assertFalse(contains_chinese(str(widget.cget("text"))))
        with patch.object(gui.messagebox, "showwarning") as warning, patch.object(gui, "SZUSrunClient") as client:
            self.app._manual_login()
            self.assertEqual(contains_chinese(warning.call_args.args[1]), not IS_ENGLISH)
            client.assert_not_called()

    def test_save_keeps_current_account_without_language_selection(self):
        self.app.entry_user.insert(0, "test-account")
        self.app.entry_pwd.insert(0, "synthetic-test-password")
        with patch.object(gui, "save_config", return_value=True) as save, patch.object(gui.messagebox, "showinfo"):
            self.app._save_settings()
            saved = save.call_args.args[0]
            self.assertEqual(saved["username"], "test-account")
            self.assertEqual(saved["password"], "synthetic-test-password")


if __name__ == "__main__":
    unittest.main()
