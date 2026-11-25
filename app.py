"""PimPid - ตรวจจับการพิมพ์ผิดภาษา (ลืมเปลี่ยน ไทย/อังกฤษ) บน Windows

รัน: pythonw app.py   (หรือดับเบิลคลิก run.bat)
ตัวเลือก: --background (เปิดแบบซ่อนหน้าต่าง อยู่ใน tray), --install, --uninstall [--silent], --portable
"""
import ctypes
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

import installer
import winhook as w
from detector import judge_text
from layout import key_chars
from ui_style import apply_style
from version import APP_NAME, VERSION

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(installer.DATA_DIR, "config.json")
OLD_CONFIG_PATH = os.path.join(APP_DIR, "config.json")  # เวอร์ชันแรกเก็บไว้ข้างโค้ด

DEFAULT_CONFIG = {
    "enabled": True,
    "auto_fix": False,          # แก้ให้อัตโนมัติเมื่อเคาะ space
    "switch_layout": True,      # เปลี่ยนภาษาแป้นพิมพ์ให้หลังแก้
    "live_check": True,         # เตือนระหว่างพิมพ์ ไม่ต้องรอ space
    "popup_seconds": 8,
    # hotkey สำหรับแก้คำ: Ctrl+Shift+Space (เปลี่ยนได้) และปุ่ม Pause ใช้ได้เสมอ
    "hotkey": {"ctrl": True, "shift": True, "alt": False, "vk": 0x20},
    "idle_reset_seconds": 15,   # ไม่พิมพ์นานเกินนี้ถือว่าเริ่มใหม่ (อาจคลิกเมาส์ย้ายตำแหน่งไปแล้ว)
}

VK_PAUSE = 0x13


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    for path in (CONFIG_PATH, OLD_CONFIG_PATH):
        try:
            with open(path, encoding="utf-8") as f:
                cfg.update(json.load(f))
            break
        except (OSError, ValueError):
            continue
    return cfg


def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def hotkey_label(hk):
    names = {0x20: "Space"}
    parts = [n for n, k in (("Ctrl", "ctrl"), ("Alt", "alt"), ("Shift", "shift")) if hk.get(k)]
    vk = hk.get("vk", 0x20)
    parts.append(names.get(vk, chr(vk) if 0x30 <= vk <= 0x5A else f"VK{vk:02X}"))
    return "+".join(parts)


# =================================================================== engine
class Engine:
    """รับปุ่มจาก hook แล้วเก็บเป็นบัฟเฟอร์คำล่าสุด ตรวจว่าผิดภาษาไหม"""

    def __init__(self, cfg, ui_queue):
        self.cfg = cfg
        self.ui = ui_queue
        self.events = queue.Queue()
        self.caps = w.caps_on()
        self.reset()
        self.suggestion = None  # (n_backspace, text, typed, from_lang)
        self.hook = w.KeyboardHook(self._on_key)
        threading.Thread(target=self._worker, daemon=True, name="engine").start()

    def start(self):
        self.hook.start()

    def stop(self):
        self.hook.stop()

    # ---------- hook thread (ต้องเร็ว)
    def _on_key(self, vk, is_down, flags):
        if flags & w.LLKHF_INJECTED:
            return False
        if not is_down:
            return False
        if vk == w.VK_CAPITAL:
            self.caps = not self.caps
            return False
        if not self.cfg["enabled"]:
            return False
        ctrl, shift = w.key_down(w.VK_CONTROL), w.key_down(w.VK_SHIFT)
        alt = w.key_down(w.VK_MENU)
        win = w.key_down(w.VK_LWIN) or w.key_down(w.VK_RWIN)
        hk = self.cfg["hotkey"]
        is_hotkey = (vk == VK_PAUSE and not (ctrl or alt or shift)) or (
            vk == hk["vk"] and ctrl == hk["ctrl"] and shift == hk["shift"] and alt == hk["alt"] and not win)
        if is_hotkey and self.suggestion:
            if ctrl or shift or alt:
                w.send_mask_key()
            self.events.put(("fix",))
            return True  # กลืนปุ่มนี้
        self.events.put(("key", vk, shift, ctrl, alt, win, self.caps, w.current_lang(), w.foreground_window(),
                         time.time()))
        return False

    # ---------- worker thread
    def reset(self):
        self.en = []
        self.th = []
        self.lang = None
        self.hwnd = None
        self.last_time = 0

    def _set_suggestion(self, s):
        if s != self.suggestion:
            self.suggestion = s
            self.ui.put(("suggest", s))

    def _worker(self):
        while True:
            ev = self.events.get()
            try:
                if ev[0] == "fix":
                    self._do_fix()
                elif ev[0] == "key":
                    self._handle_key(*ev[1:])
                elif ev[0] == "clear":
                    self.reset()
                    self._set_suggestion(None)
            except Exception as e:
                print("engine error:", e)

    def _handle_key(self, vk, shift, ctrl, alt, win, caps, lang, hwnd, t):
        if vk in w.MODIFIER_VKS:
            return
        if hwnd != self.hwnd or t - self.last_time > self.cfg["idle_reset_seconds"]:
            self.reset()
            self.hwnd = hwnd
        self.last_time = t

        if ctrl or alt or win:
            self.reset()
            self.hwnd = hwnd
            self._set_suggestion(None)
            return

        if vk == w.VK_BACK:
            if self.en:
                self.en.pop()
                self.th.pop()
        elif vk == w.VK_SPACE:
            if not self.en:
                return
            self.en.append(" ")
            self.th.append(" ")
        else:
            chars = key_chars(vk, shift, caps)
            if chars is None or lang is None:
                self.reset()
                self.hwnd = hwnd
                self._set_suggestion(None)
                return
            if self.lang is not None and lang != self.lang:
                self.reset()
                self.hwnd = hwnd
            self.lang = lang
            self.en.append(chars[0])
            self.th.append(chars[1])

        # เก็บแค่ช่วงท้าย ๆ พอ
        if len(self.en) > 80:
            del self.en[:-80]
            del self.th[:-80]

        if not self.en or self.lang is None:
            self._set_suggestion(None)
            return

        en, th = "".join(self.en), "".join(self.th)
        word_done = en.endswith(" ")
        if not word_done and not self.cfg["live_check"]:
            return
        r = judge_text(en, th, self.lang, partial=not word_done)
        if r is None:
            self._set_suggestion(None)
            return
        n, text, _ = r
        typed = (en if self.lang == "en" else th)[-n:]
        self._set_suggestion((n, text, typed, self.lang))
        if word_done and self.cfg["auto_fix"]:
            self._do_fix()

    def _do_fix(self):
        s = self.suggestion
        if not s:
            return
        n, text, typed, from_lang = s
        if w.foreground_window() != self.hwnd:
            self._set_suggestion(None)
            return
        w.wait_modifiers_released()
        w.replace_text(n, text)
        if self.cfg["switch_layout"]:
            w.switch_lang("th" if from_lang == "en" else "en")
        self.reset()
        self._set_suggestion(None)
        self.ui.put(("fixed", typed, text))


# =================================================================== UI
GWL_EXSTYLE = -20
WS_EX_TOPMOST, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x8, 0x80, 0x08000000
SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x10, 0x40
SW_HIDE = 0
HWND_TOPMOST = -1
u32 = ctypes.windll.user32
u32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, ctypes.c_uint]
u32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
u32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
u32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
u32.GetParent.restype = ctypes.c_void_p
u32.GetParent.argtypes = [ctypes.c_void_p]
u32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]

BG, FG, ACCENT, MUTED = "#1f2430", "#f2f4f8", "#ffcc66", "#9aa3b5"


class Popup:
    """หน้าต่างแจ้งเตือนเล็ก ๆ ที่ไม่แย่งโฟกัสจากแอปที่กำลังพิมพ์"""

    def __init__(self, root, on_click, fam):
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.configure(bg=BG)
        frame = tk.Frame(self.top, bg=BG, padx=14, pady=10, highlightthickness=1, highlightbackground="#3a4255")
        frame.pack()
        self.title = tk.Label(frame, text="ลืมเปลี่ยนภาษาหรือเปล่า?", bg=BG, fg=MUTED, font=(fam, 9))
        self.title.pack(anchor="w")
        row = tk.Frame(frame, bg=BG)
        row.pack(anchor="w", pady=(2, 4))
        self.typed = tk.Label(row, bg=BG, fg=MUTED, font=(fam, 11, "overstrike"))
        self.typed.pack(side="left")
        tk.Label(row, text="  →  ", bg=BG, fg=MUTED, font=(fam, 11)).pack(side="left")
        self.fixed = tk.Label(row, bg=BG, fg=ACCENT, font=(fam, 15, "bold"))
        self.fixed.pack(side="left")
        self.hint = tk.Label(frame, bg=BG, fg=MUTED, font=(fam, 9))
        self.hint.pack(anchor="w")
        for wdg in (self.top, frame, row, self.typed, self.fixed, self.hint, self.title):
            wdg.bind("<Button-1>", lambda e: on_click())
        self.top.update_idletasks()
        self.hwnd = u32.GetParent(self.top.winfo_id()) or self.top.winfo_id()
        style = u32.GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
        u32.SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE, style | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        self.hide()
        self._hide_job = None

    def show(self, typed, fixed, hint, seconds):
        self.typed.config(text=typed.strip())
        self.fixed.config(text=fixed.strip())
        self.hint.config(text=hint)
        self.top.update_idletasks()
        wd, ht = self.top.winfo_reqwidth(), self.top.winfo_reqheight()
        x, y = self._place(wd, ht)
        u32.SetWindowPos(self.hwnd, HWND_TOPMOST, x, y, wd, ht, SWP_NOACTIVATE | SWP_SHOWWINDOW)
        if self._hide_job:
            self.top.after_cancel(self._hide_job)
        self._hide_job = self.top.after(int(seconds * 1000), self.hide)

    @staticmethod
    def _place(wd, ht):
        """หาตำแหน่งป๊อปอัป: ใต้เคอร์เซอร์พิมพ์ > ข้างเมาส์ (ถ้าอยู่ในหน้าต่างที่พิมพ์) > มุมขวาล่าง"""
        gap = 6
        caret = w.caret_rect()
        if caret:
            cx, ctop, cbottom = caret
            l, t, r, b = w.work_area(cx, cbottom)
            x, y = cx - 8, cbottom + gap
            if y + ht > b:  # ล้นขอบล่าง ย้ายไปไว้เหนือบรรทัดที่พิมพ์
                y = ctop - ht - gap
        else:
            mx, my = w.cursor_pos()
            fl, ft, fr, fb = w.foreground_rect()
            l, t, r, b = w.work_area(mx, my)
            if fl <= mx <= fr and ft <= my <= fb:
                x, y = mx + 16, my + 22
                if y + ht > b:
                    y = my - ht - 12
            else:
                l, t, r, b = w.work_area((fl + fr) // 2, (ft + fb) // 2)
                x, y = r - wd - 24, b - ht - 24
        x = max(l, min(x, r - wd))
        y = max(t, min(y, b - ht))
        return x, y

    def hide(self):
        u32.ShowWindow(self.hwnd, SW_HIDE)


k32 = ctypes.windll.kernel32
k32.CreateEventW.restype = ctypes.c_void_p
k32.CreateMutexW.restype = ctypes.c_void_p
k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]


class Tray:
    """ไอคอนที่มุมขวาล่าง (system tray) ให้แอปทำงานเบื้องหลังได้"""

    def __init__(self, app):
        import pystray
        from icon import make_icon

        self._make_icon = make_icon
        q = app.ui_queue
        menu = pystray.Menu(
            pystray.MenuItem("เปิดหน้าต่าง PimPid", lambda: q.put(("show",)), default=True),
            pystray.MenuItem("กำลังตรวจ", lambda: q.put(("toggle",)), checked=lambda item: app.cfg["enabled"]),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("ออกจากโปรแกรม", lambda: q.put(("quit",))),
        )
        self.icon = pystray.Icon(APP_NAME, make_icon(64, app.cfg["enabled"]), self._title(app.cfg["enabled"]), menu)
        self.icon.run_detached()

    @staticmethod
    def _title(enabled):
        return f"{APP_NAME} — " + ("กำลังตรวจการพิมพ์" if enabled else "หยุดชั่วคราว")

    def set_enabled(self, enabled):
        self.icon.icon = self._make_icon(64, enabled)
        self.icon.title = self._title(enabled)
        self.icon.update_menu()

    def notify(self, text):
        try:
            self.icon.notify(text, APP_NAME)
        except Exception:
            pass

    def stop(self):
        try:
            self.icon.stop()
        except Exception:
            pass


class App:
    def __init__(self, background=False):
        self.cfg = load_config()
        self.ui_queue = queue.Queue()
        self.root = tk.Tk()
        self.fam = apply_style(self.root)
        self.root.title(f"{APP_NAME} — ตรวจพิมพ์ผิดภาษา")
        self._set_window_icon()
        self._build()
        self.popup = Popup(self.root, self._popup_clicked, self.fam)
        self.engine = Engine(self.cfg, self.ui_queue)
        self.engine.start()
        try:
            self.tray = Tray(self)
        except Exception as e:  # ไม่มี pystray ก็ยังใช้งานได้ แค่ปิดหน้าต่าง = ออก
            print("tray unavailable:", e)
            self.tray = None
        # ให้ตัวที่เปิดซ้ำ / ตัวติดตั้ง สั่งเราได้
        self.show_event = k32.CreateEventW(None, False, False, installer.SHOW_EVENT)
        self.quit_event = k32.CreateEventW(None, False, False, installer.QUIT_EVENT)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window if self.tray else self.quit)
        if background and self.tray:
            self.root.withdraw()
        self.root.after(30, self._poll)

    def _set_window_icon(self):
        try:
            from PIL import ImageTk

            from icon import make_icon
            self._icon_img = ImageTk.PhotoImage(make_icon(64))
            self.root.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _build(self):
        pad = {"padx": 12, "pady": 4}
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=12, pady=(10, 4))
        self.status = ttk.Label(top, style="Status.TLabel")
        self.status.pack(side="left")
        self.toggle_btn = ttk.Button(top, command=self._toggle)
        self.toggle_btn.pack(side="right")

        self.var_auto = tk.BooleanVar(value=self.cfg["auto_fix"])
        self.var_switch = tk.BooleanVar(value=self.cfg["switch_layout"])
        self.var_live = tk.BooleanVar(value=self.cfg["live_check"])
        self.var_startup = tk.BooleanVar(value=installer.get_startup())
        opts = ttk.LabelFrame(self.root, text="ตั้งค่า", padding=(8, 4))
        opts.pack(fill="x", **pad)
        for text, var, cmd in (
                ("แก้ให้อัตโนมัติเมื่อเคาะ Space", self.var_auto, self._save_opts),
                ("เปลี่ยนภาษาแป้นพิมพ์ให้ด้วยหลังแก้", self.var_switch, self._save_opts),
                ("เตือนระหว่างพิมพ์ (ไม่ต้องรอเว้นวรรค)", self.var_live, self._save_opts),
                ("เปิดอัตโนมัติเมื่อเปิดเครื่อง", self.var_startup, self._toggle_startup)):
            ttk.Checkbutton(opts, text=text, variable=var, command=cmd).pack(anchor="w", pady=1)
        ttk.Label(opts, style="Muted.TLabel",
                  text=f"แก้คำ: กด {hotkey_label(self.cfg['hotkey'])} หรือ Pause หรือคลิกที่ป๊อปอัป").pack(
            anchor="w", pady=(4, 2))

        hist = ttk.LabelFrame(self.root, text="ประวัติการแก้", padding=4)
        hist.pack(fill="both", expand=True, **pad)
        self.history = tk.Listbox(hist, font=(self.fam, 11), activestyle="none", borderwidth=0,
                                  highlightthickness=0, height=7, width=46)
        self.history.pack(fill="both", expand=True, padx=4, pady=4)

        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Label(bottom, text=f"v{VERSION}  ·  ปิดหน้าต่างแล้วยังทำงานต่อที่ไอคอนมุมขวาล่าง",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(bottom, text="ออกจากโปรแกรม", command=self.quit).pack(side="right")
        self._refresh_status()

    def _refresh_status(self):
        on = self.cfg["enabled"]
        self.status.config(text="● กำลังตรวจ" if on else "○ หยุดชั่วคราว", foreground="#1a8f3c" if on else "#999")
        self.toggle_btn.config(text="หยุด" if on else "เริ่ม")
        if getattr(self, "tray", None):
            self.tray.set_enabled(on)

    def _toggle(self):
        self.cfg["enabled"] = not self.cfg["enabled"]
        save_config(self.cfg)
        self._refresh_status()
        if not self.cfg["enabled"]:
            self.engine.events.put(("clear",))

    def _save_opts(self):
        self.cfg["auto_fix"] = self.var_auto.get()
        self.cfg["switch_layout"] = self.var_switch.get()
        self.cfg["live_check"] = self.var_live.get()
        save_config(self.cfg)

    def _toggle_startup(self):
        try:
            installer.set_startup(self.var_startup.get())
        except OSError:
            self.var_startup.set(installer.get_startup())

    def _popup_clicked(self):
        self.engine.events.put(("fix",))

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

    def hide_window(self):
        self.root.withdraw()
        if not self.cfg.get("tray_hint_shown"):
            self.tray.notify("PimPid ยังทำงานอยู่เบื้องหลัง — คลิกไอคอนนี้เพื่อเปิดหน้าต่างอีกครั้ง")
            self.cfg["tray_hint_shown"] = True
            save_config(self.cfg)

    def _poll(self):
        if k32.WaitForSingleObject(self.show_event, 0) == 0:
            self.show_window()
        if k32.WaitForSingleObject(self.quit_event, 0) == 0:
            self.quit()
            return
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                if msg[0] == "suggest":
                    s = msg[1]
                    if s is None:
                        self.popup.hide()
                    else:
                        _, text, typed, from_lang = s
                        to = "ไทย" if from_lang == "en" else "English"
                        hint = f"เป็น{to}?  กด {hotkey_label(self.cfg['hotkey'])} / Pause / คลิก เพื่อแก้"
                        if self.cfg["auto_fix"]:
                            hint = f"เป็น{to}? จะแก้ให้อัตโนมัติเมื่อเว้นวรรค"
                        self.popup.show(typed, text, hint, self.cfg["popup_seconds"])
                elif msg[0] == "fixed":
                    _, typed, text = msg
                    self.history.insert(0, f"{time.strftime('%H:%M')}   {typed.strip()}  →  {text.strip()}")
                    self.history.delete(200, "end")
                elif msg[0] == "show":
                    self.show_window()
                elif msg[0] == "toggle":
                    self._toggle()
                elif msg[0] == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(30, self._poll)

    def quit(self):
        self.engine.stop()
        if self.tray:
            self.tray.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    args = sys.argv[1:]
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass

    if "--uninstall" in args:
        installer.uninstall_flow(silent="--silent" in args)
        return
    if "--install" in args:  # ติดตั้งแบบไม่มีหน้าต่าง (สำหรับแจกจ่ายหลายเครื่อง)
        installer.install(startup="--no-startup" not in args, desktop="--desktop" in args)
        if "--no-launch" not in args:
            installer.launch_installed()
        return
    if installer.is_frozen() and not installer.is_installed_copy() and "--portable" not in args:
        installer.install_dialog()
        return

    # ป้องกันการเปิดซ้อนหลายตัว: ถ้าเปิดอยู่แล้ว ให้ตัวเดิมโชว์หน้าต่างแทน
    mutex = k32.CreateMutexW(None, False, installer.MUTEX_NAME)
    if k32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        if "--background" not in args:
            installer.signal_event(installer.SHOW_EVENT)
        return
    App(background="--background" in args).run()
    k32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
