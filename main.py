# -*- coding: utf-8 -*-
"""Shanyi · 入口：互斥锁 → 装配热键线程 + UI。"""
import queue
import sys
import threading

import winapi
from config import VERSION, log
import hotkeys
import ui


def main():
    q: queue.Queue = queue.Queue()
    threading.Thread(target=hotkeys.hotkey_loop, args=(q,), daemon=True).start()
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
