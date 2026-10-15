# -*- coding: utf-8 -*-
"""Shanyi 配置：用户配置（JSON）+ AI 云配置（TOML 或环境变量）。"""
import json
import os
import tomllib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# 用户数据（配置/日志）默认放包外 %LOCALAPPDATA%\Shanyi，代码目录保持干净
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Shanyi"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONF_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "shanyi.log"
# 迁移：老用户的配置和日志仍在 Tools 目录，原地兼容
LEGACY_CONF = BASE_DIR.parent / "qingjian-huaci.json"
LEGACY_LOG = BASE_DIR.parent / "qingjian-huaci.log"

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
    "hotkey_ocr": {"mods": ["ALT"], "key": "O"},
    "hotkey_quit": {"mods": ["CTRL", "ALT"], "key": "X"},
    "popup_seconds": 10,
    "max_chars": 2000,
    "http_timeout": 20,
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


def log(msg: str):
    import datetime
    line = f"[{datetime.datetime.now():%m-%d %H:%M:%S}] {msg}\n"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)


def _hotkey_code(spec: dict) -> tuple[int, int]:
    mods = 0
    for m in spec.get("mods", []):
        mods |= MOD_MAP.get(m.upper(), 0)
    key = str(spec.get("key", "T")).upper()
    code = 0x6F + int(key[1:]) if key.startswith("F") and key[1:].isdigit() else ord(key)
    return mods, code


def _load_conf():
    global CONF, _HOTKEYS
    conf = dict(DEFAULT_CONF)
    conf["cloud"] = dict(DEFAULT_CONF["cloud"])
    src = CONF_PATH if CONF_PATH.exists() else (
        LEGACY_CONF if LEGACY_CONF.exists() else None)
    if src is None:
        CONF_PATH.write_text(json.dumps(conf, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    else:
        try:
            disk = json.loads(src.read_text(encoding="utf-8"))
            disk.setdefault("cloud", {})
            disk["cloud"].setdefault("base_url", conf["cloud"]["base_url"])
            disk["cloud"].setdefault("model", conf["cloud"]["model"])
            disk["cloud"].setdefault("ocr_model", conf["cloud"]["ocr_model"])
            disk["cloud"].setdefault("api_key", "")
            disk["cloud"].setdefault("api_key_env", "")
            conf.update(disk)
        except Exception as e:
            log(f"配置解析失败，用默认: {e}")
    CONF = conf
    _HOTKEYS = {name: _hotkey_code(spec) for name, spec in
                (("translate", CONF["hotkey_translate"]),
                 ("ocr", CONF["hotkey_ocr"]),
                 ("quit", CONF["hotkey_quit"]))}


_load_conf()  # import 即生效：hotkeys.py 的 from-import 依赖 import 时就绪的值


def hotkey_id(name: str) -> tuple[int, int]:
    return _HOTKEYS[name]


def hotkey_label() -> str:
    t = CONF["hotkey_translate"]
    return "+".join(t["mods"]).upper() + "+" + str(t["key"]).upper()


def load_cloud() -> tuple[str, str, str]:
    """返回 (base_url, model, api_key)。优先 config.json 的 cloud 段；
    其中任一字段缺省时回落到青简 config.toml（装了青简的老用户零配置）。"""
    c = CONF["cloud"]
    base = c.get("base_url") or ""
    model = c.get("model") or ""
    api_key = c.get("api_key") or ""
    if not api_key and c.get("api_key_env"):
        api_key = os.environ.get(c["api_key_env"], "")
    if not model or not api_key or not base:
        try:
            p = tomllib.loads(QJ_CONFIG.read_text(encoding="utf-8"))["predict"]
            base = base or p.get("base_url", "")
            model = model or p.get("model", "")
            api_key = api_key or p.get("api_key", "")
        except Exception:
            pass
    return base.rstrip("/"), model, api_key


QJ_CONFIG = Path(os.environ.get("APPDATA", "")) / "Qingjian" / "config.toml"
