"""Windows API ผ่าน ctypes: low-level keyboard hook, SendInput, สลับภาษาแป้นพิมพ์"""
import ctypes
import threading
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0100, 0x0101, 0x0104, 0x0105
WM_QUIT = 0x0012
WM_INPUTLANGCHANGEREQUEST = 0x0050
LLKHF_INJECTED = 0x10

VK_BACK, VK_TAB, VK_RETURN, VK_SHIFT, VK_CONTROL, VK_MENU = 0x08, 0x09, 0x0D, 0x10, 0x11, 0x12
VK_CAPITAL, VK_ESCAPE, VK_SPACE = 0x14, 0x1B, 0x20
VK_LWIN, VK_RWIN = 0x5B, 0x5C
MODIFIER_VKS = {0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, VK_LWIN, VK_RWIN}

LANG_EN = 0x0409
LANG_TH = 0x041E

ULONG_PTR = wintypes.WPARAM
LRESULT = wintypes.LPARAM


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
user32.GetKeyboardLayout.restype = wintypes.HKL
user32.GetKeyboardLayoutList.argtypes = [ctypes.c_int, ctypes.POINTER(wintypes.HKL)]
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetCurrentThreadId.restype = wintypes.DWORD


def key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def caps_on():
    return bool(user32.GetKeyState(VK_CAPITAL) & 1)


def foreground_window():
    return user32.GetForegroundWindow()


def current_lang():
    """ภาษาแป้นพิมพ์ของหน้าต่างที่กำลังใช้งาน: 'en', 'th' หรือ None"""
    hwnd = user32.GetForegroundWindow()
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    hkl = user32.GetKeyboardLayout(tid) or 0
    lang = hkl & 0xFFFF
    if lang == LANG_TH:
        return "th"
    if (lang & 0xFF) == 0x09:  # English ทุกประเทศ
        return "en"
    return None


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD), ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND), ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND), ("rcCaret", wintypes.RECT)]


user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]


def _gui_info():
    hwnd = user32.GetForegroundWindow()
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
    if not user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
        return None
    return info


def _caret_win32(info):
    """แอป Win32 แบบดั้งเดิม (Notepad, กล่องข้อความทั่วไป)"""
    if not info or not info.hwndCaret:
        return None
    r = info.rcCaret
    tl = wintypes.POINT(r.left, r.top)
    br = wintypes.POINT(r.left, r.bottom)
    user32.ClientToScreen(info.hwndCaret, ctypes.byref(tl))
    user32.ClientToScreen(info.hwndCaret, ctypes.byref(br))
    if br.x == 0 and br.y == 0:
        return None
    return tl.x, tl.y, br.y


# ---- MSAA (IAccessible ผ่าน OBJID_CARET): Chrome, Edge, Firefox, Electron, Office ฯลฯ
class _GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8)]


class _VARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort),
                ("r3", ctypes.c_ushort), ("val", ctypes.c_longlong), ("pad", ctypes.c_void_p)]


_IID_IAccessible = _GUID(0x618736E0, 0x3C3D, 0x11CF, (ctypes.c_ubyte * 8)(0x81, 0x0C, 0x00, 0xAA, 0x00, 0x38, 0x9B, 0x71))
OBJID_CARET = -8
VT_I4 = 3
try:
    _oleacc = ctypes.WinDLL("oleacc")
    _oleacc.AccessibleObjectFromWindow.argtypes = [wintypes.HWND, wintypes.LONG, ctypes.POINTER(_GUID),
                                                   ctypes.POINTER(ctypes.c_void_p)]
    _ole32 = ctypes.WinDLL("ole32")
except OSError:
    _oleacc = None

_RELEASE = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
_ACC_LOCATION = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_long),
                                   ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long),
                                   ctypes.POINTER(ctypes.c_long), _VARIANT)
_com_ready = threading.local()


def _caret_msaa(info):
    if _oleacc is None:
        return None
    if not getattr(_com_ready, "ok", False):
        _ole32.CoInitialize(None)
        _com_ready.ok = True
    hwnd = (info.hwndFocus if info and info.hwndFocus else None) or user32.GetForegroundWindow()
    ptr = ctypes.c_void_p()
    if _oleacc.AccessibleObjectFromWindow(hwnd, OBJID_CARET, ctypes.byref(_IID_IAccessible), ctypes.byref(ptr)) != 0 \
            or not ptr.value:
        return None
    try:
        vtbl = ctypes.cast(ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
        acc_location = _ACC_LOCATION(vtbl[22])  # IAccessible::accLocation
        x, y, cx, cy = ctypes.c_long(), ctypes.c_long(), ctypes.c_long(), ctypes.c_long()
        child = _VARIANT(vt=VT_I4, val=0)  # CHILDID_SELF
        hr = acc_location(ptr, ctypes.byref(x), ctypes.byref(y), ctypes.byref(cx), ctypes.byref(cy), child)
        if hr != 0 or (x.value == 0 and y.value == 0) or cy.value <= 0:
            return None
        return x.value, y.value, y.value + cy.value
    finally:
        _RELEASE(vtbl[2])(ptr)


def caret_rect():
    """ตำแหน่งเคอร์เซอร์พิมพ์บนจอ (x, y_บน, y_ล่าง) หรือ None ถ้าแอปไม่ยอมบอก"""
    info = _gui_info()
    for fn in (_caret_win32, _caret_msaa):
        try:
            r = fn(info)
        except OSError:
            r = None
        if r:
            return r
    return None


def cursor_pos():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)]


user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
user32.MonitorFromPoint.restype = wintypes.HMONITOR
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MONITORINFO)]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]


def work_area(x, y):
    """พื้นที่ใช้งาน (ไม่รวม taskbar) ของจอที่จุด (x, y) อยู่: (left, top, right, bottom)"""
    mon = user32.MonitorFromPoint(wintypes.POINT(x, y), 2)  # MONITOR_DEFAULTTONEAREST
    mi = _MONITORINFO(cbSize=ctypes.sizeof(_MONITORINFO))
    user32.GetMonitorInfoW(mon, ctypes.byref(mi))
    r = mi.rcWork
    return r.left, r.top, r.right, r.bottom


def foreground_rect():
    r = wintypes.RECT()
    user32.GetWindowRect(user32.GetForegroundWindow(), ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def send_mask_key():
    """ส่งปุ่มหลอก (vk 0xE8 ที่ไม่มีใครใช้) กันไม่ให้ Windows ตีความ Ctrl+Shift / Alt
    ที่เหลือค้างอยู่เป็นการสลับภาษาหรือเปิดเมนู หลังจากเรากลืน hotkey ไปแล้ว"""
    send_inputs([_key_input(vk=0xE8), _key_input(vk=0xE8, flags=KEYEVENTF_KEYUP)])


def _installed_layouts():
    n = user32.GetKeyboardLayoutList(0, None)
    arr = (wintypes.HKL * n)()
    user32.GetKeyboardLayoutList(n, arr)
    return [h or 0 for h in arr]


def switch_lang(target):
    """ขอให้หน้าต่างปัจจุบันเปลี่ยนภาษาเป็น target ('en'/'th')"""
    for hkl in _installed_layouts():
        lang = hkl & 0xFFFF
        if (target == "th" and lang == LANG_TH) or (target == "en" and (lang & 0xFF) == 0x09):
            user32.PostMessageW(user32.GetForegroundWindow(), WM_INPUTLANGCHANGEREQUEST, 0, hkl)
            return True
    return False


def _key_input(vk=0, scan=0, flags=0):
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.u.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
    return inp


def send_inputs(inputs):
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def wait_modifiers_released(timeout=1.5):
    end = time.time() + timeout
    while time.time() < end:
        if not any(key_down(vk) for vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN)):
            return True
        time.sleep(0.02)
    return False


def replace_text(n_backspace, text):
    """ลบ n_backspace ตัวอักษรแล้วพิมพ์ text แทน (ใช้ Unicode ไม่ขึ้นกับภาษาแป้นพิมพ์)"""
    inputs = []
    for _ in range(n_backspace):
        inputs.append(_key_input(vk=VK_BACK))
        inputs.append(_key_input(vk=VK_BACK, flags=KEYEVENTF_KEYUP))
    for ch in text:
        code = ord(ch)
        inputs.append(_key_input(scan=code, flags=KEYEVENTF_UNICODE))
        inputs.append(_key_input(scan=code, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
    send_inputs(inputs)


class KeyboardHook:
    """ติดตั้ง WH_KEYBOARD_LL ใน thread ของตัวเอง

    on_key(vk, is_down, flags) -> True ถ้าต้องการ "กลืน" ปุ่มนี้ (ไม่ส่งต่อให้แอปอื่น)
    callback ต้องทำงานเร็วมาก ห้ามทำงานหนักในนี้
    """

    def __init__(self, on_key):
        self.on_key = on_key
        self._proc = HOOKPROC(self._callback)  # เก็บ reference ไว้ไม่ให้ถูก GC
        self._hook = None
        self._tid = None
        self._thread = None

    def _callback(self, n_code, w_param, l_param):
        if n_code == 0:
            kb = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            is_down = w_param in (WM_KEYDOWN, WM_SYSKEYDOWN)
            try:
                if self.on_key(kb.vkCode, is_down, kb.flags):
                    return 1
            except Exception as e:  # อย่าให้ exception ทำให้คีย์บอร์ดค้าง
                print("hook error:", e)
        return user32.CallNextHookEx(self._hook, n_code, w_param, l_param)

    def _run(self):
        self._tid = kernel32.GetCurrentThreadId()
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
        if not self._hook:
            raise ctypes.WinError(ctypes.get_last_error())
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            pass
        user32.UnhookWindowsHookEx(self._hook)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="kbd-hook")
        self._thread.start()

    def stop(self):
        if self._tid:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
