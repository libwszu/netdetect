# 深大校园网自动重连工具

中文独立版 · [English project](https://github.com/libwszu/netdetect-en)

**[下载中文版 EXE（Windows 64 位，免安装）](https://github.com/libwszu/netdetect/releases/latest/download/SZU-Net-Monitor-CN.exe)**

[便携 ZIP 包](https://github.com/libwszu/netdetect/releases/latest/download/SZU-Net-Monitor-CN-Windows-x64.zip) · [全部发布版本](https://github.com/libwszu/netdetect/releases) · [开发者源码 ZIP](https://github.com/libwszu/netdetect/archive/refs/heads/main.zip)

## 下载后直接使用

无需安装 Python。下载上面的 EXE，放到自己可写的文件夹后双击运行；也可下载便携 ZIP，解压后运行其中的 EXE。

首次运行进入“账号设置”，填写自己的校园网账号和密码，保存后点击“启动监控”。个人配置和日志会保存在程序所在目录，发布包不含任何人的账号信息。适用于 Windows 10 / 11 的 64 位系统。

Windows 可能对未签名程序提示发布者未知。请核对下载来源为本仓库 Releases，或用 `SHA256SUMS.txt` 校验文件；无需关闭系统安全防护。


适用于深圳大学深澜 SRUN 校园网的 Windows 网络监控工具。检测连接状态，在需要时使用用户自己的账号完成校园网认证，提供图形界面、控制台和无界面后台监控。

当前 GUI 源码版本为 **v4.7**；控制台入口独立维护，参数和界面版本可能不同。这是个人工具，非深圳大学官方软件。

## 独立中文版

本仓库为固定中文界面、中文配置向导和中文运行日志的项目，不需要语言参数。英文项目单独维护在 [netdetect-en](https://github.com/libwszu/netdetect-en)。两边均针对深大校园网；同一账号建议只运行一个监控程序。

既有账号配置可继续使用，旧配置中的语言选项不再影响此中文版。

## 功能

- HTTP 优先判断网络连通性，Ping 用作补充，减少部分 VPN 环境中的误报。
- 实现 SRUN challenge、XXTEA、换表 Base64、HMAC-MD5 和 SHA1 认证流程。
- 图形界面配置账号、检测间隔、自动重连和重试参数，支持手动检测、登录和注销。
- 提供 `--daemon` 后台监控，以及 Windows 登录后启动的计划任务 / 当前用户启动项。
- 可选锁屏防睡眠，退出监控时恢复睡眠策略。
- 本地运行日志，便于排查认证或网络错误。

检测默认每 **600 秒**执行一次，GUI 最小间隔为 30 秒；恢复时间取决于检测周期、网络和认证服务响应。

## 使用方式

Git 源码仓库保存最新版代码及必要资源；免安装 EXE 和便携 ZIP 通过 Releases 提供。个人配置、运行日志和旧发布包不纳入 Git。

1. 连接校园有线网络或适用的校园 Wi-Fi。
2. 双击下载的 EXE，打开“账号设置”，填写自己的账号和认证密码，保存配置。
3. 回到“监控控制”，点击“启动监控”。
4. 按需调整检测间隔，或启用登录后运行的后台守护。

关闭 GUI 会停止该窗口的监控；另行安装的后台守护可独立运行。移动 EXE 或源码目录前，先卸载后台守护，再在新位置重新安装。

## 从源码运行

建议 Windows 10 / 11、Python 3.11+，并安装包含 tkinter 的 Python 发行版。运行依赖见 [requirements.txt](requirements.txt)。

```powershell
git clone https://github.com/libwszu/netdetect.git
Set-Location netdetect
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe net_monitor_gui.py
```

控制台方式需先配置账号，并从项目根目录启动：

```powershell
.\.venv\Scripts\python.exe setup_config.py
.\.venv\Scripts\python.exe net_monitor.py
```

在独立终端中运行无界面监控：

```powershell
.\.venv\Scripts\python.exe net_monitor_gui.py --daemon
```

如需单轮检测 / 重连，可使用 `--daemon-once`；此命令会执行真实网络操作。普通使用优先通过 GUI 管理后台守护，避免同时启动多个监控实例。

## 配置说明

程序首次启动会生成 `net_monitor_config.json`，也可从 [配置示例](net_monitor_config.example.json) 复制后填写：

```powershell
Copy-Item net_monitor_config.example.json net_monitor_config.json
```

如果已有配置，请直接在 GUI 中修改。示例文件不含个人账号密码。

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `username` | 空 | 用户自己的校园网账号 |
| `password` | 空 | 该账号的认证密码 |
| `check_interval` | `600` | GUI / daemon 检测间隔，秒，最小 30 |
| `auto_login_enabled` | `true` | 检测异常后启用自动认证 |
| `reconnect_retries` | `3` | 重试次数，最小 1 |
| `reconnect_wait_seconds` | `20` | 重连等待参数，秒；实际等待依代码分支处理 |
| `prevent_sleep_enabled` | `true` | 监控期间阻止系统睡眠，允许锁屏和息屏 |

GUI 和 daemon 读写程序目录的配置；控制台与配置向导使用当前工作目录。控制台检测间隔由 `net_monitor.py` 的 `CHECK_INTERVAL` 常量控制。

认证服务器由源码中的 `SRUN_BASE_URL = "http://net.szu.edu.cn"` 和 `SRUN_AC_ID = "12"` 决定；配置中的历史字段 `login_url` 不会替换这些常量。当前默认针对教学区，其他区域或学校需要自行核实服务器与协议。

## 账号与日志

账号密码以**明文保存在本地 JSON**，该文件和日志应只保存在自己的设备上。仓库通过 `.gitignore` 排除个人配置、日志、PID / 停止信号、旧发布包和工作助手记录。

反馈问题时请删除账号、IP、认证参数等敏感内容。工具仅用于自己获授权的账号，使用时遵守校园网规定。

## 构建 EXE

使用本仓库的中文 spec 构建，输出文件名为 `深大校园网自动重连.exe`。英文项目使用独立的构建配置。

在 Windows 项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm ".\深大校园网自动重连.spec"
```

现有 spec 已包含 `assets/` 中需要的图标资源，输出为 `dist/深大校园网自动重连.exe`。构建过程无需填写账号或连接认证服务器。

## 文件结构

```text
.
├── net_monitor_gui.py             # GUI、daemon、后台启动项管理
├── net_monitor.py                 # 控制台网络监控
├── setup_config.py                # 交互式配置向导
├── net_monitor_config.example.json # 空账号配置示例
├── 深大校园网自动重连.spec         # PyInstaller 构建配置
├── assets/                        # 界面和打包使用的图片、图标
├── requirements.txt               # requests 依赖
├── README.md
└── LICENSE
```

## 常见问题

**认证失败。** 先确认校园网络已连接，并通过官方认证页面验证账号状态。账号欠费、认证服务变更或当前区域的 `ac_id` 不同都可能导致失败。

**VPN 开启后异常。** 程序会关闭认证请求对系统代理环境的自动读取，但 TUN 路由仍可能影响连接。按所用 VPN 客户端的配置，将校园认证服务器设为直连后再检查。

**后台守护安装失败。** 程序会先创建登录触发的计划任务，失败时尝试当前用户启动项；查看 GUI 返回的具体消息和日志。可在账号设置中卸载后台守护。

**锁屏后仍断网。** 防睡眠只能减少监控被系统睡眠暂停的情况，不能维持关机状态下的联网，也无法阻止网卡省电或校园网主动断开。

本版本包含中文界面、配置兼容性、密码隐藏、后台监控和认证参数的离线回归测试。测试不执行真实校园网登录、注销或后台任务安装；实际认证仍需在校园网环境验证。

## 反馈与许可

- [问题反馈](https://github.com/libwszu/netdetect/issues)
- [MIT License](LICENSE)，保留原项目版权声明。
- 协议实现参考：[lossinwind/szu-auto-login](https://github.com/lossinwind/szu-auto-login)。

`assets/` 中的校徽相关资源仅用于识别使用场景，不表示官方背书；第三方标识的相关权利归各自权利人。

## 发布构建

免安装版本由 GitHub Actions 的 Windows 环境从公开源码构建。运行离线测试、打包后启动检查和内置模块检查后，生成 EXE、便携 ZIP、SHA-256 校验表及构建信息，再发布到 Releases。维护者可以在 Actions 中运行“Build portable Windows app”，或推送版本标签触发构建。
