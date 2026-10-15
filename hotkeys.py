# -*- coding: utf-8 -*-
"""热键注册、消息循环与工作线程。"""
import ctypes
import ctypes.wintypes as wt
import os
import queue
import threading

import api
from capture import capture_selection, capture_screen_region, mouse_pos
from config import (CONF, FLAG_PATH, MSG_SELECT, MSG_SHOW, WM_HOTKEY, log)
import winapi


def translate_worker(q: queue.Queue):
    x, y = mouse_pos()
    q.put((MSG_SHOW, x, y, "⏳ 翻译中…", False))
    try:
        text = capture_selection()
        if not text or not text.strip():
            q.put((MSG_SHOW, x, y, "⚠️ 未获取到选中文本", True))
            return
        text = text.strip()
        if len(text) > CONF["max_chars"]:
            q.put((MSG_SHOW, x, y, f"⚠️ 选区过长（>{CONF['max_chars']} 字符）", True))
            return
        log(f"翻译 {len(text)} 字符: {text[:40]}…")
        result = api.translate(text)
        log(f"译文: {result[:60]}")
        q.put((MSG_SHOW, x, y, result, True))
    except Exception as e:
        log(f"错误: {e!r}")
        q.put((MSG_SHOW, x, y, f"❌ {e}", True))


def ocr_worker(q: queue.Queue, sx: int, sy: int, sw: int, sh: int):
    """框选区域 → 截屏 → OCR → 翻译 → 弹窗"""
    q.put((MSG_SHOW, sx, sy, "⏳ 识别文字中…", False))
    try:
        b64 = capture_screen_region(sx, sy, sw, sh)
        if not b64:
            q.put((MSG_SHOW, sx, sy, "⚠️ 截屏失败", True))
            return
        text = api.ocr(b64)
        if not text:
            q.put((MSG_SHOW, sx, sy, "⚠️ 未识别到文字", True))
            return
        log(f"OCR 识别 {len(text)} 字符: {text[:40]}…")
        result = api.translate(text)
        log(f"OCR 译文: {result[:60]}")
        q.put((MSG_SHOW, sx, sy, result, True))
    except Exception as e:
        log(f"OCR 错误: {e!r}")
        q.put((MSG_SHOW, sx, sy, f"❌ {e}", True))


def hotkey_loop(q: queue.Queue):
    """热键注册 + 消息循环（本线程阻塞等待消息）。"""
    from config import hotkey_id, hotkey_label
    hm, hk = hotkey_id("translate")
    om, ok_ = hotkey_id("ocr")
    qm, qk = hotkey_id("quit")
    if not winapi.user32.RegisterHotKey(None, 1, hm, hk):
        log(f"热键 {hotkey_label()} 注册失败，可能被占用")
        os._exit(1)
    winapi.user32.RegisterHotKey(None, 2, qm, qk)
    winapi.user32.RegisterHotKey(None, 3, om, ok_)
    log(f"已启动：{hotkey_label()} 翻译 / Alt+O 屏幕取词 / Ctrl+Alt+X 退出")

    msg = wt.MSG()
    while winapi.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY and msg.wParam == 1:
            threading.Thread(target=translate_worker, args=(q,), daemon=True).start()
        elif msg.message == WM_HOTKEY and msg.wParam == 2:
            log("收到退出热键，再见")
            FLAG_PATH.write_text("user quit", encoding="utf-8")
            os._exit(0)
        elif msg.message == WM_HOTKEY and msg.wParam == 3:
            q.put((MSG_SELECT, 0, 0, "", False))
