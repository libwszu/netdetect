"""Build and package a portable Windows app from a clean source checkout."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile


EDITIONS = {
    "cn": {"spec": "深大校园网自动重连.spec", "built_name": "深大校园网自动重连.exe", "name": "SZU-Net-Monitor-CN", "language": "zh-CN"},
    "en": {"spec": "SZU-Net-Monitor.spec", "built_name": "SZU-Net-Monitor.exe", "name": "SZU-Net-Monitor-EN", "language": "en"},
}


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def create_assets(root, executable, output, edition, tag, source_sha):
    """Package only an explicit allowlist; never read the personal configuration."""
    root, executable, output = Path(root), Path(executable), Path(output)
    settings = EDITIONS[edition]
    sample = json.loads((root / "net_monitor_config.example.json").read_text(encoding="utf-8-sig"))
    if sample.get("username") or sample.get("password"):
        raise ValueError("The configuration example must not contain credentials")
    if not re.fullmatch(r"v\d+\.\d+(?:\.\d+)?(?:[-.][A-Za-z0-9]+)*", tag):
        raise ValueError("Use a version tag such as v4.7 or v4.7.1")
    if not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise ValueError("A full source commit SHA is required")
    output.mkdir(parents=True, exist_ok=True)
    app = output / (settings["name"] + ".exe")
    shutil.copy2(executable, app)
    archive = output / (settings["name"] + "-Windows-x64.zip")
    if edition == "cn":
        quick_start = """深大校园网自动重连工具（中文免安装版）

1. 将 ZIP 完整解压到自己的可写文件夹，不要直接在压缩包中运行。
2. 双击 SZU-Net-Monitor-CN.exe。无需安装 Python。
3. 打开“账号设置”，填写自己的校园网账号和密码，保存设置。
4. 点击“启动监控”；程序只适用于对应的深大校园网。

账号密码以明文保存在程序旁的 net_monitor_config.json 中，日志也保存在本机。
请勿共享自己的配置和日志。发布包只含空白配置示例，不含任何个人账号。
适用系统：Windows 10 / 11，64 位。
"""
        notes = """Windows 64 位免安装版，无需 Python。

- 下载 `SZU-Net-Monitor-CN.exe` 后双击运行，或下载便携 ZIP 并完整解压。
- 首次使用请在“账号设置”中填写自己的校园网账号和密码。
- 适用于深大对应 SRUN 校园网。账号配置和日志保存在自己的电脑上。
- `SHA256SUMS.txt` 提供文件校验，`BUILD-INFO.json` 记录源码版本和构建信息。

构建自公开源码；已运行离线测试和打包启动检查，未执行真实校园网认证。
"""
    else:
        quick_start = """SZU Network Monitor — portable English edition

1. Extract the ZIP into a folder you can write to. Do not run inside the ZIP.
2. Double-click SZU-Net-Monitor-EN.exe. Python is not required.
3. In Settings, enter your own campus account and password, then save.
4. Select Start monitoring. This app is for the configured SZU campus network.

Credentials are stored in plain text in net_monitor_config.json next to the app.
Logs also stay on your device. Do not share your personal configuration or logs.
This package contains only an empty configuration example, not personal accounts.
System requirements: 64-bit Windows 10 / 11.
"""
        notes = """Portable Windows 64-bit app. Python is not required.

- Download `SZU-Net-Monitor-EN.exe` and run it, or extract the portable ZIP first.
- On first launch, enter your own campus account and password in Settings.
- For the configured SZU SRUN campus network; settings and logs stay on your device.
- `SHA256SUMS.txt` provides checksums; `BUILD-INFO.json` records source and build details.

Built from public source. Offline tests and packaged startup checks are performed; live campus authentication is not exercised.
"""
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as package:
        prefix = settings["name"] + "/"
        package.write(app, prefix + app.name)
        package.write(root / "LICENSE", prefix + "LICENSE")
        package.writestr(prefix + "QUICK_START.txt", quick_start.encode("utf-8-sig"))
        package.writestr(prefix + "net_monitor_config.example.json", json.dumps(sample, indent=2).encode("utf-8"))
    metadata = {
        "version": tag, "edition": settings["language"], "platform": "Windows x64",
        "source_commit": source_sha, "python": platform.python_version(),
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in (app, archive)],
    }
    info = output / "BUILD-INFO.json"
    info.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    checksums = output / "SHA256SUMS.txt"
    checksums.write_text("".join(sha256(path) + "  " + path.name + "\n" for path in (app, archive, info)), encoding="utf-8")
    (output / "RELEASE_NOTES.md").write_text(notes, encoding="utf-8")
    return (app, archive, info, checksums)


def validate_binary(executable, edition):
    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

    reader = CArchiveReader(str(executable))
    names = set(reader.toc)
    assert "LICENSE" in names, "The license must be embedded in the executable"
    assert any(name.lower().startswith("python") and name.lower().endswith(".dll") for name in names), "Python runtime DLL is missing"
    forbidden = {"net_monitor_config.json", "net_monitor.log"}
    assert not any(Path(name.replace("\\", "/")).name in forbidden or ".workbuddy" in name for name in names)
    pyz = next(name for name in names if name.upper().endswith(".PYZ"))
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "modules.pyz"
        path.write_bytes(reader.extract(pyz))
        modules = set(ZlibArchiveReader(str(path)).toc)
        assert {"tkinter", "requests", "i18n"} <= modules, "A required application module is missing"
        assert ("translations" in modules) == (edition == "en"), "Wrong language bundle"
        clean_env = {key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "PYTHONHOME")}
        clean_env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        result = subprocess.run([str(executable), "--help"], cwd=folder, env=clean_env, capture_output=True, timeout=60)
        assert result.returncode == 0, "Packaged startup failed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", required=True, choices=EDITIONS)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    if sys.platform != "win32" or struct.calcsize("P") != 8:
        raise SystemExit("Build on 64-bit Windows with 64-bit Python")
    root = Path(__file__).resolve().parents[1]
    settings = EDITIONS[args.edition]
    subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", settings["spec"]], cwd=root, check=True)
    executable = root / "dist" / settings["built_name"]
    validate_binary(executable, args.edition)
    assets = create_assets(root, executable, root / "release-assets", args.edition, args.tag, args.source_sha)
    print(json.dumps({"packaged_startup": "passed", "assets": [path.name for path in assets]}))


if __name__ == "__main__":
    main()
