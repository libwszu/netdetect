"""
深大校园网配置向导 - 一键设置学号密码
用法: python setup_config.py
"""

import json
import os

CONFIG_FILE = "net_monitor_config.json"

def main():
    print("\n" + "=" * 58)
    print("  🎓 深大校园网自动重连工具 - 配置向导")
    print("=" * 58)

    # 加载已有配置
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"\n📂 已加载现有配置文件。")
    else:
        cfg = {
            "login_url": "https://net.szu.edu.cn",
            "auto_login_enabled": True,
            "reconnect_retries": 3,
            "reconnect_wait_seconds": 20,
            "prevent_sleep_enabled": True,
        }
        print(f"\n📝 将创建新配置文件。")

    print(f"\n请输入深大校园网认证信息（直接回车保留默认值）：\n")

    # 用户名（学号/教职工号）
    default_user = cfg.get("username", "")
    user = input(f"  学号/教职工号 [{default_user or '(必填)'}]: ").strip()
    cfg["username"] = user if user else default_user

    # 密码（统一身份认证密码）
    default_pwd = cfg.get("password", "")
    pwd_hint = "*" * len(default_pwd) if default_pwd else "(必填)"
    pwd = input(f"  统一身份认证密码 [{pwd_hint}]: ").strip()
    cfg["password"] = pwd if pwd else default_pwd

    # 自动登录开关
    auto = cfg.get("auto_login_enabled", True)
    auto_str = input(
        f"  启用断网自动重连? (y/n) [{'y' if auto else 'n'}]: "
    ).strip().lower()
    if auto_str in ("n", "no"):
        cfg["auto_login_enabled"] = False
    elif auto_str in ("y", "yes", ""):
        cfg["auto_login_enabled"] = True

    # 高级参数
    print(f"\n--- 高级选项 ---")
    try:
        retry_str = input(
            f"  断网后重连尝试次数 [{cfg.get('reconnect_retries', 3)}]: "
        ).strip()
        if retry_str:
            cfg["reconnect_retries"] = int(retry_str)

        retry_wait = input(
            f"  每次重连间隔秒数 [{cfg.get('reconnect_wait_seconds', 20)}]: "
        ).strip()
        if retry_wait:
            cfg["reconnect_wait_seconds"] = int(retry_wait)
    except ValueError:
        print("  ⚠️ 输入无效，使用默认值")

    # 保存
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    # 显示结果（脱敏）
    show_cfg = cfg.copy()
    if show_cfg.get("password"):
        show_cfg["password"] = "*" * len(show_cfg["password"])

    print(f"\n{'='*58}")
    print(f"  ✅ 配置已保存到: {CONFIG_FILE}")
    print(f"{'='*58}")
    print(f"\n当前配置：")
    print(f"  认证地址: {show_cfg['login_url']}")
    print(f"  学号:     {show_cfg['username']}")
    print(f"  密码:     {show_cfg['password']}")
    print(f"  自动重连: {'开启' if show_cfg['auto_login_enabled'] else '关闭'}")
    print(f"  重试次数: {show_cfg['reconnect_retries']}次")
    print(f"\n现在运行以下命令启动监控：")
    print(f"  python net_monitor.py\n")


if __name__ == "__main__":
    main()
