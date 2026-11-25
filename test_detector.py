"""ทดสอบตัวตรวจ: python test_detector.py"""
import sys

from detector import judge_text
from layout import en_to_th, th_to_en

sys.stdout.reconfigure(encoding="utf-8")

# ภาษาไทยที่ลืมเปลี่ยน (แป้นยังเป็น EN) -> ต้องจับได้
THAI_IN_EN = [
    "สวัสดี", "ทดสอบ", "กินข้าว", "ไปไหน", "ขอบคุณครับ", "คน", "ถึงแล้ว", "พิมพ์ผิด",
    "ภาษาไทย", "อร่อยมาก", "เป็นอะไร", "ไม่รู้", "โอเค", "รักนะ", "วันนี้ฝนตก", "ได้เลย",
    "เดี๋ยวโทรกลับ", "ประชุมกี่โมง", "ทำงานอยู่", "นอน", "กิน", "ไป", "ใช่", "มา",
]
# ภาษาอังกฤษที่ลืมเปลี่ยน (แป้นยังเป็น TH) -> ต้องจับได้
EN_IN_TH = [
    "hello", "the", "world", "test", "python", "thank you", "meeting", "computer",
    "please", "good morning", "code", "what", "keyboard", "github", "username", "is",
    "google", "download", "awesome", "Hello", "I am fine",
]
# พิมพ์ถูกภาษาอยู่แล้ว -> ห้ามเตือน
EN_OK = [
    "hello", "world", "python", "is", "the", "I", "ok", "keyboard", "detection", "awesome",
    "github", "stackoverflow", "username", "kubernetes", "README.md", "2024", "10:30",
    "e-mail", "don't", "Bangkok", "Thailand", "lol", "xyz", "Mr.", "a", "pimpid", "npm",
    "localhost:8080", "C++", "html", "ctrl", "def", "src/app.py",
]
TH_OK = [
    "สวัสดี", "ทดสอบ", "ประเทศไทย", "คอมพิวเตอร์", "กรุงเทพมหานคร", "นักศึกษา", "เชียงใหม่",
    "แมว", "ก๋วยเตี๋ยว", "ศักดิ์สิทธิ์", "น้ำ", "เกาะ", "ไก่", "ค่ะ", "ครับ", "เด็ก", "โรงเรียน",
    "แล้ว", "ก็", "ๆ", "หนังสือ", "มหาวิทยาลัย", "สนุกมาก", "จ้า", "ชื่อ", "เพลง", "ฤดู",
]


def check(label, typed_lang, items, expect):
    fails = 0
    for s in items:
        if typed_lang == "en":
            en, th = s, en_to_th(s)
        else:
            th, en = s, th_to_en(s)
            if expect is False:
                pass
        if typed_lang == "th" and expect is True:
            # s คือภาษาอังกฤษ แต่พิมพ์บนแป้นไทย
            en, th = s, en_to_th(s)
        if typed_lang == "en" and expect is True:
            # s คือภาษาไทย แต่พิมพ์บนแป้นอังกฤษ
            th, en = s, th_to_en(s)
        r = judge_text(en, th, typed_lang)
        got = r is not None
        ok = got == expect
        if not ok:
            fails += 1
        mark = "OK  " if ok else "FAIL"
        typed = en if typed_lang == "en" else th
        print(f"  {mark} [{typed_lang}] {typed!r:24} -> {r[1] if r else '-'}")
    print(f"{label}: {len(items) - fails}/{len(items)}")
    return fails


if __name__ == "__main__":
    f = 0
    f += check("ไทยบนแป้น EN (ต้องเตือน)", "en", THAI_IN_EN, True)
    f += check("อังกฤษบนแป้น TH (ต้องเตือน)", "th", EN_IN_TH, True)
    f += check("อังกฤษถูกต้อง (ห้ามเตือน)", "en", EN_OK, False)
    f += check("ไทยถูกต้อง (ห้ามเตือน)", "th", TH_OK, False)
    print("FAILED:", f)
    sys.exit(1 if f else 0)
