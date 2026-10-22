"""Interactive campus account setup for this standalone edition."""

import getpass
import json
import os

from i18n import parse_cli_args, tr

CONFIG_FILE = "net_monitor_config.json"


def _prompt_int(message, default, minimum):
    value = input(tr(message, default)).strip()
    if not value:
        return default
    try:
        return max(minimum, int(value))
    except ValueError:
        print(tr("输入无效，保留默认值。"))
        return default


def main(argv=None):
    parse_cli_args(argv, description=tr("深大校园网账号配置向导"))
    cfg = {
        "username": "",
        "password": "",
        "check_interval": 600,
        "auto_login_enabled": True,
        "reconnect_retries": 3,
        "reconnect_wait_seconds": 20,
        "prevent_sleep_enabled": True,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as handle:
                cfg.update(json.load(handle))
        except (OSError, ValueError, TypeError):
            print(tr("无法读取现有配置，请先备份并检查该文件。"))
            return 1

    print("\n" + "=" * 64)
    print(tr("深大校园网账号配置向导"))
    print("=" * 64)
    print(tr("按回车保留已有设置。密码输入不会显示。"))
    print(tr("账号密码将以明文保存在本机配置文件中，请勿共享该文件。"))

    old_user = cfg.get("username", "")
    hint = old_user[:3] + "***" if old_user else tr("必填")
    username = input(tr("校园网账号（学号或教职工号）[{0}]: ", hint)).strip()
    cfg["username"] = username or old_user
    password = getpass.getpass(tr("校园网密码（回车保留原密码）: "))
    cfg["password"] = password or cfg.get("password", "")

    default_auto = "y" if cfg.get("auto_login_enabled", True) else "n"
    auto = input(tr("断网时自动登录？(y/n) [{0}]: ", default_auto)).strip().lower()
    if auto in ("y", "yes", "n", "no"):
        cfg["auto_login_enabled"] = auto in ("y", "yes")
    cfg["check_interval"] = _prompt_int("检测间隔（秒）[{0}]: ", cfg.get("check_interval", 600), 30)
    cfg["reconnect_retries"] = _prompt_int("登录尝试次数 [{0}]: ", cfg.get("reconnect_retries", 3), 1)
    cfg["reconnect_wait_seconds"] = _prompt_int("重试等待秒数 [{0}]: ", cfg.get("reconnect_wait_seconds", 20), 5)

    with open(CONFIG_FILE, "w", encoding="utf-8") as handle:
        json.dump(cfg, handle, ensure_ascii=False, indent=2)
    print(tr("配置已保存到:\n") + os.path.abspath(CONFIG_FILE))
    print(tr("密码已保存在本机，不会在此显示。"))
    print(tr("启动图形界面: python net_monitor_gui.py"))
    print(tr("启动命令行监控: python net_monitor.py"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
