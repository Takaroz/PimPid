"""ติดตั้ง / ถอนการติดตั้ง / เปิดพร้อม Windows (ต่อผู้ใช้ ไม่ต้องใช้สิทธิ์ Administrator)

PimPid.exe ไฟล์เดียวทำหน้าที่เป็นตัวติดตั้งด้วย:
  PimPid.exe                 -> ถ้ายังไม่ได้อยู่ในที่ติดตั้ง จะเปิดหน้าต่างติดตั้ง
  PimPid.exe --install       -> ติดตั้งเงียบ ๆ (เปิดพร้อม Windows + ทางลัด Start Menu)
  PimPid.exe --uninstall     -> ถอนการติดตั้ง (เพิ่ม --silent เพื่อไม่ถาม)
"""
import ctypes
import os
import shutil
import subprocess
import sys
import time
import winreg

from version import APP_NAME, PUBLISHER, VERSION

LOCALAPPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
APPDATA = os.environ.get("APPDATA", os.path.expanduser(r"~\AppData\Roaming"))
INSTALL_DIR = os.path.join(LOCALAPPDATA, "Programs", APP_NAME)
INSTALLED_EXE = os.path.join(INSTALL_DIR, f"{APP_NAME}.exe")
DATA_DIR = os.path.join(APPDATA, APP_NAME)
START_MENU_LNK = os.path.join(APPDATA, r"Microsoft\Windows\Start Menu\Programs", f"{APP_NAME}.lnk")
DESKTOP_LNK = os.path.join(os.path.expanduser("~"), "Desktop", f"{APP_NAME}.lnk")

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
UNINSTALL_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"

MUTEX_NAME = "PimPidTypingChecker"
SHOW_EVENT = "Local\\PimPidShowWindow"
QUIT_EVENT = "Local\\PimPidQuit"
CREATE_NO_WINDOW = 0x08000000

k32 = ctypes.windll.kernel32
k32.OpenEventW.restype = ctypes.c_void_p
k32.OpenMutexW.restype = ctypes.c_void_p
k32.SetEvent.argtypes = [ctypes.c_void_p]
k32.CloseHandle.argtypes = [ctypes.c_void_p]


def is_frozen():
    return getattr(sys, "frozen", False)


def is_installed_copy():
    return is_frozen() and os.path.normcase(os.path.abspath(sys.executable)) == os.path.normcase(INSTALLED_EXE)


def launch_command(background=True):
    """คำสั่งที่ใช้เปิดแอปตัวที่กำลังรันอยู่ (exe หรือ python script)"""
    flag = " --background" if background else ""
    if is_frozen():
        return f'"{sys.executable}"{flag}'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    return f'"{pyw}" "{script}"{flag}'


# ------------------------------------------------------------ startup
def get_startup():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_startup(enabled, command=None):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
        if enabled:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, command or launch_command(True))
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except OSError:
                pass


# ------------------------------------------------------------ running instance
def signal_event(name):
    h = k32.OpenEventW(0x0002, False, name)  # EVENT_MODIFY_STATE
    if h:
        k32.SetEvent(h)
        k32.CloseHandle(h)
        return True
    return False


def is_running():
    h = k32.OpenMutexW(0x00100000, False, MUTEX_NAME)  # SYNCHRONIZE
    if h:
        k32.CloseHandle(h)
        return True
    return False


def stop_running(timeout=6.0):
    if not is_running():
        return True
    signal_event(QUIT_EVENT)
    end = time.time() + timeout
    while time.time() < end:
        if not is_running():
            time.sleep(0.3)  # ให้ process ปิดไฟล์ exe เสร็จ
            return True
        time.sleep(0.1)
    # ยังไม่ปิด ใช้วิธีบังคับ
    subprocess.run(["taskkill", "/F", "/IM", f"{APP_NAME}.exe"], creationflags=CREATE_NO_WINDOW,
                   capture_output=True)
    time.sleep(0.5)
    return not is_running()


# ------------------------------------------------------------ install / uninstall
def _make_shortcut(lnk, target):
    os.makedirs(os.path.dirname(lnk), exist_ok=True)
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
          f"$s.TargetPath='{target}';$s.WorkingDirectory='{os.path.dirname(target)}';"
          f"$s.IconLocation='{target},0';$s.Description='{APP_NAME} - ตรวจพิมพ์ผิดภาษา';$s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                   creationflags=CREATE_NO_WINDOW, capture_output=True)


def install(startup=True, desktop=False):
    if not is_frozen():
        raise RuntimeError("ติดตั้งได้เฉพาะจากไฟล์ PimPid.exe ที่ build แล้ว")
    stop_running()
    os.makedirs(INSTALL_DIR, exist_ok=True)
    if not is_installed_copy():
        # ตัวเก่าอาจยังปิดไม่สนิท (ไฟล์ exe ยังถูกล็อกอยู่ครู่หนึ่ง) ลองซ้ำสักพัก
        for attempt in range(40):
            try:
                shutil.copy2(sys.executable, INSTALLED_EXE)
                break
            except PermissionError:
                if attempt == 39:
                    raise
                time.sleep(0.25)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
        size_kb = os.path.getsize(INSTALLED_EXE) // 1024
        for name, val in (("DisplayName", APP_NAME), ("DisplayVersion", VERSION), ("Publisher", PUBLISHER),
                          ("DisplayIcon", INSTALLED_EXE), ("InstallLocation", INSTALL_DIR),
                          ("UninstallString", f'"{INSTALLED_EXE}" --uninstall'),
                          ("QuietUninstallString", f'"{INSTALLED_EXE}" --uninstall --silent')):
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
        for name, val in (("NoModify", 1), ("NoRepair", 1), ("EstimatedSize", size_kb)):
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, val)

    _make_shortcut(START_MENU_LNK, INSTALLED_EXE)
    if desktop:
        _make_shortcut(DESKTOP_LNK, INSTALLED_EXE)
    set_startup(startup, f'"{INSTALLED_EXE}" --background')


def uninstall(remove_settings=True):
    stop_running()
    set_startup(False)
    for p in (START_MENU_LNK, DESKTOP_LNK):
        try:
            os.remove(p)
        except OSError:
            pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass
    if remove_settings:
        shutil.rmtree(DATA_DIR, ignore_errors=True)
    if is_installed_copy():
        # exe ลบตัวเองตอนกำลังรันไม่ได้ ให้ cmd รอเราปิดก่อนแล้วค่อยลบโฟลเดอร์
        subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{INSTALL_DIR}"',
                         creationflags=CREATE_NO_WINDOW, cwd=os.environ.get("TEMP", "C:\\"))
    else:
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)


def launch_installed():
    subprocess.Popen([INSTALLED_EXE], cwd=INSTALL_DIR)


# ------------------------------------------------------------ dialogs
def install_dialog():
    import tkinter as tk
    from tkinter import messagebox, ttk

    from ui_style import apply_style

    root = tk.Tk()
    root.title(f"ติดตั้ง {APP_NAME} {VERSION}")
    root.resizable(False, False)
    apply_style(root)
    try:
        from PIL import ImageTk

        from icon import make_icon
        root._icon = ImageTk.PhotoImage(make_icon(64))
        root.iconphoto(True, root._icon)
    except Exception:
        pass
    frm = ttk.Frame(root, padding=20)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text=f"{APP_NAME}", style="Title.TLabel").pack(anchor="w")
    ttk.Label(frm, text="ตรวจจับการพิมพ์ผิดภาษา เมื่อลืมเปลี่ยน ไทย ⇄ English").pack(anchor="w", pady=(2, 12))
    ttk.Label(frm, text=f"ติดตั้งไปที่:  {INSTALL_DIR}", style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
    v_start = tk.BooleanVar(value=True)
    v_desk = tk.BooleanVar(value=True)
    v_run = tk.BooleanVar(value=True)
    ttk.Checkbutton(frm, text="เปิดอัตโนมัติเมื่อเปิดเครื่อง", variable=v_start).pack(anchor="w")
    ttk.Checkbutton(frm, text="สร้างทางลัดบนเดสก์ท็อป", variable=v_desk).pack(anchor="w")
    ttk.Checkbutton(frm, text="เปิดโปรแกรมหลังติดตั้งเสร็จ", variable=v_run).pack(anchor="w")
    btns = ttk.Frame(frm)
    btns.pack(fill="x", pady=(16, 0))

    def do_install():
        root.config(cursor="watch")
        root.update()
        try:
            install(v_start.get(), v_desk.get())
        except Exception as e:
            root.config(cursor="")
            messagebox.showerror(APP_NAME, f"ติดตั้งไม่สำเร็จ:\n{e}")
            return
        if v_run.get():
            launch_installed()
            messagebox.showinfo(APP_NAME, "ติดตั้งเรียบร้อย\nPimPid ทำงานอยู่ที่ไอคอนมุมขวาล่างของจอ (tray)")
        else:
            messagebox.showinfo(APP_NAME, "ติดตั้งเรียบร้อย เปิดได้จาก Start Menu")
        root.destroy()

    ttk.Button(btns, text="ยกเลิก", command=root.destroy).pack(side="right")
    ttk.Button(btns, text="ติดตั้ง", command=do_install, style="Accent.TButton").pack(side="right", padx=(0, 8))
    root.mainloop()


def uninstall_flow(silent=False):
    if not silent:
        ok = ctypes.windll.user32.MessageBoxW(None, f"ต้องการถอนการติดตั้ง {APP_NAME} ใช่ไหม?\n"
                                                    "(การตั้งค่าและประวัติจะถูกลบด้วย)",
                                              f"ถอนการติดตั้ง {APP_NAME}", 0x04 | 0x20)  # YESNO | QUESTION
        if ok != 6:  # IDYES
            return
    uninstall()
    if not silent:
        ctypes.windll.user32.MessageBoxW(None, f"ถอนการติดตั้ง {APP_NAME} เรียบร้อยแล้ว", APP_NAME, 0x40)
