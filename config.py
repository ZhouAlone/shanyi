# -*- coding: utf-8 -*-
"""Shanyi 配置：用户配置（JSON）+ AI 云配置。"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# 用户数据放包外 %LOCALAPPDATA%\Shanyi，代码目录保持干净
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Shanyi"
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass  # 目录建不出来也不拦启动：宁可无日志/无配置持久化也要能跑
CONF_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "shanyi.log"
# 用户主动退出的标记：托盘/热键退出时写入；手动启动时清除
FLAG_PATH = DATA_DIR / "exited.flag"

# WinAPI 常量
WM_HOTKEY = 0x0312
MOD_MAP = {"ALT": 0x0001, "CTRL": 0x0002, "SHIFT": 0x0004, "WIN": 0x0008}
VK_CTRL, VK_SHIFT, VK_MENU, VK_C = 0x11, 0x10, 0x12, 0x43
KEYEVENTF_KEYUP = 0x0002
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
SRCCOPY = 0x00CC0020
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ERROR_ALREADY_EXISTS = 183

# 队列消息：(kind, ...)，kind ∈ {MSG_SHOW, MSG_SELECT}
MSG_SHOW = "msg"
MSG_SELECT = "select"

DEFAULT_CONF = {
    "hotkey_translate": {"mods": ["ALT"], "key": "T"},
    "hotkey_explain": {"mods": ["ALT"], "key": "E"},
    "hotkey_ocr": {"mods": ["ALT"], "key": "O"},
    "hotkey_quit": {"mods": ["CTRL", "ALT"], "key": "X"},
    "popup_seconds": 10,
    "max_chars": 6000,
    "explain_max_tokens": 1000,
    "max_output_tokens": 8000,   # 长文翻译的输出预算上限（随输入自动伸缩）
    "http_timeout": 40,
    "ocr_min_side": 64,
    "cloud": {
        "base_url": "",
        "model": "",
        "ocr_model": "deepseek-ai/DeepSeek-OCR",
        "api_key": "",
        "api_key_env": "",
    },
}

VERSION = "0.1.0"

CONF: dict = dict(DEFAULT_CONF)
_HOTKEYS: dict = {}


_log_warned = False


def log(msg: str):
    """写运行日志。写失败只吞掉、绝不抛错：日志只是附属品。

    曾因开机瞬间 shanyi.log 被外部进程短暂锁定（PermissionError [Errno 13]）
    把整个程序崩掉 → 开机自启失败。任何持久化写入都不值得为之崩溃。
    """
    import datetime
    global _log_warned
    line = f"[{datetime.datetime.now():%m-%d %H:%M:%S}] {msg}\n"
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        if not _log_warned:  # 只提示一次，避免每次 log 刷屏
            _log_warned = True
            try:
                print(f"Shanyi: 日志不可写，后续日志跳过: {e!r}", file=sys.stderr)
            except OSError:
                pass


def write_flag(text: str):
    """写用户退出标记（exited.flag）。同理：失败绝不致命。"""
    try:
        FLAG_PATH.write_text(text, encoding="utf-8")
    except OSError as e:
        log(f"退出标记写入失败: {e!r}")


def _hotkey_code(spec: dict) -> tuple[int, int]:
    mods = 0
    for m in spec.get("mods", []):
        mods |= MOD_MAP.get(m.upper(), 0)
    key = str(spec.get("key", "T")).upper()
    code = 0x6F + int(key[1:]) if key.startswith("F") and key[1:].isdigit() else ord(key)
    return mods, code


def _load_conf():
    global CONF, _HOTKEYS
    conf = json.loads(json.dumps(DEFAULT_CONF))  # deep copy
    if CONF_PATH.exists():
        try:
            disk = json.loads(CONF_PATH.read_text(encoding="utf-8"))
            for k, v in disk.items():
                if k == "cloud":
                    conf["cloud"] = {**conf["cloud"], **v}
                elif k in conf:
                    conf[k] = v
        except Exception as e:
            log(f"配置解析失败，用默认: {e}")
    else:
        try:
            CONF_PATH.write_text(json.dumps(conf, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        except OSError as e:
            log(f"默认配置写入失败（用内存配置继续）: {e!r}")
    CONF = conf
    _HOTKEYS = {name: _hotkey_code(spec) for name, spec in
                (("translate", CONF["hotkey_translate"]),
                 ("explain", CONF["hotkey_explain"]),
                 ("ocr", CONF["hotkey_ocr"]),
                 ("quit", CONF["hotkey_quit"]))}


_load_conf()  # import 即生效：hotkeys.py 的 from-import 依赖 import 时就绪的值


def hotkey_id(name: str) -> tuple[int, int]:
    return _HOTKEYS[name]


def hotkey_label() -> str:
    t = CONF["hotkey_translate"]
    return "+".join(t["mods"]).upper() + "+" + str(t["key"]).upper()


def load_cloud() -> tuple[str, str, str]:
    """返回 (base_url, model, api_key)，全部来自 config.json 的 cloud 段；
    api_key 可留空改用 api_key_env 指定的环境变量。"""
    c = CONF["cloud"]
    base = c.get("base_url") or ""
    model = c.get("model") or ""
    api_key = c.get("api_key") or ""
    if not api_key and c.get("api_key_env"):
        api_key = os.environ.get(c["api_key_env"], "")
    return base.rstrip("/"), model, api_key
