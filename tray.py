# -*- coding: utf-8 -*-
"""系统托盘：独立线程 + 自建 Win32 隐藏窗口（不干扰 tkinter 主线程）。

启动气泡告知用户"活着"；左键再弹气泡；右键退出；零依赖纯 ctypes。
x64 注意：WPARAM/LPARAM 均为 8 字节，回调与 MSG 结构体必须按 64 位声明；
WNDPROC 回调对象必须保全局引用，否则被 GC 后变野指针、线程静默崩溃。
"""
from __future__ import annotations
import ctypes
import threading

from config import FLAG_PATH, VERSION, log

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIM_ICON, NIM_TIP, NIF_INFO = 0x01, 0x02, 0x04, 0x10
NIIF_INFO = 0x01
WM_APP_TRAY = 0x8000          # uCallbackMessage
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_DESTROY = 0x0002

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# ---------- 64 位句柄原型（返回值必须显式声明，默认 c_int 会截断） ----------
kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]

user32.CreateWindowExW.restype = ctypes.c_void_p
user32.CreateWindowExW.argtypes = [
    ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
user32.DefWindowProcW.restype = ctypes.c_longlong
user32.DefWindowProcW.argtypes = [
    ctypes.c_void_p, ctypes.c_uint, ctypes.c_ulonglong, ctypes.c_longlong]

# WNDPROC: LRESULT(HWND, UINT, WPARAM, LPARAM) — x64 下 WPARAM/LPARAM 8 字节
WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, ctypes.c_void_p, ctypes.c_uint,
    ctypes.c_ulonglong, ctypes.c_longlong)


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint), ("hWnd", ctypes.c_void_p),
        ("uID", ctypes.c_uint), ("uFlags", ctypes.c_uint),
        ("uCallbackMessage", ctypes.c_uint), ("hIcon", ctypes.c_void_p),
        ("szTip", ctypes.c_wchar * 128), ("dwState", ctypes.c_uint),
        ("dwStateMask", ctypes.c_uint), ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", ctypes.c_uint), ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", ctypes.c_uint),
    ]


class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint), ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p), ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p), ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p), ("lpszClassName", ctypes.c_wchar_p),
    ]


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class _MSG(ctypes.Structure):
    # x64: wParam 8 字节无符号、lParam 8 字节有符号；小了会被 GetMessageW 越界写
    _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint),
                ("wParam", ctypes.c_ulonglong), ("lParam", ctypes.c_longlong),
                ("time", ctypes.c_uint),
                ("ptX", ctypes.c_long), ("ptY", ctypes.c_long)]


class _ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", ctypes.c_int), ("xHotspot", ctypes.c_uint),
                ("yHotspot", ctypes.c_uint), ("hbmMask", ctypes.c_void_p),
                ("hbmColor", ctypes.c_void_p)]


_on_quit_cb = None
_wndproc_ref = None   # 保住回调对象不被 GC（关键！局部临时对象会被回收）


def _make_icon():
    """16x16 图标：深底 + 薄荷绿「闪」字（程序内绘制，无需图标文件）。"""
    hdc = user32.GetDC(None)
    hdc_mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, 16, 16)
    gdi32.SelectObject(hdc_mem, bmp)
    brush = gdi32.CreateSolidBrush(0x212121)          # #212121 DeepL 深色
    rect = _RECT(0, 0, 16, 16)
    user32.FillRect(ctypes.c_void_p(hdc_mem), ctypes.byref(rect), brush)
    font = gdi32.CreateFontW(-12, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0,
                             "Microsoft YaHei UI")
    gdi32.SelectObject(hdc_mem, font)
    gdi32.SetBkMode(hdc_mem, 1)                       # TRANSPARENT
    gdi32.SetTextColor(hdc_mem, 0xC9F16C)             # 薄荷绿 #6cf1c9 (BGR)
    rect2 = _RECT(0, 0, 16, 16)                       # DrawTextW 会改写矩形
    user32.DrawTextW(hdc_mem, "闪", -1, ctypes.byref(rect2), 0x25)
    ii = _ICONINFO()
    ii.fIcon = 1
    ii.hbmColor = bmp
    ii.hbmMask = gdi32.CreateBitmap(16, 16, 1, 1, None)
    hicon = user32.CreateIconIndirect(ctypes.byref(ii))
    user32.ReleaseDC(None, hdc)
    return hicon


def _show_balloon(nid, title, text):
    nid.uFlags |= NIF_INFO
    nid.szInfoTitle = title
    nid.szInfo = text
    nid.dwInfoFlags = NIIF_INFO
    ok = shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
    if not ok:
        log(f"托盘气泡失败 err={ctypes.GetLastError()}")


def start(on_quit):
    """启动托盘线程。on_quit: 用户点"退出"时回调。"""
    threading.Thread(target=_run, args=(on_quit,), daemon=True,
                     name="tray").start()


def _run(on_quit):
    try:
        _run_inner(on_quit)
    except Exception as e:
        # 托盘崩溃绝不能静默——上次就是这个坑：线程死了日志却一片干净
        log(f"托盘线程异常: {e!r}")


def _run_inner(on_quit):
    global _on_quit_cb, _wndproc_ref
    _on_quit_cb = on_quit

    wc = _WNDCLASSW()
    wc_name = "ShanyiTray"
    _wndproc_ref = WNDPROC(_wndproc)          # 全局引用防 GC
    wc.lpfnWndProc = ctypes.cast(_wndproc_ref, ctypes.c_void_p).value
    wc.lpszClassName = wc_name
    wc.hInstance = kernel32.GetModuleHandleW(None)
    if not user32.RegisterClassW(ctypes.byref(wc)):
        log(f"托盘 RegisterClassW 失败 err={ctypes.GetLastError()}")
        return

    hwnd = user32.CreateWindowExW(
        0, wc_name, "Shanyi", 0, 0, 0, 0, 0, None, None,
        wc.hInstance, None)
    if not hwnd:
        log(f"托盘 CreateWindowExW 失败 err={ctypes.GetLastError()}")
        return

    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIM_ICON | NIM_TIP
    nid.uCallbackMessage = WM_APP_TRAY
    nid.hIcon = _make_icon()
    nid.szTip = f"Shanyi 闪译 v{VERSION} — Alt+T 划词 | Alt+O 截图"
    if not nid.hIcon:
        log("托盘图标绘制失败（CreateIconIndirect 返回空）")
    ok = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
    log(f"托盘图标 NIM_ADD → {bool(ok)}")
    if ok:
        _show_balloon(nid, "Shanyi 已启动", "Alt+T 划词翻译 · Alt+O 截图 OCR")

    msg = _MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))


def _wndproc(hwnd, msg, wparam, lparam):
    if msg == WM_APP_TRAY:
        if lparam == WM_RBUTTONUP:
            # 用户请求退出：写标记 + 通知主程序
            FLAG_PATH.write_text("user quit", encoding="utf-8")
            if _on_quit_cb:
                _on_quit_cb()
            return 0
        if lparam == WM_LBUTTONUP:
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.hWnd = hwnd
            nid.uID = 1
            _show_balloon(nid, "Shanyi 运行中",
                          "Alt+T 划词翻译\nAlt+O 截图 OCR\nCtrl+Alt+X 退出")
            return 0
    elif msg == WM_DESTROY:
        user32.PostQuitMessage(0)
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
