# -*- coding: utf-8 -*-
"""UI：译文弹窗（DeepL 深色风）+ OCR 框选遮罩 + 消息轮询。"""
from __future__ import annotations
import queue
import tkinter as tk

from config import CONF, log


def run_ui(q: queue.Queue):
    root = tk.Tk()
    root.withdraw()
    st = {"popup": None, "hovered": False, "job": None}

    def close_popup():
        if st["popup"]:
            try:
                st["popup"].destroy()
            except Exception:
                pass
            st["popup"] = None

    def show(x, y, text, final=True):
        close_popup()
        pop = tk.Toplevel(root)
        st["popup"] = pop
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        # DeepL 深色规范：#212121 表面 + 1px #3D3D3D 描边分层（替代投影）
        frame = tk.Frame(pop, bg="#212121", highlightthickness=1,
                         highlightbackground="#3D3D3D")
        frame.pack(padx=1, pady=1)
        tk.Label(frame, text=text, bg="#212121", fg="#eaeaea", justify="left",
                 wraplength=480, font=("Microsoft YaHei UI", 10),
                 padx=14, pady=11).pack()
        pop.update_idletasks()
        sw, sh = pop.winfo_screenwidth(), pop.winfo_screenheight()
        x = min(x + 18, sw - pop.winfo_width() - 8)
        y = min(y + 20, sh - pop.winfo_height() - 8)
        pop.geometry(f"+{max(4, x)}+{max(4, y)}")

        if not final:
            # 进度 toast（⏳）：只显示不交互——鼠标挪开不关、不自动关，
            # 一直挂到被结果消息替换为止，避免框选后出现"真空期"
            return

        def close():
            try:
                pop.destroy()
            except Exception:
                pass

        def on_enter(e=None):
            st["hovered"] = True
            if st["job"]:                       # 悬停期间：取消自动关闭
                try:
                    root.after_cancel(st["job"])
                except Exception:
                    pass
                st["job"] = None

        def on_leave(e=None):
            st["hovered"] = False
            root.after(150, lambda: (not st["hovered"]) and close())

        # 右上角按钮：📋 复制（仅最终译文） + ✕ 关闭
        def mk_btn(txt, cmd):
            b = tk.Label(frame, text=txt, bg="#212121", fg="#8a8a8a",
                         font=("Segoe UI Symbol", 10), padx=6, pady=2, cursor="hand2")

            def cmd_break(e=None):
                cmd(e)
                return "break"                 # 阻断冒泡到弹窗的拖动/关闭逻辑

            b.bind("<Button-1>", cmd_break)
            b.bind("<Enter>", lambda e: b.configure(fg="#eaeaea", bg="#333333"))
            b.bind("<Leave>", lambda e: b.configure(fg="#8a8a8a", bg="#212121"))
            b.bind("<Enter>", on_enter, add="+")
            b.bind("<Leave>", on_leave, add="+")
            return b

        bar = tk.Frame(pop, bg="#212121")
        bar.place(relx=1.0, x=-2, y=2, anchor="ne")
        if final:
            def copy_text(e=None):
                try:
                    from capture import _set_clipboard_text
                    _set_clipboard_text(text)
                    btn_copy.configure(text="✓", fg="#6cf1c9")   # DeepL 薄荷绿
                    pop.after(1200, lambda: btn_copy.configure(text="📋"))
                    pop.after(1200, lambda: btn_copy.configure(fg="#8a8a8a"))
                except Exception:
                    pass
            btn_copy = mk_btn("📋", copy_text)
            btn_copy.pack(side="left", padx=(0, 2))
        btn_x = mk_btn("✕", lambda e: close())
        btn_x.pack(side="left")

        pop.bind("<Enter>", on_enter)
        pop.bind("<Leave>", on_leave)

        # 拖动移动：按住拖 → 跟随；轻点（<5px）→ 关闭；拖动 = 取消自动关闭
        drag = [None, False]

        def on_press(e):
            drag[0] = (e.x_root, e.y_root, pop.winfo_x(), pop.winfo_y())
            drag[1] = False

        def on_motion(e):
            if drag[0] is None:
                return
            dx, dy = e.x_root - drag[0][0], e.y_root - drag[0][1]
            if abs(dx) + abs(dy) >= 5:
                drag[1] = True
                on_enter()
            pop.geometry(f"+{drag[0][2] + dx}+{drag[0][3] + dy}")

        def on_release(e):
            if drag[0] is not None and not drag[1]:
                close()
            drag[0] = None

        pop.bind("<Button-1>", on_press)
        pop.bind("<B1-Motion>", on_motion)
        pop.bind("<ButtonRelease-1>", on_release)
        st["job"] = root.after(CONF["popup_seconds"] * 1000, close)

    def show_overlay():
        # 全屏半透明遮罩，拖矩形框选 → 启动 OCR
        ov = tk.Toplevel(root)
        ov.overrideredirect(True)
        ov.attributes("-topmost", True)
        ov.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
        ov.attributes("-alpha", 0.25)
        cv = tk.Canvas(ov, bg="black", highlightthickness=0, cursor="crosshair")
        cv.pack(fill="both", expand=True)
        st["drag0"] = None

        def on_press(e):
            st["drag0"] = (e.x_root, e.y_root)
            st["box"] = cv.create_rectangle(e.x, e.y, e.x, e.y,
                                            outline="#0A84FF", width=2)

        def on_motion(e):
            if st["drag0"]:
                cv.coords(st["box"], st["drag0"][0], st["drag0"][1],
                          e.x_root, e.y_root)

        def on_release(e):
            if not st["drag0"]:
                return
            x0, y0 = st["drag0"]
            st["drag0"] = None
            ov.destroy()
            x, y = min(x0, e.x_root), min(y0, e.y_root)
            w, h = abs(e.x_root - x0), abs(e.y_root - y0)
            if w > 8 and h > 8:
                # 细面条区域（单行文字）扩到 OCR 最小尺寸，否则服务器 400
                from capture import expand_region
                x, y, w, h = expand_region(
                    x, y, w, h, root.winfo_screenwidth(),
                    root.winfo_screenheight(), CONF.get("ocr_min_side", 64))
                import threading
                from hotkeys import ocr_worker
                threading.Thread(target=ocr_worker, args=(q, x, y, w, h),
                                 daemon=True).start()

        cv.bind("<Button-1>", on_press)
        cv.bind("<B1-Motion>", on_motion)
        cv.bind("<ButtonRelease-1>", on_release)
        ov.bind("<Escape>", lambda e: ov.destroy())
        ov.focus_force()

    def poll():
        try:
            while True:
                item = q.get_nowait()
                if item[0] == "select":
                    show_overlay()
                elif item[0] == "msg":
                    _, x, y, text, final = item
                    show(x, y, text, final)
        except queue.Empty:
            pass
        except Exception as e:
            log(f"poll 异常（消息已跳过）: {e!r}")
        root.after(150, poll)

    poll()
    root.mainloop()
