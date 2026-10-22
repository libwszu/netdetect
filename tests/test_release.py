"""Portable package checks that use a dummy binary and never read personal files."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


spec = importlib.util.spec_from_file_location("build_release", Path(__file__).resolve().parents[1] / "tools" / "build_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class PortablePackageTests(unittest.TestCase):
    def test_package_contains_only_allowed_files_and_checksum_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "app.exe").write_bytes(b"MZ-test-binary")
            (root / "LICENSE").write_text("Test license", encoding="utf-8")
            (root / "net_monitor_config.example.json").write_text(json.dumps({"username": "", "password": ""}), encoding="utf-8")
            (root / "net_monitor_config.json").write_text('{"password":"do-not-package"}', encoding="utf-8")
            (root / "net_monitor.log").write_text("private log", encoding="utf-8")
            assets = release.create_assets(root, root / "app.exe", root / "out", "en", "v4.7", "a" * 40)
            with zipfile.ZipFile(assets[1]) as package:
                self.assertEqual(set(package.namelist()), {
                    "SZU-Net-Monitor-EN/SZU-Net-Monitor-EN.exe", "SZU-Net-Monitor-EN/LICENSE",
                    "SZU-Net-Monitor-EN/QUICK_START.txt", "SZU-Net-Monitor-EN/net_monitor_config.example.json",
                })
                self.assertEqual(package.read("SZU-Net-Monitor-EN/SZU-Net-Monitor-EN.exe"), assets[0].read_bytes())
            metadata = json.loads(assets[2].read_text(encoding="utf-8"))
            self.assertEqual(metadata["files"][0]["sha256"], release.sha256(assets[0]))
            for line in assets[3].read_text(encoding="utf-8").splitlines():
                digest, name = line.split("  ")
                self.assertEqual(digest, release.sha256(root / "out" / name))

    def test_nonempty_account_example_is_rejected_before_packaging(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "net_monitor_config.example.json").write_text('{"username":"synthetic-account","password":""}', encoding="utf-8")
            with self.assertRaises(ValueError):
                release.create_assets(root, root / "app.exe", root / "out", "cn", "v4.7", "a" * 40)


if __name__ == "__main__":
    unittest.main()
