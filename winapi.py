# -*- coding: utf-8 -*-
"""WinAPI 绑定：全部 ctypes 声明集中于此（restype/argtypes 一个不漏）。

教训（都是真实踩过的）：
- 64 位句柄不声明 restype 会被截断成 32 位 → access violation
- 句柄作参数不声明 argtypes → OverflowError: int too long to convert
"""
import ctypes
import ctypes.wintypes as wt

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# ---- 返回类型 ----
user32.GetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.restype = ctypes.c_void_p
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.restype = ctypes.c_int
kernel32.CreateMutexW.restype = ctypes.c_void_p

# ---- 参数类型 ----
kernel32.GlobalAlloc.argtypes = [wt.UINT, ctypes.c_size_t]
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.SetClipboardData.argtypes = [wt.UINT, ctypes.c_void_p]
user32.GetClipboardData.argtypes = [wt.UINT]
user32.OpenClipboard.argtypes = [wt.HWND]


def last_error() -> int:
    """正确的 GetLastError：kernel32.GetLastError() 在 ctypes 下返回陈旧值。"""
    return ctypes.GetLastError()
