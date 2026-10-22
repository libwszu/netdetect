# SZU Network Monitor

English | [简体中文](README.zh-CN.md)

A Windows network monitor for Shenzhen University (SZU) students and staff, including international users. It checks connectivity and can sign in to the campus SRUN portal with your own account when the connection drops.

**Version 4.7** adds an English interface, activity messages, account setup wizard and documentation, with Simplified Chinese available as an option. This is an independent project, not an official SZU application. It is configured for SZU's campus SRUN service; it is not a general VPN or a sign-in tool for arbitrary networks.

## Features

- Desktop interface for network status, account settings, manual sign-in / sign-out and activity logs.
- Automatic sign-in after repeated connectivity failures, with configurable retry settings.
- HTTP connectivity checks with ping as a fallback, plus system-proxy bypass for SRUN requests.
- A background monitor that can start when you sign in to Windows.
- Optional sleep prevention while monitoring; locking the screen is still allowed.
- English and Simplified Chinese, using the same authentication implementation.

The default check interval is **600 seconds**. Reconnection time depends on this interval, retry settings and the campus service response.

## Quick start

Use Windows 10 or 11 with **Python 3.11+**, including tkinter. In PowerShell:

```powershell
git clone https://github.com/libwszu/netdetect.git
Set-Location netdetect
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe net_monitor_gui.py --lang en
```

1. Connect to the relevant SZU wired network or campus Wi-Fi.
2. Open **Settings** and enter your campus account (student or staff ID) and the password accepted by the official campus sign-in page. This is not your Wi-Fi passphrase.
3. Select **Save settings**, then **Start monitoring**.
4. Use **Check now**, **Sign in** or **Sign out** for manual actions.

Credentials are optional for connectivity checks, but required for automatic campus sign-in. New installations use English by default; an explicit `--lang en` overrides a previously saved Chinese preference.

## Change language

In **Settings → Interface language**, choose **English** or **简体中文**, save and restart the application. You can also select the language for one run:

```powershell
python net_monitor_gui.py --lang en
python net_monitor_gui.py --lang zh-CN
python setup_config.py --lang en
python net_monitor.py --lang en
```

`--lang` takes priority over the saved `language` setting. Background monitoring uses the saved language unless you pass an explicit override. Existing logs and messages received directly from Windows or the authentication server retain their original language.

## Command-line and background modes

For the console monitor, run the setup wizard first from the project directory:

```powershell
python setup_config.py --lang en
python net_monitor.py --lang en
```

The wizard hides password input. Press Enter to keep an existing setting; stop console monitoring with **Ctrl+C**.

For monitoring without a window:

```powershell
python net_monitor_gui.py --daemon --lang en
```

`--daemon-once` runs one real connectivity check and returns `0` if online or `2` if offline. With a fresh one-check run, automatic sign-in is not triggered because reconnection requires two consecutive failures.

To start monitoring automatically after Windows sign-in, use **Settings → Background monitor → Install**. The application first tries a scheduled task, then a per-user startup entry if necessary. Use **Start now** or **Uninstall** in the same section. Uninstall before moving the program, then reinstall from its new location.

Closing the GUI stops its own monitoring. A separately installed background monitor runs independently. Sleep prevention cannot maintain connectivity while the computer is shut down, and cannot prevent campus service outages or network adapter power-saving behavior.

## Configuration and privacy

The GUI creates `net_monitor_config.json` in the program directory. An empty [configuration example](net_monitor_config.example.json) is provided; copy it only if you do not already have a configuration:

```powershell
Copy-Item net_monitor_config.example.json net_monitor_config.json
```

| Setting | Default | Meaning |
| --- | --- | --- |
| `language` | `en` | `en` or `zh-CN` |
| `username`, `password` | empty | Your own campus account credentials |
| `check_interval` | `600` | GUI / background check interval, in seconds; minimum 30 |
| `auto_login_enabled` | `true` | Enable automatic sign-in after repeated failures |
| `reconnect_retries` | `3` | Maximum sign-in attempts; minimum 1 |
| `reconnect_wait_seconds` | `20` | Reconnection wait setting; actual delays vary by retry path |
| `prevent_sleep_enabled` | `true` | Prevent system sleep while monitoring |

GUI and background modes use the program directory; the console monitor and setup wizard use the current working directory. The console interval is controlled by `CHECK_INTERVAL` in `net_monitor.py`.

**Credentials are stored in plain text on your own device.** Keep the configuration private. Configuration files, activity logs, daemon state, executables and old local distribution packages are excluded by `.gitignore`. Remove accounts, passwords, IP addresses and authentication responses before sharing diagnostic output. Use only an account you are authorized to use and follow campus network rules.

The default authentication service is `http://net.szu.edu.cn`, with `ac_id = 12` and the default account domain `@hlw`. These remain defined in the source. The legacy `login_url` configuration field does not replace these constants. Availability in other campus zones depends on their authentication settings.

## Build a Windows executable

From the project directory, using the environment above:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm SZU-Net-Monitor.spec
```

Output: `dist/SZU-Net-Monitor.exe`. The executable supports the same language and background-mode arguments. The existing Chinese-named spec is also available; both builds include the same bilingual code. Keep the executable in a writable directory.

This repository contains current source and required resources. Personal configuration, data, runtime logs and compiled executables remain local.

## Troubleshooting

- **Sign-in fails:** confirm your account works on the official campus portal, check account status and verify that your network uses the configured `ac_id`.
- **A VPN interferes:** add a direct-connection rule for the campus authentication server in your VPN client. Bypassing system proxy settings cannot override every VPN routing policy.
- **Background installation fails:** check the message in Settings and your Windows task / startup permissions.
- **Settings language does not change immediately:** save and restart. If you keep starting with `--lang en`, that argument will override a saved Chinese preference.

## Development and validation

Offline regression checks use synthetic credentials and mocked network calls:

```powershell
python -m unittest discover -s tests -v
```

The tests cover translations and formatting, language precedence, configuration compatibility, hidden password entry, GUI messages, background language selection, and unchanged SRUN payloads across languages. Real campus sign-in and Windows startup-task installation require validation in the target environment.

## License and acknowledgements

[MIT License](LICENSE). SRUN implementation reference: [lossinwind/szu-auto-login](https://github.com/lossinwind/szu-auto-login).

Campus logo resources belong to their respective rights holders and do not imply official endorsement. Report issues through [GitHub Issues](https://github.com/libwszu/netdetect/issues), with private information removed.
