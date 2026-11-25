"""ตัวตรวจว่าข้อความที่พิมพ์ "ผิดภาษา" หรือไม่

แนวคิด: ทุกปุ่มที่กดสามารถแปลได้ทั้งเป็นอักษรอังกฤษและอักษรไทย
เราให้คะแนนว่าแต่ละเวอร์ชันดูเป็นภาษาจริงแค่ไหน แล้วเทียบกัน
  - ภาษาอังกฤษ: อยู่ในพจนานุกรม, bigram ตัวอักษร, มีสระ, ไม่มีสัญลักษณ์/ตัวเลขปนกลางคำ
  - ภาษาไทย: กฎการเรียงอักษร (สระ/วรรณยุกต์ต้องตามพยัญชนะ ฯลฯ), พจนานุกรม, bigram
"""
import math
import re
from collections import Counter
from dataclasses import dataclass

from wordlists import EN_WORDS, TH_WORDS

# ---------------------------------------------------------------- Thai chars
TH_CONSONANTS = set(chr(c) for c in range(0x0E01, 0x0E2F))
TH_LEADING = set("เแโใไ")
TH_FOLLOW = set("ะาำ")
TH_ABOVE_BELOW = set("ัิีึืุู")
TH_TONES = set("่้๊๋")
TH_OTHER_MARKS = set("็์ํฺ")
TH_DIGITS = set("๐๑๒๓๔๕๖๗๘๙")
TH_RARE = set("ฃฅฆฌฎฏฑฒฬฦฤํฺๅ฿")
THAI_LETTERS = TH_CONSONANTS | TH_LEADING | TH_FOLLOW | TH_ABOVE_BELOW | TH_TONES | TH_OTHER_MARKS | set("ๆฯ")

EN_VOWELS = set("aeiouy")
_NUMBER_RE = re.compile(r"^[\d.,:/\-+%$()]+$")
_TRAIL_PUNCT = ".,!?:\"')"
_LEAD_PUNCT = "\"'("


def thai_violations(w, partial=False):
    """นับจำนวนครั้งที่ลำดับอักษรไทยผิดหลักการเขียน"""
    bad = 0
    prev = ""
    for i, ch in enumerate(w):
        if ch in TH_ABOVE_BELOW or ch == "็":
            if prev not in TH_CONSONANTS:
                bad += 1
        elif ch in TH_TONES:
            if not (prev in TH_CONSONANTS or prev in TH_ABOVE_BELOW):
                bad += 1
        elif ch == "์":
            if not (prev in TH_CONSONANTS or prev in "ิุ"):
                bad += 1
        elif ch in TH_FOLLOW:
            if i == 0 or not (prev in TH_CONSONANTS or prev in TH_TONES or prev in "ั" or (ch == "ะ" and prev == "็")):
                bad += 1
            if prev in TH_FOLLOW and not (prev == "า" and ch == "ะ"):
                bad += 1
        elif ch in TH_LEADING:
            nxt = w[i + 1] if i + 1 < len(w) else None
            if nxt is None:
                if not partial:
                    bad += 1
            elif nxt not in TH_CONSONANTS and not (ch == "เ" and nxt == "เ"):
                bad += 1
        elif ch in "ๆฯ":
            if i == 0:
                bad += 1
        elif ch == "ํ" or ch == "ฺ":
            bad += 1  # แทบไม่มีใครพิมพ์ใช้
        prev = ch
    return bad


# ---------------------------------------------------------------- bigram LM
class CharBigram:
    def __init__(self, words, alphabet_size):
        self.big = Counter()
        self.uni = Counter()
        for w in words:
            s = "^" + w + "$"
            for a, b in zip(s, s[1:]):
                self.big[a, b] += 1
                self.uni[a] += 1
        self.V = alphabet_size + 1
        self.k = 0.3
        self.uniform = -math.log(self.V)

    def gain(self, w):
        """ค่าเฉลี่ย log-prob ต่อ bigram เทียบกับการสุ่ม (ยิ่งมากยิ่งดูเป็นภาษาจริง)"""
        s = "^" + w + "$"
        total = 0.0
        n = 0
        for a, b in zip(s, s[1:]):
            p = (self.big[a, b] + self.k) / (self.uni[a] + self.k * self.V)
            total += math.log(p)
            n += 1
        return total / n - self.uniform


EN_LM = CharBigram([w for w in EN_WORDS if w.isalpha()], 26)
TH_LM = CharBigram(TH_WORDS, len(THAI_LETTERS))


def _strip_punct(w):
    return w.lstrip(_LEAD_PUNCT).rstrip(_TRAIL_PUNCT)


def en_score(w, partial=False):
    core = _strip_punct(w)
    low = core.lower()
    if not core:
        return -1.0
    if low in EN_WORDS:
        return 6.0
    if partial and any(x.startswith(low) for x in EN_WORDS if len(x) > len(low)):
        dict_bonus = 2.0
    else:
        dict_bonus = 0.0
    score = dict_bonus
    letters = "".join(c for c in low if c.isalpha())
    # สัญลักษณ์ที่เจอบ่อยเวลาพิมพ์ไทยบนแป้นอังกฤษ ( ; ' [ ] = \ คือ ว ง บ ล ช ฃ )
    for i, c in enumerate(core):
        if c.isalpha():
            continue
        if c.isdigit():
            near_letter = (i > 0 and core[i - 1].isalpha()) or (i + 1 < len(core) and core[i + 1].isalpha())
            score -= 3.0 if near_letter else 0.5
        elif c in ";[]=\\{}|^&*":
            score -= 3.0
        elif c == "'":
            # don't / it's ปกติ แต่ ' ท้ายคำหรือหลังตัวเลขมักเป็น "ง"
            ok = 0 < i < len(core) - 1 and core[i - 1].isalpha() and core[i + 1].isalpha()
            score -= 0.5 if ok else 3.0
        elif c == "-":
            score -= 0.5
        else:  # , . : / @ _ ใช้ใน URL/ไฟล์/อีเมลได้
            score -= 1.5
    # ตัวพิมพ์ใหญ่กลางคำ (ที่ไม่ใช่ ALL CAPS) มักมาจาก Shift ของภาษาไทย
    if not core.isupper():
        score -= 1.5 * sum(1 for c in core[1:] if c.isupper())
    if len(letters) >= 2 and not any(c in EN_VOWELS for c in letters):
        score -= 2.0
    if letters:
        score += 2.0 * EN_LM.gain(letters)
    return score


def _dict_coverage(w):
    """สัดส่วนของคำที่ตัดได้ด้วยพจนานุกรม (longest match แบบง่าย)"""
    i = 0
    covered = 0
    maxlen = 12
    while i < len(w):
        for L in range(min(maxlen, len(w) - i), 1, -1):
            if w[i:i + L] in TH_WORDS:
                covered += L
                i += L
                break
        else:
            i += 1
    return covered / len(w) if w else 0.0


def th_score(w, partial=False):
    core = w.strip(" ")
    if not core:
        return -1.0
    if core in TH_WORDS:
        return 6.0
    score = 0.0
    score -= 3.0 * thai_violations(core, partial)
    score -= 1.0 * sum(1 for c in core if c in TH_RARE)
    inner = core.rstrip(_TRAIL_PUNCT)
    score -= 3.0 * sum(1 for c in inner if c not in THAI_LETTERS)
    score -= 1.5 * sum(1 for c in core if c in TH_DIGITS)
    # พยัญชนะติดกันยาว ๆ โดยไม่มีสระเลย แทบไม่มีในภาษาไทย
    for run in re.findall(r"[ก-ฮ]{4,}", core):
        score -= 1.5 * (len(run) - 3)
    score += 4.0 * _dict_coverage(core)
    letters = "".join(c for c in core if c in THAI_LETTERS)
    if letters:
        score += 1.5 * TH_LM.gain(letters)
    return score


# ---------------------------------------------------------------- decision
@dataclass
class Verdict:
    wrong: bool
    typed: str
    suggestion: str
    typed_score: float
    alt_score: float


MARGIN = 3.0


def judge_word(en_w, th_w, current, partial=False, chained=False):
    """current = 'en' หรือ 'th' (ภาษาของแป้นพิมพ์ตอนที่พิมพ์)

    chained=True คือคำถัดไปถูกตัดสินว่าผิดภาษาแล้ว จึงใช้เกณฑ์ที่ผ่อนลง
    """
    if len(en_w) < 2 and not chained:
        return Verdict(False, en_w if current == "en" else th_w, "", 0, 0)
    if _NUMBER_RE.match(en_w):
        return Verdict(False, en_w if current == "en" else th_w, "", 0, 0)
    e = en_score(en_w, partial)
    t = th_score(th_w, partial)
    if current == "en":
        typed, alt, ts, as_ = en_w, th_w, e, t
    else:
        typed, alt, ts, as_ = th_w, en_w, t, e
    if chained:
        margin = 0.5
    else:
        margin = MARGIN + (1.5 if partial else 0) + (1.0 if len(en_w) == 2 else 0)
        if as_ >= 6.0:  # อีกภาษาตรงกับคำในพจนานุกรมพอดี
            margin -= 0.5
    wrong = (as_ - ts) >= margin and as_ > 0
    return Verdict(wrong, typed, alt, ts, as_)


def judge_text(en_text, th_text, current, partial=False):
    """ตรวจทั้งประโยค คืน (จำนวนตัวอักษรท้ายข้อความที่ผิด, ข้อความที่ถูก) หรือ None

    ไล่จากคำท้ายสุดย้อนกลับไปเรื่อย ๆ ตราบใดที่คำยังผิดภาษา
    """
    assert len(en_text) == len(th_text)
    # แยกคำโดยเก็บตำแหน่ง
    spans = [(m.start(), m.end()) for m in re.finditer(r"[^ ]+", en_text)]
    if not spans:
        return None
    start_idx = None
    n_wrong = 0
    for k in range(len(spans) - 1, -1, -1):
        s, e = spans[k]
        is_last = k == len(spans) - 1
        is_partial = partial and is_last and e == len(en_text)
        v = judge_word(en_text[s:e], th_text[s:e], current, is_partial, chained=n_wrong > 0)
        if v.wrong:
            start_idx = s
            n_wrong += 1
        else:
            break
    if start_idx is None:
        return None
    alt = th_text if current == "en" else en_text
    return len(en_text) - start_idx, alt[start_idx:], n_wrong
