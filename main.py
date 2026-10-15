# -*- coding: utf-8 -*-
"""Shanyi · 入口：互斥锁 → 装配热键线程 + UI + 托盘。"""
import os
import queue
import sys
import threading

import winapi
from config import VERSION, log
import hotkeys
import ui


def _quit_app():
    """托盘"退出"回调：终止整个进程（所有线程均为 daemon）。"""
    log("托盘请求退出，再见")
    os._exit(0)


def main():
    q: queue.Queue = queue.Queue()
    threading.Thread(target=hotkeys.hotkey_loop, args=(q,), daemon=True).start()
    import tray
    tray.start(on_quit=_quit_app)
    ui.run_ui(q)


if __name__ == "__main__":
    winapi.kernel32.CreateMutexW(None, False, "ShanyiSingle")
    if winapi.last_error() == 183:  # ERROR_ALREADY_EXISTS → 已有实例
        sys.exit(0)
    log(f"=== Shanyi v{VERSION} 启动 ===")
    try:
        main()
    except Exception as e:
        log(f"启动失败: {e!r}")
