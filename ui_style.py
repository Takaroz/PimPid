"""ฟอนต์และสไตล์ของหน้าต่าง

Tahoma/Segoe UI ทำให้สระบน-วรรณยุกต์ลอยหรือซ้อนกันบนจอที่ขยาย DPI
จึงใช้ Leelawadee UI ซึ่งเป็นฟอนต์ไทยมาตรฐานของ Windows 10/11
"""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

THAI_FONTS = ("Leelawadee UI", "Leelawadee", "Tahoma")


def thai_family(root):
    available = set(tkfont.families(root))
    for f in THAI_FONTS:
        if f in available:
            return f
    return "TkDefaultFont"


def apply_style(root):
    fam = thai_family(root)
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont"):
        try:
            tkfont.nametofont(name).configure(family=fam, size=10)
        except tk.TclError:
            pass
    style = ttk.Style(root)
    style.configure("Title.TLabel", font=(fam, 14, "bold"))
    style.configure("Status.TLabel", font=(fam, 11, "bold"))
    style.configure("Muted.TLabel", foreground="#666666")
    style.configure("Accent.TButton", font=(fam, 10, "bold"))
    return fam
