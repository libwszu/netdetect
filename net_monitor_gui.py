"""
深大校园网断网自动重连工具 - GUI版 v4.7
=========================================
带图形界面的桌面应用程序
- 可视化配置：学号、密码、检测间隔等
- 一键启动/停止监控
- 实时日志面板 + 状态指示灯
- 断网自动通过SRUN API认证重连
- 支持系统托盘最小化（可选）

作者: WorkBuddy
用法: 双击运行 python net_monitor_gui.py
"""

import sys
from i18n import tr, parse_cli_args, ui_font
import os
import time
import datetime
import json
import socket
import hashlib
import hmac
import base64
import ctypes
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import timedelta

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# ── 尝试导入 requests ──
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# ── 资源路径辅助（PyInstaller 单文件兼容）──
def resource_path(relative_path: str) -> str:
    """获取资源的绝对路径，兼容开发模式和 PyInstaller 单文件模式。"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ── 深大 Logo（64x64 PNG, base64 内嵌）──
_LOGO_B64 = (
    "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"
    "nUzPQSvCAAAAAASUVORK5CYII="
)


def _get_logo_photoimage() -> tk.PhotoImage | None:
    """返回深大 logo 的 PhotoImage，失败返回 None。"""
    try:
        import io
        raw = base64.b64decode(_LOGO_B64)
        return tk.PhotoImage(data=raw)
    except Exception:
        return None


# ── 窗口图标数据 ──
ICON_DATA = _LOGO_B64


# ══════════════════════════════════════════════════
#   常量 & 配置文件路径
# ══════════════════════════════════════════════════

# ── 应用目录（兼容 PyInstaller 单文件模式）──
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后，用 exe 所在目录
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(APP_DIR, "net_monitor_config.json")
LOG_FILE = os.path.join(APP_DIR, "net_monitor.log")
DAEMON_STOP_FILE = os.path.join(APP_DIR, "net_monitor_daemon.stop")
DAEMON_PID_FILE = os.path.join(APP_DIR, "net_monitor_daemon.pid")

PING_TARGET = "223.5.5.5"
HTTP_TEST_URL = "http://www.baidu.com"
PING_TIMEOUT = 5
HTTP_TIMEOUT = 8

SRUN_BASE_URL = "http://net.szu.edu.cn"
SRUN_CALLBACK = "jQueryCallback"
SRUN_AC_ID = "12"
SRUN_N = "200"
SRUN_TYPE = "1"
SRUN_ENC = "srun_bx1"
SRUN_DEFAULT_DOMAIN = "@hlw"
B64_ALPHA = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"
BACKGROUND_TASK_NAME = "SZU Net Monitor Background"
RUN_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = BACKGROUND_TASK_NAME
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

# 颜色常量
C_OK = "#2ECC71"       # 绿色-在线
C_ERR = "#E74C3C"      # 红色-断网
C_WARN = "#F39C12"     # 橙色-警告
C_INFO = "#3498DB"     # 蓝色-信息
C_BG = "#1E1E2E"       # 深色背景
C_BG2 = "#2D2D3F"      # 次级背景
C_TEXT = "#E0E0E0"     # 浅色文字
C_TEXT_DIM = "#888888" # 暗淡文字
C_ACCENT = "#6C5CE7"   # 紫色强调
C_BORDER = "#3D3D5C"


# ══════════════════════════════════════════════════
#   配置管理
# ══════════════════════════════════════════════════

def load_config():
    default = {
        "username": "",
        "password": "",
        "check_interval": 600,
        "auto_login_enabled": True,
        "reconnect_retries": 3,
        "reconnect_wait_seconds": 20,
        "prevent_sleep_enabled": True,
    }
    if not os.path.exists(CONFIG_FILE):
        save_config(default)
        return default
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in default.items():
            if k not in cfg:
                cfg[k] = v
        cfg["check_interval"] = _safe_int(cfg.get("check_interval"), 600, 30)
        cfg["reconnect_retries"] = _safe_int(cfg.get("reconnect_retries"), 3, 1)
        cfg["reconnect_wait_seconds"] = _safe_int(cfg.get("reconnect_wait_seconds"), 20, 5)
        cfg["prevent_sleep_enabled"] = bool(cfg.get("prevent_sleep_enabled", True))
        return cfg
    except Exception:
        return default


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(tr('[ERROR] 保存配置失败: {0}', e))
        return False


def _safe_int(value, default, minimum):
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return default


def _run_text_command(args, timeout=10):
    kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["encoding"] = "mbcs"
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return subprocess.run(args, **kwargs)


# ══════════════════════════════════════════════════
#   工具函数
# ══════════════════════════════════════════════════

def get_timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")


def _resolve_sru_ip():
    """解析 SRUN 服务器的 IP，用于绕过 VPN 获取真实校园网 IP"""
    try:
        return socket.gethostbyname("net.szu.edu.cn")
    except Exception:
        return None


def get_local_ip():
    """
    获取本机真实校园网IP（VPN感知版本）。
    策略：
    1. 优先直接连接 SRUN 服务器 net.szu.edu.cn（绕过VPN走物理网卡）
    2. 用 client_ip 兜底（从 get_challenge 返回值获取）
    3. 最后 fallback 到传统方式
    """
    # 方式1：直接连 SRUN 服务器（校园网内直连，不受 VPN 影响）
    srun_ip = _resolve_sru_ip()
    if srun_ip:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((srun_ip, 80))
            ip = s.getsockname()[0]
            s.close()
            # 如果得到的是校园网IP段（10.x、172.16-31.x），大概率正确
            if ip.startswith("10.") or (ip.startswith("172.") and 16 <= int(ip.split(".")[1]) <= 31):
                return ip
            # 如果得到的是VPN IP段（如 10.8.x.x 是 OpenVPN 常见段），尝试下一个方式
            if ip.startswith("10.8.") or ip.startswith("10.9.") or ip.startswith("192.168."):
                pass  # 疑似VPN IP，继续尝试
            else:
                return ip  # 非典型 VPN IP，先用着
        except Exception:
            pass

    # 方式2：传统方式连阿里DNS
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((PING_TARGET, 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def detect_vpn():
    """
    检测是否可能开启了 VPN（通过扫描网络接口名称）。
    返回 (is_vpn: bool, vpn_names: list[str])
    """
    vpn_keywords = [
        "vpn", "tap", "tun", "openvpn", "wireguard", "wg",
        "nord", "express", "surfshark", "proton",
        "clash", "v2ray", "ssr", "shadowsocks", "trojan",
        "hysteria", "sing-box", "virtual", "ppp", "l2tp", "sstp",
    ]
    suspected = []
    try:
        result = _run_text_command(["ipconfig"], timeout=10)
        for line in result.stdout.split("\n"):
            line_lower = line.lower()
            for kw in vpn_keywords:
                if kw in line_lower and "adapter" in line_lower:
                    name = line.strip().rstrip(":")
                    if name not in suspected:
                        suspected.append(name)
                    break
    except Exception:
        pass

    # 也检查路由表中是否有 0.0.0.0 指向非标准网关
    try:
        result = _run_text_command(["route", "print", "0.0.0.0"], timeout=10)
        # 如果路由表有多条默认路由，可能 VPN 在工作
        default_routes = [l for l in result.stdout.split("\n") if "0.0.0.0" in l and "On-link" not in l]
        if len(default_routes) > 2:  # 正常只有1-2条（IPv4+IPv6）
            suspected.append(tr('多默认路由(可能VPN)'))
    except Exception:
        pass

    return (len(suspected) > 0, suspected)


# ══════════════════════════════════════════════════
#   VPN 绕过：物理网卡绑定 + SRUN IP 缓存
# ══════════════════════════════════════════════════

_SRUN_IP_CACHE = None  # 缓存的 SRUN 服务器 IP


def _get_physical_interface_ip():
    """
    找到非 VPN 的物理网卡 IP。
    解析 ipconfig 输出，排除 VPN 适配器，返回第一个物理网卡 IP。
    """
    vpn_kw = ["vpn", "tap", "tun", "openvpn", "wireguard", "wg",
              "clash", "v2ray", "shadow", "trojan", "hysteria", "sing-box",
              "virtual", "ppp", "l2tp", "sstp", "nord", "express", "surfshark",
              "proton", "hyper-v", "wsl", "docker", "vmware", "virtualbox"]
    try:
        result = _run_text_command(["ipconfig"], timeout=10)
        text = result.stdout
        sections = text.split("\n\n")
        for sec in sections:
            sec_lower = sec.lower()
            # 跳过 VPN/虚拟适配器
            if any(kw in sec_lower for kw in vpn_kw):
                continue
            # 找 IPv4 地址
            for line in sec.split("\n"):
                if "IPv4" in line or "IP Address" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        ip = parts[-1].strip()
                        # 必须是私有IP段
                        if ip.startswith(("10.", "172.", "192.168.")):
                            return ip
    except Exception:
        pass
    return None


def _get_srun_ip():
    """解析并缓存 SRUN 服务器 IP（绕过 VPN DNS 的关键）"""
    global _SRUN_IP_CACHE
    if _SRUN_IP_CACHE:
        return _SRUN_IP_CACHE

    host = "net.szu.edu.cn"
    # 方式1：直接用系统DNS解析
    try:
        _SRUN_IP_CACHE = socket.gethostbyname(host)
        return _SRUN_IP_CACHE
    except Exception:
        pass

    # 方式2：用 nslookup 强制查询（避免 VPN DNS 干扰）
    try:
        result = _run_text_command(["nslookup", host], timeout=10)
        in_answer = False
        for line in result.stdout.split("\n"):
            stripped = line.strip()
            lower = stripped.lower()
            if host in lower or lower.startswith("name:"):
                in_answer = True
                continue
            if in_answer and "Address" in stripped and "#" not in stripped and "." in stripped:
                parts = line.strip().split(":")
                if len(parts) >= 2:
                    ip = parts[-1].strip()
                    if ip.count(".") == 3:
                        _SRUN_IP_CACHE = ip
                        return ip
    except Exception:
        pass

    # 方式3：硬编码兜底（SRUN 服务器 IP 极少变动）
    _SRUN_IP_CACHE = "172.31.63.36"
    return _SRUN_IP_CACHE


def _create_bound_adapter(source_ip):
    """
    创建一个绑定到指定源IP的 HTTPAdapter。
    所有通过这个adapter发出的HTTP请求都会从指定网卡出去。
    """
    class BoundHTTPAdapter(requests.adapters.HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            kwargs["source_address"] = (source_ip, 0)
            super().init_poolmanager(*args, **kwargs)
    return BoundHTTPAdapter()


def _make_vpn_resistant_session():
    """
    创建用于 SRUN 认证的 requests.Session。
    认证接口必须直连校园网，不应走系统/环境代理；同时不绑定本地源 IP，
    避免 VPN/TUN 模式下 Windows 路由与手工 source_address 冲突。
    """
    session = requests.Session()
    session.trust_env = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    })
    session._vpn_direct = True
    return session


def beep(freq=1000, dur=300):
    try:
        import winsound
        winsound.Beep(freq, dur)
    except ImportError:
        pass


def write_log(msg):
    """写入日志文件"""
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def set_system_sleep_prevention(enabled=True):
    """
    允许锁屏/息屏，但阻止 Windows 进入睡眠。
    普通桌面程序锁屏后会继续运行；真正会让监控暂停的是睡眠/现代待机。
    """
    if os.name != "nt":
        return False
    try:
        flags = ES_CONTINUOUS
        if enabled:
            flags |= ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        result = ctypes.windll.kernel32.SetThreadExecutionState(flags)
        if not result and enabled:
            result = ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED
            )
        return result != 0
    except Exception:
        return False


def sleep_interruptible(seconds, stop_event=None, stop_checker=None):
    """按小步长睡眠，便于后台监控及时响应停止信号。"""
    remaining = float(seconds)
    while remaining > 0:
        if stop_event is not None and stop_event.is_set():
            return False
        if stop_checker is not None and stop_checker():
            return False
        step = min(1.0, remaining)
        time.sleep(step)
        remaining -= step
    return True


def _clear_daemon_stop_signal():
    try:
        if os.path.exists(DAEMON_STOP_FILE):
            os.remove(DAEMON_STOP_FILE)
    except Exception:
        pass


def _request_daemon_stop():
    try:
        with open(DAEMON_STOP_FILE, "w", encoding="utf-8") as f:
            f.write(datetime.datetime.now().isoformat())
        return True
    except Exception:
        return False


def _daemon_stop_requested():
    return os.path.exists(DAEMON_STOP_FILE)


def _write_daemon_pid():
    try:
        with open(DAEMON_PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def _read_daemon_pid():
    try:
        with open(DAEMON_PID_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _is_process_running(pid):
    if not pid or pid <= 0:
        return False
    try:
        if os.name == "nt":
            handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, int(pid))
            if not handle:
                return False
            try:
                return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) == 0x00000102
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _is_daemon_process_running():
    return _is_process_running(_read_daemon_pid())


def _clear_daemon_pid():
    pid = _read_daemon_pid()
    if pid is not None and pid != os.getpid() and _is_process_running(pid):
        return
    try:
        if os.path.exists(DAEMON_PID_FILE):
            os.remove(DAEMON_PID_FILE)
    except Exception:
        pass


def _daemon_argv():
    if getattr(sys, "frozen", False):
        return [sys.executable, "--daemon"]
    return [sys.executable, os.path.abspath(__file__), "--daemon"]


def _daemon_command():
    return subprocess.list2cmdline(_daemon_argv())


def _subprocess_message(result):
    parts = []
    for text in (result.stdout, result.stderr):
        if text:
            stripped = text.strip()
            if stripped:
                parts.append(stripped)
    return "\n".join(parts) or tr('退出码 {0}', result.returncode)


def _run_schtasks(args, timeout=20):
    return _run_text_command(["schtasks", *args], timeout=timeout)


def _is_scheduled_task_installed():
    try:
        result = _run_schtasks(["/Query", "/TN", BACKGROUND_TASK_NAME], timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def _read_startup_entry():
    if os.name != "nt":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_PATH, 0,
                            winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return str(value)
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _is_startup_entry_installed():
    return bool(_read_startup_entry())


def _install_startup_entry():
    try:
        import winreg
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_REG_PATH, 0,
                                winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ,
                              _daemon_command())
        return True, tr('已写入当前用户启动项，无需管理员权限。')
    except Exception as e:
        return False, str(e)


def _delete_startup_entry():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_PATH, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
        return True, tr('已删除当前用户启动项。')
    except FileNotFoundError:
        return True, tr('当前用户启动项不存在。')
    except OSError as e:
        return False, str(e)


def get_background_task_install_mode():
    if os.name != "nt":
        return "unsupported"
    if _is_scheduled_task_installed():
        return "scheduled_task"
    if _is_startup_entry_installed():
        return "startup_entry"
    return "none"


def is_background_task_installed():
    return get_background_task_install_mode() in ("scheduled_task", "startup_entry")


def install_background_task():
    """创建当前用户登录时自动启动的无界面后台监控任务。"""
    if os.name != "nt":
        return False, tr('后台守护仅支持 Windows。')
    task_msg = ""
    try:
        result = _run_schtasks(
            [
                "/Create",
                "/TN", BACKGROUND_TASK_NAME,
                "/TR", _daemon_command(),
                "/SC", "ONLOGON",
                "/RL", "LIMITED",
                "/F",
            ]
        )
        task_msg = _subprocess_message(result)
        if result.returncode == 0:
            return True, task_msg or tr('计划任务已安装。')
    except Exception as e:
        task_msg = str(e)

    ok, startup_msg = _install_startup_entry()
    if ok:
        return True, (
            tr('计划任务创建失败（{0}），已改用当前用户启动项安装，无需管理员权限。', task_msg)
        )
    return False, (
        tr('计划任务创建失败：{0}\n启动项写入失败：{1}', task_msg or tr('未知错误'), startup_msg or tr('未知错误'))
    )


def uninstall_background_task():
    if os.name != "nt":
        return False, tr('后台守护仅支持 Windows。')
    removed = []
    errors = []
    if _is_daemon_process_running():
        _request_daemon_stop()

    if _is_scheduled_task_installed():
        try:
            _run_schtasks(["/End", "/TN", BACKGROUND_TASK_NAME])
            result = _run_schtasks(["/Delete", "/TN", BACKGROUND_TASK_NAME, "/F"])
            if result.returncode == 0:
                removed.append(tr('计划任务'))
            else:
                errors.append(tr('计划任务删除失败：{0}', _subprocess_message(result)))
        except Exception as e:
            errors.append(tr('计划任务删除失败：{0}', e))

    if _is_startup_entry_installed():
        ok, msg = _delete_startup_entry()
        if ok:
            removed.append(tr('当前用户启动项'))
        else:
            errors.append(tr('启动项删除失败：{0}', msg))

    if errors:
        return False, "\n".join(errors)
    if removed:
        return True, tr('已卸载：') + ", ".join(removed)
    return True, tr('未发现已安装的后台守护。')


def run_background_task_now():
    if os.name != "nt":
        return False, tr('后台守护仅支持 Windows。')
    if _is_daemon_process_running():
        return True, tr('后台守护已在运行。')
    task_msg = ""
    if _is_scheduled_task_installed():
        try:
            result = _run_schtasks(["/Run", "/TN", BACKGROUND_TASK_NAME])
            task_msg = _subprocess_message(result)
            if result.returncode == 0:
                return True, task_msg
        except Exception as e:
            task_msg = str(e)

    try:
        _clear_daemon_stop_signal()
        subprocess.Popen(
            _daemon_argv(),
            cwd=APP_DIR,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
        )
    except Exception as e:
        if task_msg:
            return False, tr('计划任务启动失败：{0}\n直接启动失败：{1}', task_msg, e)
        return False, str(e)

    if task_msg:
        return True, tr('计划任务启动失败（{0}），已直接启动后台守护进程。', task_msg)
    return True, tr('后台守护进程已直接启动。')


# ══════════════════════════════════════════════════
#   网络检测
# ══════════════════════════════════════════════════

def check_network_ping():
    try:
        r = _run_text_command(
            ["ping", "-n", "1", "-w", str(PING_TIMEOUT * 1000), PING_TARGET],
            timeout=PING_TIMEOUT + 2,
        )
        return r.returncode == 0
    except Exception:
        return False


def check_network_http():
    """
    HTTP检测：校园网未认证时Captive Portal会把HTTP请求301跳转到认证页面。
    所以检测时要禁止跟随跳转，只认200或204，拒绝3xx跳转（说明被门户拦截了）。
    用微软的网络联通测试地址，正常互联网返回204，门户页面不会返回204。
    """
    # 方式1：严格模式（不跟随跳转），用于已知返回固定状态码的测试地址
    strict_tests = [
        ("http://www.msftconnecttest.com/connecttest.txt", 200),
        ("http://connect.rom.miui.com/generate_204", 204),
    ]
    for url, expected_code in strict_tests:
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT,
                                allow_redirects=False)
            if resp.status_code == expected_code:
                # 额外校验：msft测试会返回固定内容
                if "msftconnecttest" in url:
                    if "Microsoft Connect Test" in resp.text:
                        return True
                else:
                    return True
        except Exception:
            continue

    # 方式2：宽松模式（跟随跳转），验证最终页面内容
    # 有些测试URL会被302跳转（如baidu http→https），所以跟随跳转后验证内容
    content_tests = [
        ("http://www.baidu.com", "baidu"),
    ]
    for url, keyword in content_tests:
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT,
                                allow_redirects=True)
            if resp.status_code == 200 and keyword in resp.text.lower():
                return True
        except Exception:
            continue

    return False


def check_network():
    """
    综合检测：必须HTTP检测通过才算真正在线（能访问互联网）。
    单纯ping通不代表校园网已认证——Captive Portal会放行ICMP但拦截HTTP。
    """
    # VPN/代理常会屏蔽 ICMP，不能把 ping 失败当成断网依据。
    if check_network_http():
        return True
    return False


# ══════════════════════════════════════════════════
#   SRUN 加密算法
# ══════════════════════════════════════════════════

class _Str(str):
    def charCodeAt(self, i): return ord(self[i]) if len(self) > i else 0
    @classmethod
    def fromCharCode(cls, *c): return "".join(chr(x) for x in c)


def _s2l(s, p):
    c = len(s); v = []
    for i in range(0, c, 4):
        v.append(s.charCodeAt(i)|s.charCodeAt(i+1)<<8|s.charCodeAt(i+2)<<16|s.charCodeAt(i+3)<<24)
    if p: v.append(c)
    return v

def _l2s(a, u):
    d = len(a); c = (d-1)<<2
    if u:
        m = a[d-1]
        if m < c-3 or m > c: return None
        c = m
    out = []
    for val in a:
        out.extend([chr(val&0xFF), chr((val>>8)&0xFF), chr((val>>16)&0xFF), chr((val>>24)&0xFF)])
    r = "".join(out)
    return r[:c] if u else r

def xxtea_encrypt(plaintext, key):
    if not plaintext: return ""
    pt, ky = _Str(plaintext), _Str(key)
    v, k = _s2l(pt, True), _s2l(ky, False)
    while len(k) < 4: k.append(0)
    n = len(v)-1; z=v[n]; y=v[0]
    D = 0x9E3779B9; q = int(6+52/(n+1)); d = 0
    for _ in range(q):
        d = (d+D)&0xFFFFFFFF; e = (d>>2)&3
        for p in range(n):
            y = v[p+1]
            mx = ((z>>5)^(y<<2)) + (((y>>3)^(z<<4))^(d^y)) + (k[(p&3)^e]^z)
            z = v[p] = (v[p]+mx)&0xFFFFFFFF
        y=v[0]
        mx = ((z>>5)^(y<<2)) + (((y>>3)^(z<<4))^(d^y)) + (k[(n&3)^e]^z)
        z=v[n]=(v[n]+mx)&0xFFFFFFFF
    return _l2s(v, False)

def trans_base64(s, alpha=None):
    r = base64.b64encode(s.encode("latin-1")).decode()
    if alpha and len(alpha)==64:
        r = r.translate(str.maketrans(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/", alpha))
    return r

def hmac_md5(m, k): return hmac.new(k.encode(), m.encode(), hashlib.md5).hexdigest()
def sha1_hash(m): return hashlib.sha1(m.encode()).hexdigest()


def normalize_srun_username(username):
    username = (username or "").strip()
    if username and "@" not in username:
        return username + SRUN_DEFAULT_DOMAIN
    return username


# ══════════════════════════════════════════════════
#   SRUN 认证客户端
# ══════════════════════════════════════════════════

class SZUSrunClient:
    def __init__(self, username, password, log_callback=None):
        self.username = username
        self.auth_username = normalize_srun_username(username)
        self.password = password
        self.ip = None
        self.token = None
        self._log = log_callback or (lambda x: None)

        # ★ VPN 绕过：使用绑定物理网卡的 session + 解析 SRUN IP
        self._is_vpn, self._vpn_names = detect_vpn()
        self.session = _make_vpn_resistant_session()
        self._srun_ip = _get_srun_ip()  # 缓存 SRUN 服务器 IP
        self._use_direct_ip = self._is_vpn  # VPN 模式下直接用 IP

        if self._is_vpn:
            self._log(tr('⚠️ VPN已检测: {0}', ', '.join(self._vpn_names[:2])))
            self._log(tr('🔌 SRUN认证请求已关闭系统代理，避免被VPN代理接管'))
            self._log(tr('🌐 SRUN直连IP: {0}', self._srun_ip))

        if self.auth_username != self.username:
            self._log(tr('账号未带认证域，按官方默认补全为: {0}', self.auth_username))

    def _build_url(self, path):
        """构造 SRUN API URL，VPN模式下直接用IP（绕过DNS和路由）"""
        if self._use_direct_ip:
            # 直接用IP + Host头
            return f"http://{self._srun_ip}{path}"
        return f"{SRUN_BASE_URL}{path}"

    def _get_host_headers(self):
        """VPN 模式下需要手动设置 Host 头"""
        if self._use_direct_ip:
            return {"Host": "net.szu.edu.cn"}
        return {}

    def refresh_ip(self):
        """刷新本机IP（含 VPN 检测）"""
        self.ip = get_local_ip()
        if self._is_vpn:
            self._log(tr('⚠️ 检测到可能VPN: {0}', ', '.join(self._vpn_names[:2])))
            self._log(tr('   当前检测IP: {0}（将与SRUN服务器核对）', self.ip))
        else:
            self._log(tr('📡 本机IP: {0}', self.ip))

    def get_challenge(self):
        """步骤1：获取challenge token，并用服务器返回的 client_ip 修正本机IP"""
        if not self.ip: self.refresh_ip()
        url = self._build_url("/cgi-bin/get_challenge")

        # 如果首次IP可能被 VPN 污染，先试一下，让服务器告诉我们真实IP
        params = {"callback": SRUN_CALLBACK, "username": self.auth_username,
                  "ip": self.ip, "_": str(int(time.time()*1000))}
        self._log(tr('🔑 获取认证Token...'))
        try:
            resp = self.session.get(url, params=params, timeout=10,
                                     headers=self._get_host_headers())
            t = resp.text.strip()
            if not t:
                self._log(tr('❌ 服务器返回空（IP {0} 可能被拒绝）', self.ip))
                # 尝试不清IP直接请求
                params2 = {"callback": SRUN_CALLBACK, "username": self.auth_username,
                          "ip": "", "_": str(int(time.time()*1000))}
                resp = self.session.get(url, params=params2, timeout=10,
                                         headers=self._get_host_headers())
                t = resp.text.strip()
                if not t:
                    self._log(tr('❌ 服务器仍返回空，请检查VPN是否拦截了校园网流量'))
                    return False
            data = json.loads(t[t.index("(")+1:t.rindex(")")])
            if data.get("res") != "ok":
                self._log(tr('❌ Token获取失败: {0}', data))
                return False

            # ★ 关键：用服务器看到的 client_ip 覆盖本机IP（绕过VPN）
            client_ip = data.get("client_ip", "")
            old_ip = self.ip
            if client_ip and client_ip != old_ip:
                self.ip = client_ip
                self._log(tr('🔧 IP已修正: {0} → {1}（服务器真实IP）', old_ip, client_ip))

            self.token = data["challenge"]
            self._log(tr('✅ Token获取成功 (有效期{0}秒)', data.get('expire', '?')))
            return True
        except Exception as e:
            self._log(tr('❌ Token异常: {0}', e))
            return False

    def build_params(self):
        t, u, p, ip = self.token, self.auth_username, self.password, self.ip
        h = hmac_md5(p, t)
        enc_pwd = "{MD5}"+h
        info_j = json.dumps({"username":u,"password":p,"ip":ip,"acid":SRUN_AC_ID,"enc_ver":SRUN_ENC}, separators=(",",":"))
        enc_info = "{SRBX1}"+trans_base64(xxtea_encrypt(info_j,t), B64_ALPHA)
        chk_str = t+u+t+h+t+SRUN_AC_ID+t+ip+t+SRUN_N+t+SRUN_TYPE+t+enc_info
        return {
            "callback": SRUN_CALLBACK, "action": "login",
            "username": u, "password": enc_pwd,
            "os": "Windows", "name": "Windows", "nas_ip": "", "double_stack": 0,
            "chksum": sha1_hash(chk_str), "info": enc_info,
            "ac_id": SRUN_AC_ID, "ip": ip, "n": SRUN_N, "type": SRUN_TYPE,
            "captchaVal": "", "_": str(int(time.time()*1000)),
        }

    def do_login(self):
        if not self.token:
            if not self.get_challenge(): return {"success":False, "msg":tr('获取Token失败')}
        url = self._build_url("/cgi-bin/srun_portal")
        self._log(tr('🔐 提交认证请求...'))
        try:
            resp = self.session.get(url, params=self.build_params(), timeout=15,
                                     headers=self._get_host_headers())
            t = resp.text
            data = json.loads(t[t.index("(")+1:t.rindex(")")])
            res = data.get("res", "")
            emsg = data.get("error_msg", data.get("msg", ""))
            if res == "ok":
                self._log(tr('✅✅✅ 校园网认证成功！'))
                return {"success": True, "msg": tr('认证成功')}
            else:
                self._log(tr('❌ 认证失败: [{0}] {1}', res, emsg))
                return {"success": False, "msg": emsg}
        except Exception as e:
            self._log(tr('❌ 认证异常: {0}', e))
            return {"success": False, "msg": str(e)}

    def do_logout(self):
        """注销校园网（与官方JS _logoutNormal 一致，仅需4个参数）"""
        params = {
            "callback": SRUN_CALLBACK,
            "action": "logout",
            "username": self.auth_username,
            "ip": self.ip or get_local_ip(),
            "ac_id": SRUN_AC_ID,
        }
        url = self._build_url("/cgi-bin/srun_portal")
        try:
            resp = self.session.get(url, params=params, timeout=10,
                                     headers=self._get_host_headers())
            t = resp.text
            try:
                data = json.loads(t[t.index("(")+1:t.rindex(")")])
                res = data.get("res", "")
                emsg = data.get("error_msg", data.get("msg", ""))
                if res == "ok" or "logout" in str(data).lower():
                    self._log(tr('✅ 注销成功'))
                    return True
                else:
                    self._log(tr('❌ 注销失败: [{0}] {1}', res, emsg))
                    return False
            except (ValueError, Exception):
                self._log(tr('📤 已发送注销请求'))
                return True
        except Exception as e:
            self._log(tr('❌ 注销失败: {0}', e))
            return False


def _daemon_auto_reconnect(cfg, log_fn):
    max_tries = cfg.get("reconnect_retries", 3)
    wait_sec = cfg.get("reconnect_wait_seconds", 20)
    user = cfg.get("username", "")
    pwd = cfg.get("password", "")

    if not user or not pwd:
        log_fn(tr('⚠️ 后台守护无法自动重连：账号或密码为空'))
        return False

    log_fn("━" * 40)
    log_fn(tr('🔄 后台守护触发 SRUN 自动认证'))

    for attempt in range(1, max_tries + 1):
        log_fn(tr('▶ 第 {0}/{1} 次认证尝试...', attempt, max_tries))
        client = SZUSrunClient(user, pwd, log_fn)
        client.token = None
        client.refresh_ip()
        result = client.do_login()

        if result["success"]:
            log_fn(tr('⏳ 等待 {0}s 验证网络...', wait_sec))
            sleep_interruptible(wait_sec)
            if check_network():
                log_fn(tr('🎉 网络恢复！认证成功！'))
                return True
            log_fn(tr('⚠️ 认证成功但网络尚未通畅，继续重试'))
        elif attempt < max_tries:
            retry_wait = min(wait_sec, 15)
            log_fn(tr('⏳ 等 {0}s 后重试...', retry_wait))
            sleep_interruptible(retry_wait)

    log_fn(tr('😞 已尝试 {0} 次未恢复，请手动检查', max_tries))
    return False


def run_daemon_monitor(run_once=False):
    """无界面后台监控入口，供计划任务或命令行 --daemon 使用。"""
    _clear_daemon_stop_signal()
    if not run_once:
        if _is_daemon_process_running():
            write_log(tr('ℹ️ 后台守护已在运行，本次启动退出'))
            return 0
        _write_daemon_pid()
    write_log(tr('🚀 后台守护已启动'))
    consecutive_failures = 0
    sleep_prevention_active = False

    try:
        while True:
            if _daemon_stop_requested():
                write_log(tr('🛑 收到停止后台守护请求'))
                return 0

            cfg = load_config()
            should_prevent_sleep = cfg.get("prevent_sleep_enabled", True)
            if should_prevent_sleep != sleep_prevention_active:
                if set_system_sleep_prevention(should_prevent_sleep):
                    sleep_prevention_active = should_prevent_sleep
                    if should_prevent_sleep:
                        write_log(tr('🔒 已启用锁屏防睡眠：允许锁屏/息屏，但阻止系统睡眠'))
                    else:
                        write_log(tr('🔓 已关闭锁屏防睡眠'))

            is_online = check_network()
            if is_online:
                consecutive_failures = 0
                write_log(tr('✅ 网络正常'))
            else:
                consecutive_failures += 1
                write_log(tr('❌ 网络异常 (第{0}次)', consecutive_failures))
                if consecutive_failures >= 2 and cfg.get("auto_login_enabled", True):
                    if _daemon_auto_reconnect(cfg, write_log):
                        consecutive_failures = 0

            if run_once:
                return 0 if consecutive_failures == 0 else 2

            interval = cfg.get("check_interval", 600)
            next_time = datetime.datetime.now() + timedelta(seconds=interval)
            write_log(tr('💤 下次检测: {0}', next_time.strftime('%H:%M:%S')))
            if not sleep_interruptible(interval, stop_checker=_daemon_stop_requested):
                write_log(tr('🛑 收到停止后台守护请求'))
                return 0
    finally:
        if _daemon_stop_requested():
            _clear_daemon_stop_signal()
        if not run_once:
            _clear_daemon_pid()
        if sleep_prevention_active:
            set_system_sleep_prevention(False)
            write_log(tr('🔓 已恢复系统睡眠策略'))


# ══════════════════════════════════════════════════
#   GUI 主窗口
# ══════════════════════════════════════════════════

class NetMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.cfg = load_config()
        self.monitoring = False
        self.stop_event = threading.Event()
        self.consecutive_failures = 0
        self.total_checks = 0
        self.success_count = 0

        # 窗口设置
        self.title(tr('深大校园网自动重连工具 v4.7'))
        self.geometry("800x780")
        self.minsize(760, 680)
        self.configure(bg=C_BG)

        # 设置窗口图标（任务栏图标）
        try:
            ico_path = resource_path("assets/szu_logo.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
        except Exception:
            pass

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._setup_styles()

        # 构建UI
        self._build_ui()

        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ── 样式设置 ──

    def _setup_styles(self):
        """自定义ttk样式（深色主题）"""
        bg = C_BG; fg = C_TEXT; acc = C_ACCENT

        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg,
                             font=(ui_font(), 9))
        self.style.configure("Title.TLabel", font=(ui_font(), 12, "bold"),
                             foreground="#FFFFFF")
        self.style.configure("Status.TLabel", font=("Consolas", 11, "bold"))
        self.style.configure("Hint.TLabel", foreground=C_TEXT_DIM,
                             font=(ui_font(), 8))

        self.style.configure("TEntry", fieldbackground=C_BG2, foreground=fg,
                             insertcolor=fg, font=("Consolas", 10),
                             relief="flat", padding=(8, 6))

        self.style.configure("TSpinbox", arrowsize=12, font=(ui_font(), 9))

        self.style.configure("TButton", font=(ui_font(), 10, "bold"),
                             padding=(16, 8))
        self.style.configure("Start.TButton", background=C_OK)
        self.style.configure("Stop.TButton", background=C_ERR)
        self.style.configure("Accent.TButton", background=acc, foreground="#FFF")

        self.style.configure("TCheckbutton", background=bg, foreground=fg,
                             font=(ui_font(), 9))
        self.style.configure("TLabelframe", background=bg, foreground=fg)
        self.style.configure("TLabelframe.Label", background=bg, foreground=acc,
                             font=(ui_font(), 10, "bold"))

        self.style.configure("TNotebook", background=bg)
        self.style.configure("TNotebook.Tab", font=(ui_font(), 10),
                             padding=[16, 8])

    # ── 构建UI ──

    def _build_ui(self):
        root_frame = ttk.Frame(self)
        root_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=14)

        # === 标题栏 ===
        header = ttk.Frame(root_frame)
        header.pack(fill=tk.X, pady=(0, 12))

        # 深大 Logo 图标
        self.logo_img = _get_logo_photoimage()
        if self.logo_img:
            logo_label = tk.Label(header, image=self.logo_img, bg=C_BG)
            logo_label.pack(side=tk.LEFT, padx=(0, 8))

        title_l = ttk.Label(header, text=tr('深大校园网断网自动重连工具'),
                            style="Title.TLabel")
        title_l.pack(side=tk.LEFT)

        status_indicator = tk.Canvas(header, width=16, height=16,
                                      highlightthickness=0, bg=C_BG)
        status_indicator.pack(side=tk.RIGHT, padx=(0, 4))
        self.status_dot = status_indicator
        self._draw_status_dot("idle")

        status_text = ttk.Label(header, text=tr('未启动'), style="Status.TLabel",
                                foreground=C_TEXT_DIM)
        status_text.pack(side=tk.RIGHT)
        self.status_label = status_text

        # === 分页标签页 ===
        notebook = ttk.Notebook(root_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # --- 页签1：监控 ---
        monitor_frame = ttk.Frame(notebook)
        notebook.add(monitor_frame, text=tr('  📡 监控控制  '))

        self._build_monitor_tab(monitor_frame)

        # --- 页签2：设置 ---
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text=tr('  ⚙️ 账号设置  '))

        self._build_settings_tab(settings_frame)

        # --- 页签3：日志 ---
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text=tr('  📋 运行日志  '))

        self._build_log_tab(log_frame)

        # === 底部按钮栏 ===
        btn_bar = ttk.Frame(root_frame)
        btn_bar.pack(fill=tk.X, pady=(14, 0))

        self.start_btn = tk.Button(btn_bar, text=tr('▶ 启动监控'), command=self._start_monitoring,
                                   bg=C_OK, fg="white", activebackground="#27AE60",
                                   font=(ui_font(), 11, "bold"),
                                   relief="flat", cursor="hand2", padx=24, pady=8,
                                   bd=0, highlightthickness=0)
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.stop_btn = tk.Button(btn_bar, text=tr('⏹ 停止监控'), command=self._stop_monitoring,
                                  bg=C_ERR, fg="white", activebackground="#C0392B",
                                  font=(ui_font(), 11, "bold"),
                                  relief="flat", cursor="hand2", padx=24, pady=8,
                                  state=tk.DISABLED, bd=0, highlightthickness=0)
        self.stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        # 统计标签
        self.stats_label = ttk.Label(btn_bar, text="", style="Hint.TLabel")
        self.stats_label.pack(side=tk.RIGHT, pady=(6, 0))

    # ── 监控页签 ──

    def _build_monitor_tab(self, parent):
        # 状态卡片区域
        card_frame = tk.Frame(parent, bg=C_BG2, bd=0, highlightbackground=C_BORDER,
                              highlightthickness=1, padx=16, pady=14)
        card_frame.pack(fill=tk.X, pady=(0, 10))

        # 第一行：状态 + IP
        row1 = tk.Frame(card_frame, bg=C_BG2)
        row1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row1, text=tr('网络状态'), bg=C_BG2, fg=C_TEXT_DIM,
                 font=(ui_font(), 9)).pack(side=tk.LEFT)
        self.net_status_label = tk.Label(row1, text="--", bg=C_BG2,
                                         font=("Consolas", 14, "bold"), fg=C_TEXT_DIM)
        self.net_status_label.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Separator(row1, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=14, pady=2)

        tk.Label(row1, text=tr('本机IP'), bg=C_BG2, fg=C_TEXT_DIM,
                 font=(ui_font(), 9)).pack(side=tk.LEFT)
        self.ip_label = tk.Label(row1, text=get_local_ip(), bg=C_BG2,
                                 font=("Consolas", 11), fg=C_TEXT)
        self.ip_label.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Separator(row1, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=14, pady=2)

        tk.Label(row1, text=tr('连续异常'), bg=C_BG2, fg=C_TEXT_DIM,
                 font=(ui_font(), 9)).pack(side=tk.LEFT)
        self.fail_count_label = tk.Label(row1, text="0", bg=C_BG2,
                                         font=("Consolas", 14, "bold"), fg=C_TEXT)
        self.fail_count_label.pack(side=tk.LEFT, padx=(10, 0))

        # 第二行：倒计时 + VPN状态
        row2 = tk.Frame(card_frame, bg=C_BG2)
        row2.pack(fill=tk.X)

        tk.Label(row2, text=tr('下次检测'), bg=C_BG2, fg=C_TEXT_DIM,
                 font=(ui_font(), 9)).pack(side=tk.LEFT)
        self.next_check_label = tk.Label(row2, text="--:--:--", bg=C_BG2,
                                         font=("Digital-7", 18, "bold"), fg=C_ACCENT)
        self.next_check_label.pack(side=tk.LEFT, padx=(10, 0))

        # VPN 状态指示
        is_vpn, _ = detect_vpn()
        self.vpn_label = tk.Label(row2, text="VPN: " + (tr('⚠️ 开') if is_vpn else tr('✅ 关')),
                                  bg=C_BG2, fg=C_WARN if is_vpn else C_TEXT_DIM,
                                  font=(ui_font(), 9))
        self.vpn_label.pack(side=tk.RIGHT, padx=(0, 4))

        # 进度条
        self.progress_var = tk.DoubleVar(value=0)
        progress = ttk.Progressbar(card_frame, variable=self.progress_var,
                                   maximum=100, mode='determinate', length=300)
        progress.pack(fill=tk.X, pady=(12, 0))

        # 快捷操作区
        action_frame = tk.Frame(parent, bg=C_BG)
        action_frame.pack(fill=tk.X, pady=(6, 0))

        tk.Button(action_frame, text=tr('🔍 立即检测网络'),
                  command=self._manual_check,
                  bg=C_BORDER, fg=C_TEXT, font=(ui_font(), 9),
                  relief="flat", cursor="hand2", padx=12, pady=5,
                  bd=0, activebackground=C_ACCENT, activeforeground="white").pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(action_frame, text=tr('🔐 手动登录校园网'),
                  command=self._manual_login,
                  bg=C_BORDER, fg=C_TEXT, font=(ui_font(), 9),
                  relief="flat", cursor="hand2", padx=12, pady=5,
                  bd=0, activebackground=C_ACCENT, activeforeground="white").pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(action_frame, text=tr('📤 注销校园网'),
                  command=self._manual_logout,
                  bg=C_BORDER, fg=C_TEXT, font=(ui_font(), 9),
                  relief="flat", cursor="hand2", padx=12, pady=5,
                  bd=0, activebackground=C_WARN, activeforeground="white").pack(side=tk.LEFT)

    # ── 设置页签 ──

    def _build_settings_tab(self, parent):
        # Allow the longer English form to fit on smaller laptop displays.
        canvas = tk.Canvas(parent, bg=C_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        container = tk.Frame(canvas, bg=C_BG, pady=10)
        form_window = canvas.create_window((0, 0), window=container, anchor="nw")
        container.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(form_window, width=event.width))
        self.settings_canvas = canvas

        # 表单区域
        form = tk.LabelFrame(container, text=tr('  认证账号  '), bg=C_BG, fg=C_ACCENT,
                              font=(ui_font(), 11, "bold"),
                              bd=1, labelanchor="nw", padx=18, pady=14)
        form.pack(fill=tk.X, padx=30, pady=(0, 12))

        # 学号
        row_u = tk.Frame(form, bg=C_BG)
        row_u.pack(fill=tk.X, pady=4)
        tk.Label(row_u, text=tr('学号 / 教职工号'), bg=C_BG, fg=C_TEXT,
                 font=(ui_font(), 9), width=16, anchor="w").pack(side=tk.LEFT)
        self.entry_user = tk.Entry(row_u, font=("Consolas", 11), bg=C_BG2, fg=C_TEXT,
                                    relief="flat", width=28)
        self.entry_user.insert(0, self.cfg.get("username", ""))
        self.entry_user.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)

        # 密码
        row_p = tk.Frame(form, bg=C_BG)
        row_p.pack(fill=tk.X, pady=(8, 4))
        tk.Label(row_p, text=tr('统一身份密码'), bg=C_BG, fg=C_TEXT,
                 font=(ui_font(), 9), width=16, anchor="w").pack(side=tk.LEFT)
        self.entry_pwd = tk.Entry(row_p, font=("Consolas", 11), bg=C_BG2, fg=C_TEXT,
                                   show="●", relief="flat", width=28)
        self.entry_pwd.insert(0, self.cfg.get("password", ""))
        self.entry_pwd.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)

        # 显示密码复选框
        self.show_pwd_var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(row_p, text=tr('显示密码'), variable=self.show_pwd_var,
                            bg=C_BG, fg=C_TEXT_DIM, selectcolor=C_BG,
                            activebackground=C_BG, activeforeground=C_TEXT,
                            font=(ui_font(), 8),
                            command=self._toggle_password_visibility)
        cb.pack(side=tk.LEFT, padx=(8, 0))

        # ---- 高级设置 ----
        adv_form = tk.LabelFrame(container, text=tr('  监控参数  '), bg=C_BG, fg=C_ACCENT,
                                  font=(ui_font(), 11, "bold"),
                                  bd=1, labelanchor="nw", padx=18, pady=14)
        adv_form.pack(fill=tk.X, padx=30, pady=(0, 12))

        # 检测间隔
        row_i = tk.Frame(adv_form, bg=C_BG)
        row_i.pack(fill=tk.X, pady=4)
        tk.Label(row_i, text=tr('检测间隔'), bg=C_BG, fg=C_TEXT,
                 font=(ui_font(), 9), width=16, anchor="w").pack(side=tk.LEFT)

        interval_val = self.cfg.get("check_interval", 600)
        self.var_interval = tk.StringVar(value=str(interval_val))
        interval_spin = ttk.Spinbox(row_i, from_=30, to=3600, increment=30,
                                     textvariable=self.var_interval, width=10,
                                     font=("Consolas", 10))
        interval_spin.pack(side=tk.LEFT, padx=(10, 4))

        tk.Label(row_i, text=tr('秒'), bg=C_BG, fg=C_TEXT_DIM,
                 font=(ui_font(), 9)).pack(side=tk.LEFT)

        # 预设快捷按钮
        for mins, label in [(1, tr('1分钟')), (5, tr('5分钟')), (10, tr('10分')), (30, tr('30分'))]:
            b = tk.Button(row_i, text=label,
                         command=lambda v=mins*60: self.var_interval.set(str(v)),
                         bg=C_BORDER, fg=C_TEXT_DIM, font=(ui_font(), 8),
                         relief="flat", cursor="hand2", padx=6, bd=0,
                         activebackground=C_ACCENT, activeforeground="white")
            b.pack(side=tk.LEFT, padx=2)

        # 重试次数
        row_r = tk.Frame(adv_form, bg=C_BG)
        row_r.pack(fill=tk.X, pady=(8, 4))
        tk.Label(row_r, text=tr('重连尝试次数'), bg=C_BG, fg=C_TEXT,
                 font=(ui_font(), 9), width=16, anchor="w").pack(side=tk.LEFT)
        retry_val = self.cfg.get("reconnect_retries", 3)
        self.var_retry = tk.StringVar(value=str(retry_val))
        retry_spin = ttk.Spinbox(row_r, from_=1, to=10, increment=1,
                                  textvariable=self.var_retry, width=5,
                                  font=("Consolas", 10))
        retry_spin.pack(side=tk.LEFT, padx=(10, 0))

        # 重连间隔
        row_w = tk.Frame(adv_form, bg=C_BG)
        row_w.pack(fill=tk.X, pady=(8, 4))
        tk.Label(row_w, text=tr('重连等待时间'), bg=C_BG, fg=C_TEXT,
                 font=(ui_font(), 9), width=16, anchor="w").pack(side=tk.LEFT)
        wait_val = self.cfg.get("reconnect_wait_seconds", 20)
        self.var_wait = tk.StringVar(value=str(wait_val))
        wait_spin = ttk.Spinbox(row_w, from_=5, to=120, increment=5,
                                 textvariable=self.var_wait, width=5,
                                 font=("Consolas", 10))
        wait_spin.pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(row_w, text=tr('秒'), bg=C_BG, fg=C_TEXT_DIM,
                 font=(ui_font(), 9)).pack(side=tk.LEFT)

        # 自动重连开关
        auto_val = self.cfg.get("auto_login_enabled", True)
        self.auto_var = tk.BooleanVar(value=auto_val)
        auto_cb = tk.Checkbutton(adv_form, text=tr('断网时自动重连认证'),
                                 variable=self.auto_var, bg=C_BG, fg=C_TEXT,
                                 selectcolor=C_BG, activebackground=C_BG,
                                 font=(ui_font(), 10))
        auto_cb.pack(anchor="w", pady=(10, 4))

        self.prevent_sleep_var = tk.BooleanVar(
            value=self.cfg.get("prevent_sleep_enabled", True)
        )
        sleep_cb = tk.Checkbutton(adv_form, text=tr('锁屏/息屏后保持监控运行（阻止系统睡眠）'),
                                  variable=self.prevent_sleep_var, bg=C_BG, fg=C_TEXT,
                                  selectcolor=C_BG, activebackground=C_BG,
                                  font=(ui_font(), 10))
        sleep_cb.pack(anchor="w", pady=(2, 4))

        task_form = tk.LabelFrame(container, text=tr('  锁屏后台守护  '), bg=C_BG, fg=C_ACCENT,
                                  font=(ui_font(), 11, "bold"),
                                  bd=1, labelanchor="nw", padx=18, pady=12)
        task_form.pack(fill=tk.X, padx=30, pady=(0, 12))

        self.task_status_label = tk.Label(task_form, text="", bg=C_BG, fg=C_TEXT_DIM,
                                          font=(ui_font(), 9), anchor="w")
        self.task_status_label.pack(fill=tk.X, pady=(0, 8))

        task_btns = tk.Frame(task_form, bg=C_BG)
        task_btns.pack(fill=tk.X)

        tk.Button(task_btns, text=tr('安装守护'),
                  command=self._install_background_task,
                  bg=C_ACCENT, fg="white", font=(ui_font(), 9, "bold"),
                  relief="flat", cursor="hand2", padx=12, pady=5, bd=0,
                  activebackground="#5A4BD1").pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(task_btns, text=tr('立即启动'),
                  command=self._start_background_task_now,
                  bg=C_BORDER, fg=C_TEXT, font=(ui_font(), 9),
                  relief="flat", cursor="hand2", padx=12, pady=5, bd=0,
                  activebackground=C_ACCENT, activeforeground="white").pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(task_btns, text=tr('卸载守护'),
                  command=self._uninstall_background_task,
                  bg=C_BORDER, fg=C_TEXT_DIM, font=(ui_font(), 9),
                  relief="flat", cursor="hand2", padx=12, pady=5, bd=0,
                  activebackground=C_WARN, activeforeground="white").pack(side=tk.LEFT)

        self._refresh_task_status()

        # 保存按钮
        save_btn = tk.Button(container, text=tr('💾 保存设置'),
                             command=self._save_settings,
                             bg=C_ACCENT, fg="white", font=(ui_font(), 11, "bold"),
                             relief="flat", cursor="hand2", padx=32, pady=10, bd=0,
                             activebackground="#5A4BD1", highlightthickness=0)
        save_btn.pack(pady=(8, 0))

    # ── 日志页签 ──

    def _build_log_tab(self, parent):
        # 日志操作栏
        toolbar = tk.Frame(parent, bg=C_BG)
        toolbar.pack(fill=tk.X, pady=(0, 6))

        tk.Button(toolbar, text=tr('🗑 清空日志'), command=self._clear_log,
                  bg=C_BORDER, fg=C_TEXT_DIM, font=(ui_font(), 9),
                  relief="flat", cursor="hand2", padx=10, pady=3, bd=0).pack(side=tk.LEFT)

        tk.Button(toolbar, text=tr('📂 打开日志文件'), command=self._open_log_file,
                  bg=C_BORDER, fg=C_TEXT_DIM, font=(ui_font(), 9),
                  relief="flat", cursor="hand2", padx=10, pady=3, bd=0).pack(side=tk.LEFT, padx=(4, 0))

        self.log_size_label = tk.Label(toolbar, text="", bg=C_BG, fg=C_TEXT_DIM,
                                       font=(ui_font(), 8))
        self.log_size_label.pack(side=tk.RIGHT)

        # 日志文本框
        log_container = tk.Frame(parent, bg=C_BG)
        log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_container, wrap=tk.WORD,
                                 bg=C_BG2, fg=C_TEXT,
                                 font=("Consolas", 9),
                                 insertbackground=C_TEXT,
                                 selectbackground=C_ACCENT,
                                 relief="flat", padx=10, pady=8,
                                 state=tk.DISABLED, bd=0,
                                 highlightthickness=1,
                                 highlightbackground=C_BORDER)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置颜色标签
        self.log_text.tag_configure("ok", foreground=C_OK)
        self.log_text.tag_configure("err", foreground=C_ERR)
        self.log_text.tag_configure("warn", foreground=C_WARN)
        self.log_text.tag_configure("info", foreground=C_INFO)
        self.log_text.tag_configure("time", foreground=C_TEXT_DIM)
        self.log_text.tag_configure("accent", foreground=C_ACCENT)

        # 加载历史日志
        self._load_existing_log()

    # ── 辅助方法 ──

    def _draw_status(self, status, text):
        """更新状态指示器和文字"""
        colors = {
            "idle": (C_TEXT_DIM, tr('未启动')),
            "running_ok": (C_OK, tr('监控中 · 正常')),
            "running_warn": (C_WARN, tr('监控中 · 异常')),
            "error": (C_ERR, tr('错误')),
        }
        color, txt = colors.get(status, (C_TEXT_DIM, text))
        self.status_label.config(text=text or txt, foreground=color)
        self._draw_status_dot(status)

    def _draw_status_dot(self, state):
        """绘制状态指示圆点"""
        self.status_dot.delete("all")
        colors = {
            "idle": C_TEXT_DIM,
            "running_ok": C_OK,
            "running_warn": C_WARN,
            "error": C_ERR,
        }
        c = colors.get(state, C_TEXT_DIM)
        self.status_dot.create_oval(2, 2, 14, 14, fill=c, outline=c)

    def _log_to_ui(self, msg, tag=None):
        """向GUI日志面板追加消息（线程安全）"""
        def append():
            self.log_text.config(state=tk.NORMAL)
            ts = f"[{get_timestamp()}]"
            self.log_text.insert(tk.END, ts, "time")
            self.log_text.insert(tk.END, f" {msg}\n", tag or "")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
            # 更新大小
            count = int(self.log_text.index('end-1c').split('.')[0])
            self.log_size_label.config(text=tr('{0} 条日志', count))
        self.after(0, append)

    def _write_log(self, msg, tag=None):
        """同时写UI和文件"""
        clean_msg = msg.replace("\033[91m","").replace("\033[92m","").replace("\033[93m","").replace("\033[96m","").replace("\033[95m","").replace("\033[0m","")
        self._log_to_ui(msg, tag)
        write_log(clean_msg)

    def _toggle_password_visibility(self):
        if self.show_pwd_var.get():
            self.entry_pwd.config(show="")
        else:
            self.entry_pwd.config(show="●")

    def _load_existing_log(self):
        """加载已有的日志文件内容"""
        if not os.path.exists(LOG_FILE):
            return
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()[-100:]  # 最后100行
            self.log_text.config(state=tk.NORMAL)
            for line in lines:
                line = line.rstrip("\n")
                # 简单染色
                if tr('正常') in line or tr('恢复') in line or tr('成功') in line or "✅" in line:
                    tag = "ok"
                elif tr('异常') in line or tr('失败') in line or "❌" in line or tr('错误') in line:
                    tag = "err"
                elif "⚠️" in line or tr('警告') in line:
                    tag = "warn"
                elif "🔄" in line or "🔐" in line or "🔑" in line:
                    tag = "info"
                else:
                    tag = None
                self.log_text.insert(tk.END, line + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        except Exception:
            pass

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log_size_label.config(text=tr('0 条日志'))

    def _open_log_file(self):
        if os.path.exists(LOG_FILE):
            os.startfile(LOG_FILE)
        else:
            messagebox.showinfo(tr('提示'), tr('日志文件尚未生成'))

    # ── 设置保存 ──

    def _read_settings_from_form(self):
        cfg = dict(self.cfg)
        cfg["username"] = self.entry_user.get().strip()
        cfg["password"] = self.entry_pwd.get().strip()
        try:
            cfg["check_interval"] = max(30, int(self.var_interval.get()))
        except ValueError:
            cfg["check_interval"] = 600
        try:
            cfg["reconnect_retries"] = max(1, int(self.var_retry.get()))
        except ValueError:
            cfg["reconnect_retries"] = 3
        try:
            cfg["reconnect_wait_seconds"] = max(5, int(self.var_wait.get()))
        except ValueError:
            cfg["reconnect_wait_seconds"] = 20
        cfg["auto_login_enabled"] = self.auto_var.get()
        cfg["prevent_sleep_enabled"] = self.prevent_sleep_var.get()
        return cfg

    def _save_settings(self):
        self.cfg = self._read_settings_from_form()

        if save_config(self.cfg):
            self._log_to_ui(tr('💾 设置已保存！'), "ok")
            message = tr('配置已保存到:\n') + CONFIG_FILE
            messagebox.showinfo(tr('✅ 保存成功'), message)
        else:
            messagebox.showerror(tr('❌ 保存失败'), tr('无法写入配置文件！'))

    # ── 锁屏后台守护 ──

    def _refresh_task_status(self):
        if not hasattr(self, "task_status_label"):
            return
        if os.name != "nt":
            self.task_status_label.config(text=tr('当前系统不支持 Windows 计划任务'), fg=C_WARN)
            return
        mode = get_background_task_install_mode()
        if mode == "scheduled_task":
            self.task_status_label.config(text=tr('状态：已安装，登录后会自动后台监控'), fg=C_OK)
        elif mode == "startup_entry":
            self.task_status_label.config(
                text=tr('状态：已安装（当前用户启动项，无需管理员权限）'),
                fg=C_OK,
            )
        else:
            self.task_status_label.config(text=tr('状态：未安装'), fg=C_TEXT_DIM)

    def _install_background_task(self):
        self._save_settings_silent()
        self._log_to_ui(tr('🔧 正在安装锁屏后台守护...'), "info")

        def worker():
            ok, msg = install_background_task()
            if ok:
                run_ok, run_msg = run_background_task_now()
                self._write_log(tr('✅ 锁屏后台守护已安装'), "ok")
                if run_ok:
                    self._write_log(tr('🚀 后台守护已立即启动'), "ok")
                elif run_msg:
                    self._write_log(tr('⚠️ 守护已安装，但立即启动失败：{0}', run_msg), "warn")
                install_msg = msg or tr('锁屏后台守护已安装。')
                self.after(0, lambda: [
                    self._refresh_task_status(),
                    messagebox.showinfo(
                        tr('安装成功'),
                        install_msg + tr('\n\n之后登录 Windows 会自动后台监控，锁屏后也会继续运行。')
                    )
                ])
            else:
                self._write_log(tr('❌ 安装锁屏后台守护失败：{0}', msg), "err")
                self.after(0, lambda: messagebox.showerror(tr('安装失败'), msg or tr('无法创建计划任务')))

        threading.Thread(target=worker, daemon=True).start()

    def _uninstall_background_task(self):
        self._log_to_ui(tr('🧹 正在卸载锁屏后台守护...'), "warn")

        def worker():
            ok, msg = uninstall_background_task()
            if ok:
                self._write_log(tr('✅ 锁屏后台守护已卸载'), "ok")
                self.after(0, lambda: [
                    self._refresh_task_status(),
                    messagebox.showinfo(tr('卸载成功'), tr('锁屏后台守护已卸载。'))
                ])
            else:
                self._write_log(tr('❌ 卸载锁屏后台守护失败：{0}', msg), "err")
                self.after(0, lambda: messagebox.showerror(tr('卸载失败'), msg or tr('无法删除计划任务')))

        threading.Thread(target=worker, daemon=True).start()

    def _start_background_task_now(self):
        if not is_background_task_installed():
            messagebox.showwarning(tr('尚未安装'), tr('请先点击「安装守护」。'))
            return
        self._save_settings_silent()
        self._log_to_ui(tr('🚀 正在启动后台守护...'), "info")

        def worker():
            ok, msg = run_background_task_now()
            if ok:
                self._write_log(tr('✅ 后台守护启动请求已发送'), "ok")
                self.after(0, lambda: messagebox.showinfo(tr('已启动'), tr('后台守护启动请求已发送。')))
            else:
                self._write_log(tr('❌ 启动后台守护失败：{0}', msg), "err")
                self.after(0, lambda: messagebox.showerror(tr('启动失败'), msg or tr('无法启动计划任务')))

        threading.Thread(target=worker, daemon=True).start()

    # ── 手动操作 ──

    def _manual_check(self):
        """立即执行一次网络检测"""
        self._log_to_ui(tr('🔍 手动检测网络...'), "info")
        threading.Thread(target=self._do_single_check, daemon=True).start()

    def _do_single_check(self):
        is_ok = check_network()
        if is_ok:
            self._log_to_ui(tr('✅ 网络连通正常'), "ok")
            self.after(0, lambda: (
                self.net_status_label.config(text=tr('✅ 在线'), fg=C_OK),
                self.fail_count_label.config(text="0", fg=C_TEXT),
                self._draw_status("running_ok", tr('监控中 · 正常'))
            ))
        else:
            self._log_to_ui(tr('❌ 网络不可达'), "err")
            self.after(0, lambda: (
                self.net_status_label.config(text=tr('❌ 断网'), fg=C_ERR),
                self._draw_status("running_warn", tr('监控中 · 异常'))
            ))
        beep(1200 if is_ok else 800, 200)

    def _manual_login(self):
        """手动触发一次校园网认证"""
        user = self.entry_user.get().strip() or self.cfg.get("username", "")
        pwd = self.entry_pwd.get().strip() or self.cfg.get("password", "")
        if not user or not pwd:
            messagebox.showwarning(tr('⚠️ 缺少信息'), tr('请先在「账号设置」页填写学号和密码！'))
            return
        self._log_to_ui(tr('🔐 手动发起校园网认证...'), "accent")
        threading.Thread(target=self._do_auth_thread, args=(user, pwd,), daemon=True).start()

    def _manual_logout(self):
        """注销校园网"""
        user = self.entry_user.get().strip() or self.cfg.get("username", "")
        pwd = self.entry_pwd.get().strip() or self.cfg.get("password", "")
        if not user or not pwd:
            messagebox.showwarning(tr('⚠️ 缺少信息'), tr('请先在「账号设置」页填写学号和密码！'))
            return
        self._log_to_ui(tr('📤 发起注销请求...'), "warn")
        threading.Thread(target=lambda: self._do_logout_thread(user, pwd), daemon=True).start()

    def _do_logout_thread(self, user, pwd):
        def log_fn(msg): self._write_log(msg)
        client = SZUSrunClient(user, pwd, log_fn)
        ok = client.do_logout()
        if ok:
            self.after(0, lambda: messagebox.showinfo(tr('注销结果'), tr('注销请求已发送！')))
        else:
            # 读取最后一次日志判断原因
            self.after(0, lambda: messagebox.showwarning(
                tr('注销提示'), tr("注销请求已发送。\n如提示'You are not online'，说明当前没有登录会话。")))

    def _do_auth_thread(self, user, pwd):
        def log_fn(msg): self._write_log(msg)
        client = SZUSrunClient(user, pwd, log_fn)
        result = client.do_login()
        if result["success"]:
            self.after(0, lambda: [
                self._draw_status("running_ok", tr('认证完成')),
                messagebox.showinfo(tr('认证结果'), tr('✅ 校园网认证成功！')),
            ])
            beep(1500, 200)
            time.sleep(0.1)
            beep(1800, 300)
        else:
            errmsg = result.get("msg", tr('未知错误'))
            self.after(0, lambda msg=errmsg: [
                self._draw_status("error", tr('认证失败')),
                messagebox.showerror(tr('认证结果'), tr('❌ 校园网认证失败！\n{0}', msg)),
            ])
            beep(600, 400)

    # ── 启动/停止监控 ──

    def _start_monitoring(self):
        # 先保存当前设置
        self._save_settings_silent()

        # 刷新VPN检测
        self._update_vpn_status()

        user = self.cfg.get("username", "")
        pwd = self.cfg.get("password", "")

        if not user or not pwd:
            messagebox.showwarning(tr('⚠️ 缺少信息'),
                                   tr('请先在「账号设置」页面填写学号和密码！\n\n不填账号也可以检测网络状态\n但无法自动重连校园网。'))

        # VPN 警告
        is_vpn, _ = detect_vpn()
        if is_vpn:
            messagebox.showwarning(
                tr('⚠️ VPN 已开启'),
                tr('检测到系统可能开启了 VPN！\n\n程序已启用 VPN 兼容模式：网络检测不再依赖 ping，校园网认证请求会直连 SRUN 并绕过系统代理。\n\n如果你的 VPN 客户端强制拦截校园网内网地址，请在 VPN 中把 net.szu.edu.cn / 172.31.63.36 加入直连规则。'))

        self.monitoring = True
        self.stop_event.clear()
        self.consecutive_failures = 0

        # 更新UI状态
        self.start_btn.config(state=tk.DISABLED, bg=C_TEXT_DIM)
        self.stop_btn.config(state=tk.NORMAL, bg=C_ERR)
        self._draw_status("running_ok", tr('监控中启动...'))

        # 启动监控线程
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()

        self._write_log(tr('🚀 监控已启动'), "accent")

    def _update_vpn_status(self):
        """更新 VPN 状态指示器"""
        is_vpn, names = detect_vpn()
        if is_vpn:
            self.vpn_label.config(text=tr('VPN: ⚠️ 开'), fg=C_WARN)
        else:
            self.vpn_label.config(text=tr('VPN: ✅ 关'), fg=C_TEXT_DIM)

    def _stop_monitoring(self):
        self.monitoring = False
        self.stop_event.set()

        self.start_btn.config(state=tk.NORMAL, bg=C_OK)
        self.stop_btn.config(state=tk.DISABLED, bg=C_TEXT_DIM)
        self._draw_status("idle", tr('已停止'))
        self.net_status_label.config(text="--", fg=C_TEXT_DIM)
        self.next_check_label.config(text="--:--:--")
        self.progress_var.set(0)

        self._write_log(tr('🛑 监控已停止'), "warn")

    def _save_settings_silent(self):
        """静默保存（不弹窗）"""
        self.cfg = self._read_settings_from_form()
        save_config(self.cfg)

    # ── 监控主循环（后台线程） ──

    def _monitor_loop(self):
        interval = self.cfg.get("check_interval", 600)
        tick = 0
        sleep_prevention_active = False

        if self.cfg.get("prevent_sleep_enabled", True):
            sleep_prevention_active = set_system_sleep_prevention(True)
            if sleep_prevention_active:
                self._write_log(tr('🔒 已启用锁屏防睡眠：允许锁屏/息屏，但阻止系统睡眠'), "ok")
            else:
                self._write_log(tr('⚠️ 无法启用锁屏防睡眠，请检查系统权限'), "warn")

        while self.monitoring and not self.stop_event.is_set():
            if sleep_prevention_active:
                set_system_sleep_prevention(True)

            start_time = time.time()

            # 执行检测
            is_online = check_network()
            self.total_checks += 1

            if is_online:
                self.success_count += 1
                self.consecutive_failures = 0
                self._write_log(tr('✅ 网络正常'), "ok")
                self.after(0, lambda: [
                    self.net_status_label.config(text=tr('✅ 在线'), fg=C_OK),
                    self.fail_count_label.config(text="0", fg=C_TEXT),
                    self._draw_status("running_ok", tr('监控中 · 正常')),
                    self.stats_label.config(text=tr('检测 {0} 次 | 成功 {1} 次', self.total_checks, self.success_count))
                ])
            else:
                self.consecutive_failures += 1
                cf = self.consecutive_failures
                self._write_log(tr('❌ 网络异常 (第{0}次)', cf), "err")
                beep(1000, 500)

                self.after(0, lambda c=cf: [
                    self.net_status_label.config(text=tr('❌ 断网'), fg=C_ERR),
                    self.fail_count_label.config(text=str(c), fg=C_ERR),
                    self._draw_status("running_warn", tr('监控中 · 异常')),
                ])

                # 自动重连
                if cf >= 2 and self.cfg.get("auto_login_enabled", True):
                    user = self.cfg.get("username", "")
                    pwd = self.cfg.get("password", "")
                    if user and pwd:
                        self._handle_auto_reconnect(user, pwd)

            # 倒计时更新
            remaining = interval
            step = 1.0
            while remaining > 0 and self.monitoring and not self.stop_event.is_set():
                time.sleep(min(step, remaining))
                remaining -= step
                progress_pct = ((interval - remaining) / interval) * 100
                next_dt = datetime.datetime.now() + timedelta(seconds=int(remaining))
                self.after(0, lambda p=progress_pct, n=next_dt.strftime("%H:%M:%S"), r=int(remaining): [
                    self.progress_var.set(p),
                    self.next_check_label.config(text=n),
                ])

        if sleep_prevention_active:
            set_system_sleep_prevention(False)
            self._write_log(tr('🔓 已恢复系统睡眠策略'), "info")


    def _handle_auto_reconnect(self, user, pwd):
        max_tries = self.cfg.get("reconnect_retries", 3)
        wait_sec = self.cfg.get("reconnect_wait_seconds", 20)

        self._write_log(f"\n{'━'*40}", "accent")
        self._write_log(tr('🔄 触发SRUN自动认证'), "info")

        def log_cb(msg):
            self._write_log(msg)

        for attempt in range(1, max_tries + 1):
            self._write_log(tr('▶ 第 {0}/{1} 次认证尝试...', attempt, max_tries), "info")

            client = SZUSrunClient(user, pwd, log_cb)
            client.token = None
            client.refresh_ip()
            result = client.do_login()

            if result["success"]:
                self._write_log(tr('⏳ 等待 {0}s 验证网络...', wait_sec), "info")
                time.sleep(wait_sec)
                if check_network():
                    self._write_log(f"\n{'='*40}", "ok")
                    self._write_log(tr('🎉 网络恢复！认证成功！'), "ok")
                    self._write_log(f"{'='*40}\n", "ok")
                    self.consecutive_failures = 0
                    beep(1200, 200)
                    time.sleep(0.1)
                    beep(1500, 300)
                    return
            else:
                if attempt < max_tries:
                    w = min(wait_sec, 15)
                    self._write_log(tr('⏳ 等 {0}s 重试...', w), "warn")
                    time.sleep(w)

        self._write_log(tr('😞 已尝试 {0} 次未恢复，请手动检查', max_tries), "err")
        self._write_log(tr('  → 是否连接了 SZU_WLAN？账号密码正确？'), "warn")

    # ── 关闭处理 ──

    def _on_closing(self):
        if self.monitoring:
            answer = messagebox.askyesno(tr('确认退出'),
                                          tr('监控正在运行中。\n确定要退出吗？'))
            if not answer:
                return
            self._stop_monitoring()
        self.destroy()


# ══════════════════════════════════════════════════
#   入口
# ══════════════════════════════════════════════════

def main(argv=None):
    args = parse_cli_args(argv, daemon=True)
    if args.daemon_once or args.daemon:
        return run_daemon_monitor(run_once=args.daemon_once)
    app = NetMonitorApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
