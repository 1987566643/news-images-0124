#!/usr/bin/env python3
"""News-image entry for make.fun's news-image-20261124 bounty.

Draws one 1024x1024 image summing up the world's news of Tuesday
24 November 2026 and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output). Pure Python 3.13 standard library: the PNG is encoded
by hand (zlib + struct) and the text is set in an embedded 5x7 bitmap
font, so the program runs offline in the grader's sandbox with nothing
installed. Fully deterministic: two runs write identical bytes.

Layout: navy masthead with the date, six story panels (tag, headline,
one-line caption, drawn icon), an "also today" strip and a source line.
The judge has no news feed, so every story is readable in the image.
"""
import os
import struct
import zlib

# ---------------------------------------------------------------- font
# 5x7 bitmap font. Each glyph is 7 rows of 5 bits, most significant bit
# on the left, as a tuple of 7 integers. "?" is the fallback glyph.
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "a": (0x00, 0x00, 0x0E, 0x01, 0x0F, 0x11, 0x0F),
    "b": (0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x1E),
    "c": (0x00, 0x00, 0x0E, 0x11, 0x10, 0x11, 0x0E),
    "d": (0x01, 0x01, 0x0F, 0x11, 0x11, 0x11, 0x0F),
    "e": (0x00, 0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E),
    "f": (0x06, 0x09, 0x08, 0x1E, 0x08, 0x08, 0x08),
    "g": (0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    "h": (0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x11),
    "i": (0x04, 0x00, 0x0C, 0x04, 0x04, 0x04, 0x0E),
    "j": (0x02, 0x00, 0x0C, 0x02, 0x02, 0x12, 0x0C),
    "k": (0x10, 0x10, 0x12, 0x14, 0x18, 0x14, 0x12),
    "l": (0x0C, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "m": (0x00, 0x00, 0x1A, 0x15, 0x15, 0x15, 0x15),
    "n": (0x00, 0x00, 0x1E, 0x11, 0x11, 0x11, 0x11),
    "o": (0x00, 0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E),
    "p": (0x00, 0x00, 0x1E, 0x11, 0x11, 0x1E, 0x10),
    "q": (0x00, 0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01),
    "r": (0x00, 0x00, 0x16, 0x19, 0x10, 0x10, 0x10),
    "s": (0x00, 0x00, 0x0F, 0x10, 0x0E, 0x01, 0x1E),
    "t": (0x08, 0x08, 0x1E, 0x08, 0x08, 0x08, 0x06),
    "u": (0x00, 0x00, 0x11, 0x11, 0x11, 0x13, 0x0D),
    "v": (0x00, 0x00, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "w": (0x00, 0x00, 0x11, 0x15, 0x15, 0x15, 0x0A),
    "x": (0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11),
    "y": (0x00, 0x00, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    "z": (0x00, 0x00, 0x1F, 0x02, 0x04, 0x08, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    ",": (0x00, 0x00, 0x00, 0x00, 0x0C, 0x04, 0x08),
    ":": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ";": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x04, 0x08),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "%": (0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    "*": (0x00, 0x0A, 0x04, 0x0E, 0x04, 0x0A, 0x00),
    '"': (0x0A, 0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00),
    "•": (0x00, 0x00, 0x0C, 0x0C, 0x00, 0x00, 0x00),
    "—": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    "’": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
}

# ---------------------------------------------------------------- canvas
W, H = 1024, 1024
PAPER = (247, 243, 234)
INK = (22, 22, 22)
NAVY = (14, 30, 51)
GOLD = (201, 162, 39)
GREY = (110, 108, 100)
CAPTION = (60, 58, 52)
PANEL_BORDER = (216, 210, 196)
WHITE = (255, 255, 255)


def _chunk(kind, data):
    out = kind + data
    return struct.pack(">I", len(data)) + out + struct.pack(
        ">I", zlib.crc32(out) & 0xFFFFFFFF)


def write_png(path, pixels):
    """pixels: list of H rows, each a bytes of W*3 RGB."""
    raw = b"".join(b"\x00" + row for row in pixels)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw, 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


class Canvas:
    def __init__(self):
        self.px = bytearray(PAPER * W * H)

    def _set(self, x, y, color):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x0, y0, x1, y1, color):
        for y in range(max(y0, 0), min(y1, H)):
            base = (y * W + max(x0, 0)) * 3
            span = min(x1, W) - max(x0, 0)
            if span > 0:
                self.px[base:base + span * 3] = bytes(color) * span

    def hline(self, x0, x1, y, color, w=1):
        for dy in range(w):
            for x in range(x0, x1):
                self._set(x, y + dy, color)

    def vline(self, x, y0, y1, color, w=1):
        for dx in range(w):
            for y in range(y0, y1):
                self._set(x + dx, y, color)

    def circle(self, cx, cy, r, color, fill=False, width=3):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if fill:
                    if dist <= r:
                        self._set(x, y, color)
                elif abs(dist - r) <= width / 2:
                    self._set(x, y, color)

    def ellipse(self, cx, cy, rx, ry, color, width=2):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                v = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if abs(v - 1) <= 0.12:
                    self._set(x, y, color)

    def polygon(self, pts, color):
        ys = [p[1] for p in pts]
        for y in range(max(min(ys), 0), min(max(ys), H - 1) + 1):
            xs = []
            for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                if y1 == y2:
                    continue
                if (y1 <= y < y2) or (y2 <= y < y1):
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(xs[i]), int(xs[i + 1]) + 1):
                    self._set(x, y, color)

    def text(self, x, y, s, scale, color):
        for ch in s:
            glyph = FONT.get(ch, FONT["?"])
            for row, bits in enumerate(glyph):
                for col in range(5):
                    if bits & (0x10 >> col):
                        self.rect(x + col * scale, y + row * scale,
                                  x + (col + 1) * scale, y + (row + 1) * scale,
                                  color)
            x += 6 * scale
        return x

    def text_w(self, s, scale):
        return len(s) * 6 * scale

    def wrap(self, s, scale, width):
        """Greedy word wrap; returns list of lines fitting width."""
        per = max(1, width // (6 * scale))
        words, lines, cur = s.split(" "), [], ""
        for word in words:
            trial = (cur + " " + word).strip()
            if len(trial) <= per:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                while len(word) > per:  # over-long word: hard split
                    lines.append(word[:per])
                    word = word[per:]
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def rows(self):
        return [bytes(self.px[y * W * 3:(y + 1) * W * 3]) for y in range(H)]

# ---------------------------------------------------------------- layout
STORIES = [
    ("SPACE", (31, 78, 121), "NATO vows to defend space",
     "Russia may put a nuclear weapon in orbit by December.", "satellite"),
    ("LIBYA", (179, 32, 44), "Ukraine sinks warship",
     "Kyiv confirms a sea-drone strike off Libya; UN seeks probe.", "ship"),
    ("HORMUZ", (176, 92, 12), "Tankers hit by sea mines",
     "Ships burn in the Strait of Hormuz; UK logs record attacks.", "drop"),
    ("MYANMAR", (58, 110, 72), "ICJ: Myanmar guilty",
     "Court rules Myanmar committed genocide; 14 nations back it.", "scales"),
    ("TECH", (90, 60, 140), "Nvidia brings back Huang",
     "Huang returns as CEO after Trump intervenes; shares surge.", "chip"),
    ("KOREA", (14, 90, 110), "Jet crosses into South",
     "Suspect aircraft near Ulleung island; residents shelter.", "plane"),
]

ALSO = ("COP31 ends with no deal  •  US loses measles-free status  •  "
        "Sanofi buys Insmed for $41bn  •  Nepal quake 5.6  •  "
        "2031 Women's World Cup hosts named")


def draw_icon(cv, cx, cy, kind, color):
    cv.circle(cx, cy, 30, color, width=3)
    if kind == "satellite":
        cv.ellipse(cx, cy, 24, 11, color)
        cv.rect(cx - 11, cy - 5, cx + 11, cy + 5, color)
        cv.rect(cx + 11, cy - 2, cx + 22, cy + 2, color)
        cv.circle(cx - 26, cy - 18, 4, color, fill=True)
    elif kind == "ship":
        cv.polygon([(cx - 22, cy + 6), (cx + 22, cy + 6),
                    (cx + 13, cy + 20), (cx - 13, cy + 20)], color)
        cv.vline(cx, cy + 6, cy - 18, color, 3)
        cv.polygon([(cx, cy - 18), (cx + 13, cy - 12), (cx, cy - 6)], color)
    elif kind == "drop":
        cv.polygon([(cx, cy - 22), (cx + 14, cy), (cx + 14, cy + 10),
                    (cx - 14, cy + 10), (cx - 14, cy)], color)
        cv.circle(cx, cy + 8, 14, color, fill=True)
    elif kind == "scales":
        cv.vline(cx, cy - 20, cy + 18, color, 3)
        cv.hline(cx - 20, cx + 20, cy - 14, color, 3)
        cv.polygon([(cx - 24, cy), (cx - 12, cy), (cx - 18, cy + 12)], color)
        cv.polygon([(cx + 12, cy), (cx + 24, cy), (cx + 18, cy + 12)], color)
    elif kind == "chip":
        cv.rect(cx - 14, cy - 14, cx + 14, cy - 11, color)
        cv.rect(cx - 14, cy + 11, cx + 14, cy + 14, color)
        cv.rect(cx - 14, cy - 14, cx - 11, cy + 14, color)
        cv.rect(cx + 11, cy - 14, cx + 14, cy + 14, color)
        cv.rect(cx - 6, cy - 6, cx + 6, cy + 6, color)
        for dx in (-9, 0, 9):
            cv.vline(cx + dx, cy - 22, cy - 14, color, 2)
            cv.vline(cx + dx, cy + 14, cy + 22, color, 2)
    elif kind == "plane":
        cv.polygon([(cx - 20, cy + 4), (cx + 22, cy - 12), (cx + 9, cy + 5),
                    (cx + 14, cy + 18), (cx + 3, cy + 9),
                    (cx - 11, cy + 16)], color)


def build():
    cv = Canvas()
    # masthead
    cv.rect(0, 0, W, 190, NAVY)
    kick = "T H E   W O R L D   I N   O N E   D A Y"
    cv.text((W - cv.text_w(kick, 3)) // 2, 30, kick, 3, GOLD)
    date = "24 NOVEMBER 2026"
    cv.text((W - cv.text_w(date, 6)) // 2, 84, date, 6, WHITE)
    cv.hline(W // 2 - 180, W // 2 + 180, 150, GOLD, 2)
    sub = "TUESDAY  •  WORLD NEWS AT A GLANCE"
    cv.text((W - cv.text_w(sub, 3)) // 2, 162, sub, 3, (200, 205, 215))
    # story panels
    mx, my, pw, ph, gx, gy = 28, 202, 466, 224, 20, 14
    for i, (tag, color, head, cap, icon) in enumerate(STORIES):
        x = mx + (i % 2) * (pw + gx)
        y = my + (i // 2) * (ph + gy)
        cv.rect(x, y, x + pw, y + ph, WHITE)
        cv.rect(x, y, x + pw, y + 2, PANEL_BORDER)
        cv.rect(x, y + ph - 2, x + pw, y + ph, PANEL_BORDER)
        cv.rect(x, y, x + 2, y + ph, PANEL_BORDER)
        cv.rect(x + pw - 2, y, x + pw, y + ph, PANEL_BORDER)
        cv.rect(x, y, x + pw, y + 6, color)
        cv.text(x + 18, y + 20, tag, 3, color)
        draw_icon(cv, x + pw - 52, y + 46, icon, color)
        ty = y + 50
        for line in cv.wrap(head, 4, pw - 36 - 96)[:2]:
            cv.text(x + 18, ty, line, 4, INK)
            ty += 36
        ty += 8
        for line in cv.wrap(cap, 3, pw - 36)[:3]:
            cv.text(x + 18, ty, line, 3, CAPTION)
            ty += 27
    # also-today strip
    sy = my + 3 * ph + 2 * gy + 10
    cv.rect(mx, sy, W - mx, sy + 76, WHITE)
    cv.rect(mx, sy, W - mx, sy + 2, PANEL_BORDER)
    cv.rect(mx, sy + 74, W - mx, sy + 76, PANEL_BORDER)
    cv.rect(mx, sy, mx + 2, sy + 76, PANEL_BORDER)
    cv.rect(W - mx - 2, sy, W - mx, sy + 76, PANEL_BORDER)
    cv.text(mx + 16, sy + 10, "ALSO TODAY", 2, (179, 32, 44))
    ty = sy + 32
    for line in cv.wrap(ALSO, 2, W - 2 * mx - 32)[:2]:
        cv.text(mx + 16, ty, line, 2, CAPTION)
        ty += 18
    # footer
    cv.text(mx, H - 24,
            "Compiled from Reuters, SCMP, Al Jazeera and official statements",
            2, GREY)
    foot = "24 NOV 2026"
    cv.text(W - mx - cv.text_w(foot, 2), H - 24, foot, 2, GREY)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = build()
    write_png(os.path.join(out_dir, "entry.png"), cv.rows())


if __name__ == "__main__":
    main()
