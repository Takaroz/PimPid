"""Mapping ระหว่างแป้นพิมพ์ English (US QWERTY) กับ ไทย (เกษมณี)

ใช้ตำแหน่งปุ่มเดียวกัน: ตัวอักษรที่ได้จากปุ่มเดียวกันในสองภาษา
"""

# ปุ่มที่ไม่กด Shift
_EN_NORMAL = "`1234567890-=qwertyuiop[]\\asdfghjkl;'zxcvbnm,./"
_TH_NORMAL = "_ๅ/-ภถุึคตจขชๆไำพะัีรนยบลฃฟหกดเ้่าสวงผปแอิืทมใฝ"

# ปุ่มที่กด Shift
_EN_SHIFT = '~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:"ZXCVBNM<>?'
_TH_SHIFT = '%+๑๒๓๔ู฿๕๖๗๘๙๐"ฎฑธํ๊ณฯญฐ,ฅฤฆฏโฌ็๋ษศซ.()ฉฮฺ์?ฒฬฦ'

assert len(_EN_NORMAL) == len(_TH_NORMAL), (len(_EN_NORMAL), len(_TH_NORMAL))
assert len(_EN_SHIFT) == len(_TH_SHIFT), (len(_EN_SHIFT), len(_TH_SHIFT))

EN_TO_TH = {}
TH_TO_EN = {}
for _en, _th in list(zip(_EN_NORMAL, _TH_NORMAL)) + list(zip(_EN_SHIFT, _TH_SHIFT)):
    EN_TO_TH[_en] = _th
    # ตัวที่ซ้ำกันในทั้งสองฝั่ง (เช่น " , . ?) ให้ใช้ค่าแรกที่เจอ
    TH_TO_EN.setdefault(_th, _en)
TH_TO_EN[" "] = " "
EN_TO_TH[" "] = " "

# Virtual-key code ของ Windows -> (ตัวปกติ, ตัวที่กด Shift) ในแป้น US
VK_TO_US = {}
for _i, _c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    VK_TO_US[0x41 + _i] = (_c, _c.upper())
for _i, (_n, _s) in enumerate(zip("0123456789", ")!@#$%^&*(")):
    VK_TO_US[0x30 + _i] = (_n, _s)
VK_TO_US.update({
    0xBA: (";", ":"),   # VK_OEM_1
    0xBB: ("=", "+"),   # VK_OEM_PLUS
    0xBC: (",", "<"),   # VK_OEM_COMMA
    0xBD: ("-", "_"),   # VK_OEM_MINUS
    0xBE: (".", ">"),   # VK_OEM_PERIOD
    0xBF: ("/", "?"),   # VK_OEM_2
    0xC0: ("`", "~"),   # VK_OEM_3
    0xDB: ("[", "{"),   # VK_OEM_4
    0xDC: ("\\", "|"),  # VK_OEM_5
    0xDD: ("]", "}"),   # VK_OEM_6
    0xDE: ("'", '"'),   # VK_OEM_7
})


def key_chars(vk, shift, caps):
    """คืน (ตัวอักษรอังกฤษ, ตัวอักษรไทย) ที่ปุ่มนี้จะพิมพ์ออกมา หรือ None"""
    pair = VK_TO_US.get(vk)
    if pair is None:
        return None
    normal, shifted = pair
    th = EN_TO_TH[shifted if shift else normal]
    if normal.isalpha():
        en = shifted if (shift ^ caps) else normal
    else:
        en = shifted if shift else normal
    return en, th


def en_to_th(text):
    return "".join(EN_TO_TH.get(c, EN_TO_TH.get(c.lower(), c)) for c in text)


def th_to_en(text):
    return "".join(TH_TO_EN.get(c, c) for c in text)
