#!/usr/bin/env python3
"""Draw the news-image entry for make.fun's news-image-20261124 bounty.

One image summing up the world's news of Tuesday 24 November 2026.
Drawn with Pillow only: every story is readable text in the image itself,
because the judge has no news feed and judges only from the image.
Run: python3 draw_image.py  -> writes entry.png (1024x1024, < 1 MiB).
"""
import textwrap
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
PAPER = (247, 243, 234)
INK = (22, 22, 22)
NAVY = (14, 30, 51)
GOLD = (201, 162, 39)
GREY = (110, 108, 100)
PANEL_BORDER = (216, 210, 196)

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
f_bold = lambda s: ImageFont.truetype(FONT_DIR + "DejaVuSans-Bold.ttf", s)
f_reg = lambda s: ImageFont.truetype(FONT_DIR + "DejaVuSans.ttf", s)

img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)

# ---------- masthead ----------
d.rectangle([0, 0, W, 190], fill=NAVY)
d.text((W // 2, 30), "T H E   W O R L D   I N   O N E   D A Y",
       font=f_bold(26), fill=GOLD, anchor="ma")
d.text((W // 2, 96), "24 NOVEMBER 2026", font=f_bold(54),
       fill=(255, 255, 255), anchor="ma")
d.line([W // 2 - 180, 160, W // 2 + 180, 160], fill=GOLD, width=2)
d.text((W // 2, 168), "TUESDAY  •  WORLD NEWS AT A GLANCE",
       font=f_reg(20), fill=(200, 205, 215), anchor="ma")

# ---------- story panels ----------
# (tag, tag colour, headline, caption, icon)
stories = [
    ("SPACE", (31, 78, 121), "NATO vows to defend space",
     "Allies warn Russia may put a nuclear weapon in orbit as soon as December.",
     "satellite"),
    ("LIBYA", (179, 32, 44), "Ukraine sinks Russian warship",
     "Kyiv confirms a sea-drone strike on two Russian vessels off Libya; the UN seeks a probe.",
     "ship"),
    ("HORMUZ", (176, 92, 12), "Three tankers hit by sea mines",
     "Ships catch fire in the Strait of Hormuz as the UK logs record Iranian attacks.",
     "drop"),
    ("MYANMAR", (58, 110, 72), "ICJ: Myanmar guilty of genocide",
     "Court rules on the Rohingya; 14 nations back the verdict and the UK sanctions generals.",
     "scales"),
    ("TECH", (90, 60, 140), "Nvidia brings back Huang",
     "Jensen Huang is reinstated as chief executive after Trump intervenes; shares surge.",
     "chip"),
    ("KOREA", (14, 90, 110), "North Korean jet enters South's skies",
     "Suspected aircraft near Ulleung island; residents are told to take shelter.",
     "plane"),
]


def wrap(text, font, width):
    lines = []
    for para in text.split("\n"):
        lines += textwrap.wrap(para, width=width) or [""]
    # re-wrap by pixel width for accuracy
    out = []
    for line in lines:
        while d.textlength(line, font=font) > width and " " in line:
            cut = line.rfind(" ", 0, int(len(line) * width / max(d.textlength(line, font=font), 1)) + 1)
            if cut <= 0:
                break
            out.append(line[:cut])
            line = line[cut + 1:]
        out.append(line)
    return out


def draw_icon(cx, cy, kind, color):
    r = 34
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)
    if kind == "satellite":
        d.ellipse([cx - 26, cy - 12, cx + 26, cy + 12], outline=color, width=2)
        d.rectangle([cx - 12, cy - 6, cx + 12, cy + 6], fill=color)
        d.rectangle([cx + 12, cy - 3, cx + 24, cy + 3], fill=color)
        d.ellipse([cx - 30, cy - 22, cx - 20, cy - 12], fill=color)
    elif kind == "ship":
        d.polygon([(cx - 24, cy + 8), (cx + 24, cy + 8), (cx + 14, cy + 22), (cx - 14, cy + 22)], fill=color)
        d.line([cx, cy + 8, cx, cy - 20], fill=color, width=3)
        d.polygon([(cx, cy - 20), (cx + 14, cy - 14), (cx, cy - 8)], fill=color)
    elif kind == "drop":
        d.polygon([(cx, cy - 24), (cx + 16, cy + 2), (cx + 16, cy + 12),
                   (cx - 16, cy + 12), (cx - 16, cy + 2)], fill=color)
        d.ellipse([cx - 16, cy + 2, cx + 16, cy + 22], fill=color)
    elif kind == "scales":
        d.line([cx, cy - 22, cx, cy + 20], fill=color, width=3)
        d.line([cx - 22, cy - 16, cx + 22, cy - 16], fill=color, width=3)
        d.polygon([(cx - 26, cy + 2), (cx - 14, cy + 2), (cx - 20, cy + 14)], fill=color)
        d.polygon([(cx + 14, cy + 2), (cx + 26, cy + 2), (cx + 20, cy + 14)], fill=color)
    elif kind == "chip":
        d.rectangle([cx - 16, cy - 16, cx + 16, cy + 16], outline=color, width=3)
        d.rectangle([cx - 7, cy - 7, cx + 7, cy + 7], fill=color)
        for dx in (-10, 0, 10):
            d.line([cx + dx, cy - 24, cx + dx, cy - 16], fill=color, width=2)
            d.line([cx + dx, cy + 16, cx + dx, cy + 24], fill=color, width=2)
    elif kind == "plane":
        d.polygon([(cx - 22, cy + 4), (cx + 24, cy - 14), (cx + 10, cy + 6),
                   (cx + 16, cy + 20), (cx + 4, cy + 10), (cx - 12, cy + 18)], fill=color)


MX, MY = 28, 202
PW, PH, GX, GY = 466, 212, 20, 14
for i, (tag, color, head, cap, icon) in enumerate(stories):
    x = MX + (i % 2) * (PW + GX)
    y = MY + (i // 2) * (PH + GY)
    d.rectangle([x, y, x + PW, y + PH], fill=(255, 255, 255), outline=PANEL_BORDER, width=2)
    d.rectangle([x, y, x + PW, y + 6], fill=color)
    d.text((x + 18, y + 22), tag, font=f_bold(18), fill=color)
    draw_icon(x + PW - 52, y + 46, icon, color)
    hl = wrap(head, f_bold(29), PW - 36 - 96)
    ty = y + 52
    for line in hl[:2]:
        d.text((x + 18, ty), line, font=f_bold(29), fill=INK)
        ty += 36
    cl = wrap(cap, f_reg(20), PW - 36)
    for line in cl[:3]:
        d.text((x + 18, ty + 6), line, font=f_reg(20), fill=(60, 58, 52))
        ty += 27

# ---------- also-today strip ----------
sy = MY + 3 * PH + 2 * GY + 14
d.rectangle([MX, sy, W - MX, sy + 96], fill=(255, 255, 255), outline=PANEL_BORDER, width=2)
d.text((MX + 16, sy + 10), "ALSO TODAY", font=f_bold(18), fill=(179, 32, 44))
also = ("COP31 ends with no deal on fossil fuels  •  US loses measles-free status  •  "
       "Sanofi buys Insmed for $41bn  •  Nepal quake, magnitude 5.6  •  "
       "2031 Women's World Cup hosts named  •  Leaked data: 700,000 Russian war dead")
for j, line in enumerate(wrap(also, f_reg(18), W - 2 * MX - 32)):
    d.text((MX + 16, sy + 34 + j * 23), line, font=f_reg(18), fill=(60, 58, 52))

# ---------- footer ----------
fy = H - 24
d.text((MX, fy), "Compiled from Reuters, SCMP, Al Jazeera and official statements",
       font=f_reg(16), fill=GREY)
d.text((W - MX, fy), "24 NOV 2026", font=f_bold(16), fill=GREY, anchor="ra")

img.save("entry.png", optimize=True)
print("saved entry.png", img.size)
