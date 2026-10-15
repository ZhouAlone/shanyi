# -*- coding: utf-8 -*-
"""取词（剪贴板法）与屏幕截图（GDI → PNG，纯标准库编码）。"""
from __future__ import annotations
import base64
import ctypes
import ctypes.wintypes as wt
import time

from config import (CF_UNICODETEXT, GMEM_MOVEABLE, KEYEVENTF_KEYUP,
                    PROCESS_QUERY_LIMITED_INFORMATION, SRCCOPY, VK_C, VK_CTRL,
                    VK_SHIFT, log)
import winapi

user32, kernel32, gdi32 = winapi.user32, winapi.kernel32, winapi.gdi32

TERMINALS = ("windowsterminal", "conhost", "cmd.exe", "powershell",
             "putty", "wezterm", "alacritty", "mintty")


# ================= 剪贴板 =================
def _clipboard_text():
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        return ctypes.wstring_at(h) if h else None
    finally:
        user32.CloseClipboard()


def _set_clipboard_text(s: str):
    if not user32.OpenClipboard(None):
        return
    try:
        user32.EmptyClipboard()
        buf = ctypes.create_unicode_buffer(s)
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, ctypes.sizeof(buf))
        p = kernel32.GlobalLock(h)
        ctypes.memmove(p, buf, ctypes.sizeof(buf))
        kernel32.GlobalUnlock(h)
        user32.SetClipboardData(CF_UNICODETEXT, h)
    finally:
        user32.CloseClipboard()


def _foreground_exe() -> str:
    hwnd = user32.GetForegroundWindow()
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not proc:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(512)
        size = wt.DWORD(512)
        kernel32.QueryFullProcessImageNameW(proc, 0, buf, ctypes.byref(size))
        return buf.value.lower()
    finally:
        kernel32.CloseHandle(proc)


def _press_copy_keys():
    """模拟复制：普通应用 Ctrl+C；终端类 Ctrl+Shift+C"""
    terminal = any(k in _foreground_exe() for k in TERMINALS)
    keys = [(VK_CTRL, True)]
    if terminal:
        keys.append((VK_SHIFT, True))
    keys += [(VK_C, True), (VK_C, False)]
    if terminal:
        keys.append((VK_SHIFT, False))
    keys.append((VK_CTRL, False))
    for vk, down in keys:
        user32.keybd_event(vk, 0, 0 if down else KEYEVENTF_KEYUP, 0)


def _wait_modifiers_released(timeout: float = 1.0) -> bool:
    """等物理修饰键（Alt 等）全部松开——否则模拟的 Ctrl+C 被污染成组合键"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not (user32.GetAsyncKeyState(0x12) & 0x8000      # Alt
                or user32.GetAsyncKeyState(VK_CTRL) & 0x8000
                or user32.GetAsyncKeyState(VK_SHIFT) & 0x8000):
            return True
        time.sleep(0.03)
    return False


def capture_selection() -> str | None:
    """模拟复制拿到选区文本，并还原原剪贴板。"""
    _wait_modifiers_released()
    old = _clipboard_text()
    seq0 = user32.GetClipboardSequenceNumber()
    _press_copy_keys()
    text = None
    for _ in range(25):  # 最长约 500ms
        time.sleep(0.02)
        if user32.GetClipboardSequenceNumber() != seq0:
            text = _clipboard_text()
            break
    if old is not None:
        _set_clipboard_text(old)
    return text


def mouse_pos():
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


# ================= PNG 编码（纯函数，可单测） =================
def pixels_to_png(bmp_data: bytes, w: int, h: int) -> bytes:
    """24 位 top-down BGR 像素（行 4 字节对齐）→ PNG。

    PNG 整数全部大端：长度、CRC 错一个字节服务器就 400。
    """
    import zlib
    row = ((24 * w + 31) // 32) * 4
    raw = bytearray()
    for y in range(h):
        r0 = y * row
        line = bytearray(bmp_data[r0:r0 + 3 * w])
        line[0::3], line[2::3] = line[2::3], line[0::3]  # BGR→RGB（切片赋值，C 速度）
        raw += b"\x00" + line               # filter: None

    def mk_chunk(typ: bytes, payload: bytes) -> bytes:
        return (len(payload)).to_bytes(4, "big") + typ + payload \
            + zlib.crc32(typ + payload).to_bytes(4, "big")

    ihdr = (w).to_bytes(4, "big") + (h).to_bytes(4, "big") + bytes((8, 2, 0, 0, 0))
    return (b"\x89PNG\r\n\x1a\n" + mk_chunk(b"IHDR", ihdr)
            + mk_chunk(b"IDAT", zlib.compress(bytes(raw), 1))
            + mk_chunk(b"IEND", b""))


# ================= 屏幕截图 =================
MIN_OCR_SIDE = 64   # DeepSeek-OCR 要求宽高均 >28px；细面条区域需扩边


def expand_region(x, y, w, h, screen_w, screen_h, min_side=MIN_OCR_SIDE):
    """过窄/过矮的框选区域居中扩展到 min_side，并夹回屏幕内。"""
    w, h = max(1, w), max(1, h)
    if w < min_side:
        x = x - (min_side - w) // 2
        w = min_side
    if h < min_side:
        y = y - (min_side - h) // 2
        h = min_side
    x = max(0, min(x, screen_w - w))
    y = max(0, min(y, screen_h - h))
    w = min(w, screen_w)
    h = min(h, screen_h)
    return x, y, w, h


class _BMIH(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD),
                ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


class _BMI(ctypes.Structure):
    _fields_ = [("bmiHeader", _BMIH), ("bmiColors", wt.DWORD * 3)]


def capture_screen_region(x, y, w, h) -> str | None:
    """GDI 截屏指定区域，返回 PNG 的 base64。"""
    try:
        w, h = max(1, w), max(1, h)
        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
        gdi32.SelectObject(hdc_mem, hbm)
        gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, x, y, SRCCOPY)
        row = ((24 * w + 31) // 32) * 4
        bmi = _BMI()
        bmi.bmiHeader.biSize = ctypes.sizeof(_BMIH)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h          # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 24
        bmi.bmiHeader.biCompression = 0      # BI_RGB
        buf = ctypes.create_string_buffer(row * h)
        gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, ctypes.byref(bmi), 0)
        user32.ReleaseDC(0, hdc_screen)
        gdi32.DeleteDC(hdc_mem)
        gdi32.DeleteObject(hbm)
        return base64.b64encode(pixels_to_png(buf.raw, w, h)).decode()
    except Exception as e:
        log(f"截屏失败: {e!r}")
        return None

