"""วาดไอคอนแอป (ใช้ทั้งใน tray และไฟล์ .ico ตอน build)"""
import os

from PIL import Image, ImageDraw, ImageFont

ACTIVE = (255, 186, 59)
PAUSED = (150, 156, 170)


def _font(size):
    for name in ("LeelaUIb.ttf", "LeelawUI.ttf", "tahomabd.ttf", "tahoma.ttf"):
        path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_icon(size=64, active=True):
    s = 4  # วาดใหญ่แล้วย่อให้ขอบเนียน
    img = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    W = size * s
    d.rounded_rectangle((0, 0, W - 1, W - 1), radius=W // 5, fill=(31, 36, 48))
    accent = ACTIVE if active else PAUSED
    f = _font(int(W * 0.46))
    d.text((W * 0.30, W * 0.47), "ก", font=f, fill=accent, anchor="mm")
    d.text((W * 0.72, W * 0.53), "A", font=f, fill=(242, 244, 248), anchor="mm")
    d.rounded_rectangle((W * 0.14, W * 0.80, W * 0.86, W * 0.86), radius=W // 40, fill=accent)
    return img.resize((size, size), Image.LANCZOS)


def save_ico(path):
    sizes = [16, 24, 32, 48, 64, 128, 256]
    make_icon(256).save(path, format="ICO", sizes=[(n, n) for n in sizes])


if __name__ == "__main__":
    import sys
    save_ico(sys.argv[1] if len(sys.argv) > 1 else "pimpid.ico")
