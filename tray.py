# -*- coding: utf-8 -*-
"""系统托盘：独立线程 + 自建 Win32 隐藏窗口（不干扰 tkinter 主线程）。

启动气泡告知用户"活着"；左键再弹气泡；右键菜单退出；零依赖纯 ctypes。
"""
import ctypes
import threading

from config import FLAG_PATH, VERSION

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIM_ICON, NIM_TIP, NIF_INFO = 0x01, 0x02, 0x04, 0x10
NIIF_INFO = 0x01
WM_APP_TRAY = 0x8000          # uCallbackMessage
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
ID_QUIT = 1000
CS_HREDRAW, CS_VREDRAW = 0x0002, 0x0001


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


user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

WNDPROC = ctypes.WNDPROC if hasattr(ctypes, "WNDPROC") else (
    ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_void_p, ctypes.c_uint,
                       ctypes.c_uint, ctypes.c_longlong))

_quit_event = threading.Event()


def _make_icon():
    """16x16 图标：深底 + 薄荷绿「闪」字（程序内绘制，无需图标文件）。"""
    hdc = user32.GetDC(None)
    hdc_mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, 16, 16)
    gdi32.SelectObject(hdc_mem, bmp)
    brush = gdi32.CreateSolidBrush(0x212121)          # #212121 DeepL 深色
    rect = _RECT(0, 0, 16, 16)
    user32.FillRect(ctypes.c_void_p(hdc_mem), ctypes.byref(rect), brush)
    font = gdi32.CreateFontW(-11, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0,
                             "Microsoft YaHei UI")
    gdi32.SelectObject(hdc_mem, font)
    gdi32.SetBkMode(hdc_mem, 1)                       # TRANSPARENT
    gdi32.SetTextColor(hdc_mem, 0xC9F16C)             # 薄荷绿 #6cf1c9 (BGR)
    user32.DrawTextW(hdc_mem, "闪", -1, ctypes.byref(rect), 0x25)  # 单行+居中
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
    shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))


def start(on_quit):
    """启动托盘线程。on_quit: 用户点"退出"时回调（线程安全，经主线程执行）。"""
    threading.Thread(target=_run, args=(on_quit,), daemon=True).start()


def _run(on_quit):
    # 窗口类
    wc = _WNDCLASSW()
    wc_name = "ShanyiTray"
    wc.lpfnWndProc = ctypes.cast(WNDPROC(_wndproc), ctypes.c_void_p).value
    wc.lpszClassName = wc_name
    wc.hInstance = kernel32.GetModuleHandleW(None)
    user32.RegisterClassW(ctypes.byref(wc))

    global _on_quit_cb
    _on_quit_cb = on_quit

    hwnd = user32.CreateWindowExW(
        0, wc_name, "Shanyi", 0, 0, 0, 0, 0, None, None,
        wc.hInstance, None)
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIM_ICON | NIM_TIP
    nid.uCallbackMessage = WM_APP_TRAY
    nid.hIcon = _make_icon()
    nid.szTip = f"Shanyi 闪译 v{VERSION} — Alt+T 划词 | Alt+O 截图"
    shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
    _show_balloon(nid, "Shanyi 已启动", "Alt+T 划词翻译 · Alt+O 截图 OCR")

    msg = _MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))


class _MSG(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint),
                ("wParam", ctypes.c_uint), ("lParam", ctypes.c_long),
                ("time", ctypes.c_uint),
                ("ptX", ctypes.c_long), ("ptY", ctypes.c_long)]


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


_on_quit_cb = None


class _ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", ctypes.c_int), ("xHotspot", ctypes.c_uint),
                ("yHotspot", ctypes.c_uint), ("hbmMask", ctypes.c_void_p),
                ("hbmColor", ctypes.c_void_p)]
