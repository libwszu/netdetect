"""
深大校园网断网自动重连工具 v4.7
====================================
- 每10分钟检测网络连通性（ping + HTTP双重检测）
- 断网后通过深澜SRUN API直接认证登录（无需浏览器！）
- 适用于深圳大学教学办公区校园网认证系统
- 纯Python实现，仅需 requests 依赖

作者: WorkBuddy
用法: python net_monitor.py
配置: 编辑 net_monitor_config.json 或运行 python setup_config.py
"""

import sys
from i18n import tr, set_language, get_language, resolve_language, parse_language_args, ui_font, LANGUAGE_LABELS
import subprocess
import time
import datetime
import os
import json
import socket
import hashlib
import hmac
import base64
import ctypes
try:
    import requests
except ImportError:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "requests", "-q"
    ])
    import requests

# ========== 全局配置 ==========
CHECK_INTERVAL = 600           # 检测间隔（秒），默认10分钟
PING_TARGET = "223.5.5.5"     # ping目标（阿里DNS）
HTTP_TEST_URL = "http://www.baidu.com"  # HTTP连通性测试地址
PING_TIMEOUT = 5               # ping超时（秒）
HTTP_TIMEOUT = 8               # HTTP超时（秒）
LOG_FILE = "net_monitor.log"
CONFIG_FILE = "net_monitor_config.json"

# ── 深大SRUN认证系统常量 ──
SRUN_BASE_URL = "http://net.szu.edu.cn"
SRUN_CALLBACK = "jQueryCallback"
SRUN_AC_ID = "12"
SRUN_N = "200"
SRUN_TYPE = "1"
SRUN_ENC = "srun_bx1"
SRUN_DEFAULT_DOMAIN = "@hlw"
B64_ALPHA = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

# 控制台颜色
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAGENTA = "\033[95m"
RESET  = "\033[0m"


# ══════════════════════════════════════
#  配置管理
# ══════════════════════════════════════

def load_config():
    """加载配置，不存在则创建默认配置"""
    default = {
        "language": "en",
        "login_url": "https://net.szu.edu.cn",
        "username": "",
        "password": "",
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
        cfg["reconnect_retries"] = _safe_int(cfg.get("reconnect_retries"), 3, 1)
        cfg["reconnect_wait_seconds"] = _safe_int(cfg.get("reconnect_wait_seconds"), 20, 5)
        cfg["prevent_sleep_enabled"] = bool(cfg.get("prevent_sleep_enabled", True))
        return cfg
    except Exception:
        return default


def _safe_int(value, default, minimum):
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return default


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════
#  基础工具
# ══════════════════════════════════════

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = f"[{get_timestamp()}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def beep(freq=1000, duration=300):
    """Windows蜂鸣提示"""
    try:
        import winsound
        winsound.Beep(freq, duration)
    except ImportError:
        pass


def set_system_sleep_prevention(enabled=True):
    """
    允许锁屏/息屏，但阻止 Windows 进入睡眠，避免锁屏后监控线程被系统挂起。
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


def get_local_ip():
    """获取本机真实校园网IP（VPN感知版），优先直连SRUN服务器"""
    # 方式1：直接连 SRUN 服务器（绕过 VPN 走物理网卡）
    try:
        srun_ip = socket.gethostbyname("net.szu.edu.cn")
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((srun_ip, 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
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
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"


def _get_physical_interface_ip():
    """找到非VPN的物理网卡IP，用于绑定socket绕过VPN路由"""
    vpn_kw = ["vpn", "tap", "tun", "openvpn", "wireguard", "wg",
              "clash", "v2ray", "shadow", "trojan", "hysteria", "sing-box",
              "virtual", "ppp", "l2tp", "sstp", "nord", "express", "surfshark",
              "proton", "hyper-v", "wsl", "docker", "vmware", "virtualbox"]
    try:
        result = subprocess.run(
            ["ipconfig"], capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        text = result.stdout
        sections = text.split("\n\n")
        for sec in sections:
            sec_lower = sec.lower()
            if any(kw in sec_lower for kw in vpn_kw):
                continue
            for line in sec.split("\n"):
                if "IPv4" in line or "IP Address" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        ip = parts[-1].strip()
                        if ip.startswith(("10.", "172.", "192.168.")):
                            return ip
    except Exception:
        pass
    return None


def _create_bound_adapter(source_ip):
    """创建一个绑定到指定源IP的HTTPAdapter"""
    class BoundHTTPAdapter(requests.adapters.HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            kwargs["source_address"] = (source_ip, 0)
            super().init_poolmanager(*args, **kwargs)
    return BoundHTTPAdapter()


def detect_vpn():
    """检测是否开启了VPN"""
    vpn_keywords = [
        "vpn", "tap", "tun", "openvpn", "wireguard", "wg",
        "clash", "v2ray", "shadowsocks", "trojan",
        "hysteria", "sing-box", "virtual", "ppp", "l2tp", "sstp",
    ]
    suspected = []
    try:
        result = subprocess.run(
            ["ipconfig"], capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
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

    try:
        result = subprocess.run(
            ["route", "print", "0.0.0.0"], capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        default_routes = [l for l in result.stdout.split("\n") if "0.0.0.0" in l and "On-link" not in l]
        if len(default_routes) > 2:
            suspected.append(tr('多默认路由(可能VPN)'))
    except Exception:
        pass

    return (len(suspected) > 0, suspected)


# ══════════════════════════════════════
#  网络检测（双重机制）
# ══════════════════════════════════════

def check_network_ping():
    """方式1：ping检测（快速，检测链路层）"""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(PING_TIMEOUT * 1000), PING_TARGET],
            capture_output=True, text=True, timeout=PING_TIMEOUT + 2,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_network_http():
    """
    HTTP检测：校园网Captive Portal未认证时会把HTTP请求301跳转到认证页面。
    禁止跟随跳转，只认严格的200/204状态码，拒绝3xx（门户拦截）。
    """
    # 方式1：严格模式（不跟随跳转），用于已知返回固定状态码的测试地址
    strict_tests = [
        ("http://www.msftconnecttest.com/connecttest.txt", 200),
        ("http://connect.rom.miui.com/generate_204", 204),
    ]
    for url, expected_code in strict_tests:
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=False)
            if resp.status_code == expected_code:
                if "msftconnecttest" in url:
                    if "Microsoft Connect Test" in resp.text:
                        return True
                else:
                    return True
        except Exception:
            continue

    # 方式2：宽松模式（跟随跳转），验证最终页面内容
    content_tests = [
        ("http://www.baidu.com", "baidu"),
    ]
    for url, keyword in content_tests:
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True)
            if resp.status_code == 200 and keyword in resp.text.lower():
                return True
        except Exception:
            continue

    return False


def check_network():
    """
    综合检测：必须HTTP验证通过才算真正在线。
    单纯ping通不代表校园网已认证——Captive Portal放行ICMP但拦截HTTP。
    """
    # VPN/代理常会屏蔽 ICMP，不能把 ping 失败当成断网依据。
    if check_network_http():
        return True
    return False


# ══════════════════════════════════════
#  深澜SRUN加密算法核心
#  （从认证页面JS逆向得到）
# ══════════════════════════════════════

class _String(str):
    """JS字符串兼容类，支持charCodeAt/fromCharCode"""

    def charCodeAt(self, i):
        if len(self) > i:
            return ord(self[i])
        return 0

    @classmethod
    def fromCharCode(cls, *codes):
        return "".join(chr(c) for c in codes)


def _str_to_long_arr(s, pad):
    """字符串 → 32位整数数组（小端）"""
    c = len(s)
    v = []
    for i in range(0, c, 4):
        v.append(
            s.charCodeAt(i)
            | s.charCodeAt(i + 1) << 8
            | s.charCodeAt(i + 2) << 16
            | s.charCodeAt(i + 3) << 24
        )
    if pad:
        v.append(c)
    return v


def _long_arr_to_str(a, unpad):
    """32位整数数组 → 字符串"""
    d = len(a)
    c = (d - 1) << 2
    if unpad:
        m = a[d - 1]
        if m < c - 3 or m > c:
            return None
        c = m
    out = []
    for val in a:
        out.append(chr(val & 0xFF))
        out.append(chr((val >> 8) & 0xFF))
        out.append(chr((val >> 16) & 0xFF))
        out.append(chr((val >> 24) & 0xFF))
    result = "".join(out)
    return result[:c] if unpad else result


def xxtea_encrypt(plaintext, key):
    """XXTEA加密（与SRUN前端JS一致）"""
    if not plaintext:
        return ""
    pt = _String(plaintext)
    ky = _String(key)

    v = _str_to_long_arr(pt, True)
    k = _str_to_long_arr(ky, False)
    while len(k) < 4:
        k.append(0)

    n = len(v) - 1
    z = v[n]
    y = v[0]

    # SRUN使用的DELTA和常量
    DELTA = 0x9E3779B9
    q = int(6 + 52 / (n + 1))
    d = 0

    for _ in range(q):
        d = (d + DELTA) & 0xFFFFFFFF
        e = (d >> 2) & 3
        for p in range(n):
            y = v[p + 1]
            mx = ((z >> 5) ^ (y << 2)) + (((y >> 3) ^ (z << 4)) ^ (d ^ y)) + (k[(p & 3) ^ e] ^ z)
            z = v[p] = (v[p] + mx) & 0xFFFFFFFF
        y = v[0]
        mx = ((z >> 5) ^ (y << 2)) + (((y >> 3) ^ (z << 4)) ^ (d ^ y)) + (k[(n & 3) ^ e] ^ z)
        z = v[n] = (v[n] + mx) & 0xFFFFFFFF

    return _long_arr_to_str(v, False)


def trans_base64(s, alpha=None):
    """换表Base64编码"""
    result = base64.b64encode(s.encode("latin-1")).decode()
    if alpha and len(alpha) == 64:
        table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        trans_table = str.maketrans(table, alpha)
        result = result.translate(trans_table)
    return result


def hmac_md5(msg, key):
    """HMAC-MD5"""
    return hmac.new(
        key.encode(), msg.encode(), hashlib.md5
    ).hexdigest()


def sha1_hash(msg):
    """SHA1哈希"""
    return hashlib.sha1(msg.encode()).hexdigest()


def normalize_srun_username(username):
    username = (username or "").strip()
    if username and "@" not in username:
        return username + SRUN_DEFAULT_DOMAIN
    return username


# ══════════════════════════════════════
#  深大校园网 SRUN 认证流程
# ══════════════════════════════════════

class SZUSrunClient:
    """深圳大学深澜SRUN校园网认证客户端"""

    def __init__(self, username, password):
        self.username = username
        self.auth_username = normalize_srun_username(username)
        self.password = password
        self.ip = None
        self.token = None

        # VPN 绕过
        self._is_vpn, self._vpn_names = detect_vpn()
        self._srun_ip = self._resolve_srun_ip()
        self._use_direct_ip = self._is_vpn

        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        })

        if self._is_vpn:
            log(tr('{0}⚠️ VPN已检测: {1}{2}', YELLOW, ', '.join(self._vpn_names[:2]), RESET))
            log(tr('{0}🔌 SRUN认证请求已关闭系统代理，避免被VPN代理接管{1}', CYAN, RESET))
            log(tr('{0}🌐 SRUN直连IP: {1}{2}', CYAN, self._srun_ip, RESET))

        if self.auth_username != self.username:
            log(tr('{0}账号未带认证域，按官方默认补全为: {1}{2}', CYAN, self.auth_username, RESET))

    @staticmethod
    def _resolve_srun_ip():
        """解析 SRUN 服务器 IP"""
        try:
            return socket.gethostbyname("net.szu.edu.cn")
        except Exception:
            return "172.31.63.36"

    def _build_url(self, path):
        if self._use_direct_ip:
            return f"http://{self._srun_ip}{path}"
        return f"{SRUN_BASE_URL}{path}"

    def _get_host_headers(self):
        if self._use_direct_ip:
            return {"Host": "net.szu.edu.cn"}
        return {}

    def refresh_ip(self):
        """获取/刷新本机IP"""
        self.ip = get_local_ip()
        is_vpn, vpn_names = detect_vpn()
        if is_vpn:
            log(tr('{0}⚠️ 检测到VPN: {1}{2}', YELLOW, ', '.join(vpn_names[:2]), RESET))
        log(tr('{0}📡 本机IP: {1}{2}', CYAN, self.ip, RESET))
        return self.ip

    def get_challenge(self):
        """步骤1：获取challenge token，并自动修正IP（绕过VPN）"""
        if not self.ip:
            self.refresh_ip()

        url = self._build_url("/cgi-bin/get_challenge")
        params = {
            "callback": SRUN_CALLBACK,
            "username": self.auth_username,
            "ip": self.ip,
            "_": str(int(time.time() * 1000)),
        }

        log(tr('{0}🔑 正在获取认证Token...{1}', CYAN, RESET))
        try:
            resp = self.session.get(url, params=params, timeout=10,
                                     headers=self._get_host_headers())
            text = resp.text.strip()

            # 处理空响应（VPN IP被拒绝时可能返回空）
            if not text:
                log(tr('{0}❌ 服务器返回空（IP可能被VPN拦截）{1}', RED, RESET))
                # 重试不带IP
                params2 = {"callback": SRUN_CALLBACK, "username": self.auth_username,
                          "ip": "", "_": str(int(time.time() * 1000))}
                resp = self.session.get(url, params=params2, timeout=10,
                                         headers=self._get_host_headers())
                text = resp.text.strip()
                if not text:
                    log(tr('{0}❌ 仍返回空，请关闭VPN后重试{1}', RED, RESET))
                    return False

            # 解析JSONP响应: jQueryCallback({...});
            start = text.index("(") + 1
            end = text.rindex(")")
            data = json.loads(text[start:end])

            if data.get("res") != "ok":
                log(tr('{0}❌ 获取Token失败: {1}{2}', RED, data, RESET))
                return False

            # ★ 用服务器看到的真实IP覆盖本地IP（绕过VPN）
            client_ip = data.get("client_ip", "")
            old_ip = self.ip
            if client_ip and client_ip != old_ip:
                self.ip = client_ip
                log(tr('{0}🔧 IP已修正: {1} → {2}{3}', GREEN, old_ip, client_ip, RESET))

            self.token = data["challenge"]
            expire = data.get("expire", "?")
            log(tr('{0}✅ Token获取成功 (有效期{1}秒){2}', GREEN, expire, RESET))
            return True

        except Exception as e:
            log(tr('{0}❌ 获取Token异常: {1}{2}', RED, e, RESET))
            return False

    def build_login_params(self):
        """
        步骤2：构建加密后的登录参数
        包含三个核心加密：
          1. password ← HMAC-MD5(明文密码, token)
          2. info     ← XXTEA(JSON用户信息) → 换表Base64
          3. chksum   ← SHA1(token分隔拼接所有参数)
        """
        token = self.token
        uname = self.auth_username
        pwd = self.password
        ip = self.ip

        # --- 密码加密: {MD5} + HMAC-MD5 ---
        hmd5_pwd = hmac_md5(pwd, token)
        encrypted_password = "{MD5}" + hmd5_pwd

        # --- 用户信息加密: {SRBX1} + XXTEA + 换表Base64 ---
        info_json = json.dumps({
            "username": uname,
            "password": pwd,
            "ip": ip,
            "acid": SRUN_AC_ID,
            "enc_ver": SRUN_ENC,
        }, separators=(",", ":"))  # 无空格压缩

        xxtea_result = xxtea_encrypt(info_json, token)
        encrypted_info = "{SRBX1}" + trans_base64(xxtea_result, B64_ALPHA)

        # --- 校验和: SHA1 ---
        chk_str = (
            token + uname +
            token + hmd5_pwd +
            token + SRUN_AC_ID +
            token + ip +
            token + SRUN_N +
            token + SRUN_TYPE +
            token + encrypted_info
        )
        checksum = sha1_hash(chk_str)

        # 组装完整参数
        params = {
            "callback": SRUN_CALLBACK,
            "action": "login",
            "username": uname,
            "password": encrypted_password,
            "os": "Windows",
            "name": "Windows",
            "nas_ip": "",
            "double_stack": 0,
            "chksum": checksum,
            "info": encrypted_info,
            "ac_id": SRUN_AC_ID,
            "ip": ip,
            "n": SRUN_N,
            "type": SRUN_TYPE,
            "captchaVal": "",
            "_": str(int(time.time() * 1000)),
        }
        return params

    def do_login(self):
        """步骤3：发送认证请求"""
        if not self.token:
            if not self.get_challenge():
                return {"success": False, "msg": tr('获取Token失败')}

        params = self.build_login_params()
        url = self._build_url("/cgi-bin/srun_portal")

        log(tr('{0}🔐 正在提交认证...{1}', CYAN, RESET))
        try:
            resp = self.session.get(url, params=params, timeout=15,
                                     headers=self._get_host_headers())
            text = resp.text

            # 解析JSONP
            start = text.index("(") + 1
            end = text.rindex(")")
            result = json.loads(text[start:end])

            res = result.get("res", "")
            error_msg = result.get("error_msg", result.get("msg", ""))

            if res == "ok":
                log(tr('{0}✅✅✅ 校园网认证成功！{1}', GREEN, RESET))
                return {"success": True, "msg": tr('认证成功')}
            else:
                log(tr('{0}❌ 认证失败: [{1}] {2}{3}', RED, res, error_msg, RESET))
                return {"success": False, "msg": error_msg}

        except ValueError as e:
            log(tr('{0}❌ 认证响应解析失败: {1}{2}', RED, e, RESET))
            log(tr('{0}   原始响应: {1}{2}', YELLOW, resp.text[:200], RESET))
            return {"success": False, "msg": tr('响应格式错误')}
        except Exception as e:
            log(tr('{0}❌ 认证请求异常: {1}{2}', RED, e, RESET))
            return {"success": False, "msg": str(e)}

    def do_logout(self):
        """注销登录（与官方JS _logoutNormal 一致，仅需4个参数）"""
        params = {
            "callback": SRUN_CALLBACK,
            "action": "logout",
            "username": self.auth_username,
            "ip": self.ip or get_local_ip(),
            "ac_id": SRUN_AC_ID,
        }

        try:
            resp = self.session.get(
                self._build_url("/cgi-bin/srun_portal"),
                params=params, timeout=10,
                headers=self._get_host_headers()
            )
            text = resp.text
            try:
                start = text.index("(") + 1
                end = text.rindex(")")
                data = json.loads(text[start:end])
                res = data.get("res", "")
                emsg = data.get("error_msg", data.get("msg", ""))
                if res == "ok" or "logout" in str(data).lower():
                    log(tr('{0}✅ 注销成功{1}', GREEN, RESET))
                    return True
                else:
                    log(tr('{0}❌ 注销失败: [{1}] {2}{3}', RED, res, emsg, RESET))
                    return False
            except (ValueError, Exception):
                log(tr('{0}📤 已发送注销请求{1}', CYAN, RESET))
                return True
        except Exception as e:
            log(tr('{0}❌ 注销失败: {1}{2}', RED, e, RESET))
            return False


# ══════════════════════════════════════
#  断网处理 & 自动重连主逻辑
# ══════════════════════════════════════

def handle_disconnection(consecutive_failures, cfg):
    """断网后处理：报警 + SRUN API自动认证重连"""

    max_retries = cfg.get("reconnect_retries", 3)
    retry_interval = cfg.get("reconnect_wait_seconds", 20)
    auto_enabled = cfg.get("auto_login_enabled", True)

    log(tr('{0}❌ 网络异常！(连续第 {1} 次){2}', RED, consecutive_failures, RESET))

    # 蜂鸣报警
    beep(1000, 500)

    if consecutive_failures < 2 or not auto_enabled:
        if consecutive_failures >= 3 and not auto_enabled:
            log(tr('{0}⚠️ 网络持续异常 {1} 次！（自动登录已禁用）{2}', YELLOW, consecutive_failures, RESET))
        return False

    # ===== 触发SRUN自动认证 =====
    username = cfg.get("username", "")
    password = cfg.get("password", "")

    if not username or not password:
        log(tr('{0}⚠️ 账号或密码为空！请编辑 {1} 填写。{2}', YELLOW, CONFIG_FILE, RESET))
        return False

    log(f"\n{MAGENTA}{'━' * 50}{RESET}")
    log(tr('{0}  🔄 启动深大校园网SRUN自动认证{1}', MAGENTA, RESET))
    log(f"{MAGENTA}{'━' * 50}\n{RESET}")

    client = SZUSrunClient(username, password)

    for attempt in range(1, max_retries + 1):
        log(tr('{0}▶ 第 {1}/{2} 次认证尝试...{3}', CYAN, attempt, max_retries, RESET))

        # 重置token（每次重新获取新token）
        client.token = None
        client.refresh_ip()

        result = client.do_login()

        if result["success"]:
            # 登录成功后等待几秒再验证
            log(tr('{0}⏳ 等待 {1} 秒后验证网络...{2}', CYAN, retry_interval, RESET))
            time.sleep(retry_interval)

            if check_network():
                log(f"\n{GREEN}{'=' * 50}{RESET}")
                log(tr('{0}  🎉 网络已恢复！校园网认证成功！{1}', GREEN, RESET))
                log(f"{GREEN}{'=' * 50}{RESET}\n")
                # 成功提示音
                beep(1200, 200)
                time.sleep(0.1)
                beep(1500, 300)
                return True
            else:
                log(tr('{0}⚠️ 认证成功但网络尚未通畅，继续等待...{1}', YELLOW, RESET))
        else:
            log(tr('{0}⚠️ 第 {1} 次认证未通过{2}', YELLOW, attempt, RESET))
            if attempt < max_retries:
                wait_sec = min(retry_interval, 15)
                log(tr('{0}⏳ 等待 {1} 秒后重试...{2}', CYAN, wait_sec, RESET))
                time.sleep(wait_sec)

    log(tr('{0}\n😞 已尝试 {1} 次均未恢复，请手动检查：{2}', RED, max_retries, RESET))
    log(tr('  1. 是否连接了 SZU_WLAN / 有线网络？'))
    log(tr('  2. 账号密码是否正确？'))
    log(tr('  3. 是否欠费或账号被冻结？\n'))
    return False


# ══════════════════════════════════════
#  启动界面
# ══════════════════════════════════════

def show_banner():
    cfg = load_config()

    user_display = cfg.get("username", "")
    if user_display:
        user_display = user_display[:3] + "***"  # 脱敏显示

    print(f"\n{'='*58}")
    print(tr('  🎓 深大校园网断网自动重连工具 v4.7'))
    print(tr('  (深澜SRUN认证 · 无需浏览器 · 纯API直连)'))
    print(f"{'='*58}")
    print(tr('  检测间隔: {0}分钟 ({1}秒)', CHECK_INTERVAL // 60, CHECK_INTERVAL))
    print(tr('  检测方式: Ping + HTTP 双重验证'))
    print(tr('  认证系统: 深澜 SRUN @ net.szu.edu.cn'))
    print(tr('  账号:     {0}', user_display or tr('(未设置)')))
    print(tr('  自动重连: {0}', tr('开启') if cfg.get('auto_login_enabled') else tr('关闭')))
    print(tr('  重试次数: {0}次', cfg.get('reconnect_retries', 3)))
    print(tr('  日志文件: {0}', os.path.abspath(LOG_FILE)))
    print(f"{'='*58}")
    print(tr('  按 Ctrl+C 停止 | 运行 setup_config.py 配置账号\n'))


# ══════════════════════════════════════
#  主循环
# ══════════════════════════════════════

def main(argv=None):
    args = parse_language_args(argv, description="SZU Network Monitor (command line)")
    cfg = load_config()
    set_language(resolve_language(args.lang, cfg.get("language")))
    show_banner()

    if not cfg.get("username") or not cfg.get("password"):
        log(tr('{0}⚠️ 首次运行！请先填写账号密码：{1}', YELLOW, RESET))
        log(tr('  方式1: 运行 python setup_config.py （推荐）'))
        log(tr('  方式2: 手动编辑 {0}\n', CONFIG_FILE))

    log(tr('{0}🚀 监控启动...{1}', CYAN, RESET))

    consecutive_failures = 0
    sleep_prevention_active = False

    if cfg.get("prevent_sleep_enabled", True):
        sleep_prevention_active = set_system_sleep_prevention(True)
        if sleep_prevention_active:
            log(tr('{0}🔒 已启用锁屏防睡眠：允许锁屏/息屏，但阻止系统睡眠{1}', GREEN, RESET))
        else:
            log(tr('{0}⚠️ 无法启用锁屏防睡眠，请检查系统权限{1}', YELLOW, RESET))

    try:
        while True:
            if sleep_prevention_active:
                set_system_sleep_prevention(True)

            is_online = check_network()

            if is_online:
                log(tr('{0}✅ 网络正常{1}', GREEN, RESET))
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                recovered = handle_disconnection(consecutive_failures, cfg)
                if recovered:
                    consecutive_failures = 0

            # 下次检测时间
            next_time = datetime.datetime.now() + datetime.timedelta(
                seconds=CHECK_INTERVAL
            )
            log(tr('{0}💤 下次检测: {1}{2}', CYAN, next_time.strftime('%H:%M:%S'), RESET))
            print("-" * 52)

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        log(tr('\n{0}🛑 用户手动停止监控{1}', YELLOW, RESET))
        log(tr('{0}日志已保存至: {1}{2}', CYAN, os.path.abspath(LOG_FILE), RESET))
    finally:
        if sleep_prevention_active:
            set_system_sleep_prevention(False)
            log(tr('{0}🔓 已恢复系统睡眠策略{1}', CYAN, RESET))


if __name__ == "__main__":
    main()
