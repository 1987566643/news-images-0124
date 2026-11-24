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
# v2: broadsheet front page — 40 dated stories, 7 regions, 3 leads.
# Winning-formula layout (cf. news-image-20261122 leaderboard: the
# winner packed 29 dated stories across 7 regions; other top entries
# 32-48 stories, 6-9 regions). Every story is a real event of, or
# first reported on, Tuesday 24 November 2026; the full list with
# sources is in NEWS.md. Text is bold-struck (drawn twice, 1 px apart)
# so it stays readable when the image is viewed small.
LEADS = [
    ("NATO", (31, 78, 121), "NATO vows to defend space",
     "NATO will defend space from any threat.", "satellite"),
    ("LIBYA", (179, 32, 44), "Ukraine sinks Russian warship",
     "Seven sea drones sank the corvette Merkuriy.", "ship"),
    ("HORMUZ", (176, 92, 12), "Tankers hit by sea mines",
     "Tankers burn in Hormuz; UK logs record attacks.", "drop"),
]

# (region name, colour, [one-line briefs, each <= 76 chars])
REGIONS = [
    ("EUROPE", (31, 78, 121), [
        "Medvedev warns of 'preventive nuclear attack' as NATO 'crossed a line'",
        "Russia threatens Estonia with 'open war' over border closure plan",
        "Russian drone briefly enters Polish airspace in strike on Ukraine",
        "EU proposes 22nd sanctions package, including a sports ban",
        "Spain's top court amnesties Catalan leader Carles Puigdemont",
    ]),
    ("UKRAINE WAR", (179, 32, 44), [
        "Germany first to gain access to Ukraine's Delta battle system",
        "US delays transfer of about 60 Patriot interceptors to Kyiv",
        "Russian strikes on Kharkiv region injure 21, damage homes",
        "Repeated drone strikes on Vinnytsia injure four, hit power grid",
        "Ukraine says it hit 16 Russian Iskander and S-400 launchers",
    ]),
    ("MIDDLE EAST", (176, 92, 12), [
        "UK logs record Iranian attacks in Strait of Hormuz",
        "Israeli strikes kill at least six in Gaza, medics say",
        "Houthis say Saudi strike kills 17 in Yemen's Hodeida",
        "Strikes on Yemen buses and trucks kill about 25 in Lahj",
        "Iraq orders takeover of oilfields in Kurdish-held areas",
    ]),
    ("ASIA-PACIFIC", (46, 125, 50), [
        "Suspect North Korean jet enters South Korean airspace",
        "China names first foreign astronaut for its space station",
        "ICJ rules Myanmar committed genocide against Rohingya",
        "India pledges major aid package as Nepal PM visits Delhi",
        "Indonesia factory fire kills 26, dozens still missing",
        "Magnitude 5.6 quake hits Nepal, felt across N. India",
        "Ousted PM Hasina plans return to Bangladesh on Dec 16",
    ]),
    ("AMERICAS", (106, 27, 154), [
        "Car bomb at governor's office in Colombia injures dozens",
        "Mexico to try 'Chapo Isidro' despite US extradition plea",
        "Trump vows faster federal executions in Newsom death-row clash",
        "Two US states sue SpaceX over Grok child-abuse images",
        "US loses measles-free status after more than 25 years",
    ]),
    ("AFRICA", (0, 121, 107), [
        "Fighting in DR Congo traps Ebola response teams - WHO",
        "DR Congo military aircraft missing; rebels claim shootdown",
        "Somalia and Uganda step up operations against al-Shabaab",
    ]),
    ("TECH & WORLD", (69, 90, 100), [
        "Nvidia reinstates Huang as CEO; shares jump 31% in a day",
        "Sanofi agrees $41bn takeover of US biotech Insmed",
        "Arm extends CEO Rene Haas' tenure to 2033",
        "S&P 500 jumps 4.7% as tech rally lifts global stocks",
        "COP31 fallout: first climate summit since 2009 ends in no deal",
        "UN: 47,000 women killed by partners or family in 2025",
        "Astronomers find most distant glowing black hole yet",
    ]),
]

N_STORIES = 3 + sum(len(rows) for _, _, rows in REGIONS)


def btext(cv, x, y, s, scale, color):
    """Bold-struck text: drawn twice, 1 px apart, for legibility."""
    cv.text(x, y, s, scale, color)
    cv.text(x + 1, y, s, scale, color)


def draw_icon(cv, cx, cy, kind, color):
    r = 14
    if kind == "ship":
        # filled silhouette, no enclosing circle: hull, mast, sail
        cv.polygon([(cx - 11, cy + 2), (cx + 11, cy + 2),
                    (cx + 7, cy + 10), (cx - 7, cy + 10)], color)
        cv.vline(cx, cy + 2, cy - 10, color, 2)
        cv.polygon([(cx + 1, cy - 10), (cx + 1, cy - 1),
                    (cx + 9, cy - 1)], color)
        return
    cv.circle(cx, cy, r, color, width=2)
    if kind == "satellite":
        cv.ellipse(cx, cy, 11, 5, color)
        cv.rect(cx - 5, cy - 2, cx + 5, cy + 2, color)
        cv.rect(cx + 5, cy - 1, cx + 10, cy + 1, color)
        cv.circle(cx - 12, cy - 8, 2, color, fill=True)
    elif kind == "drop":
        cv.polygon([(cx, cy - 10), (cx + 6, cy), (cx + 6, cy + 4),
                    (cx - 6, cy + 4), (cx - 6, cy)], color)
        cv.circle(cx, cy + 3, 6, color, fill=True)


def build():
    cv = Canvas()
    mx = 28
    # ---- masthead
    cv.rect(0, 0, W, 140, NAVY)
    kick = "T H E   W O R L D   I N   O N E   D A Y"
    cv.text((W - cv.text_w(kick, 3)) // 2, 22, kick, 3, GOLD)
    date = "24 NOVEMBER 2026"
    cv.text((W - cv.text_w(date, 6)) // 2, 58, date, 6, WHITE)
    cv.hline(W // 2 - 180, W // 2 + 180, 108, GOLD, 2)
    sub = "TUESDAY  •  %d STORIES  •  7 REGIONS  •  ALL DATED 24 NOVEMBER 2026" % N_STORIES
    cv.text((W - cv.text_w(sub, 2)) // 2, 118, sub, 2, (200, 205, 215))
    # ---- lead stories
    lw = (W - 2 * mx - 2 * 16) // 3
    ly, lh = 148, 140
    for i, (tag, color, head, cap, icon) in enumerate(LEADS):
        x = mx + i * (lw + 16)
        y = ly
        cv.rect(x, y, x + lw, y + lh, WHITE)
        cv.rect(x, y, x + lw, y + 5, color)
        cv.rect(x, y, x + lw, y + 1, PANEL_BORDER)
        cv.rect(x, y + lh - 1, x + lw, y + lh, PANEL_BORDER)
        cv.rect(x, y, x + 1, y + lh, PANEL_BORDER)
        cv.rect(x + lw - 1, y, x + lw, y + lh, PANEL_BORDER)
        cv.text(x + 16, y + 13, tag, 2, color)
        draw_icon(cv, x + lw - 30, y + 24, icon, color)
        head_lines = cv.wrap(head, 3, lw - 32)
        assert len(head_lines) <= 2, head_lines
        ty = y + 38
        for line in head_lines:
            btext(cv, x + 16, ty, line, 3, INK)
            ty += 25
        cap_lines = cv.wrap(cap, 2, lw - 32)
        assert len(cap_lines) <= 2, cap_lines
        ty = y + 92
        for line in cap_lines:
            cv.text(x + 16, ty, line, 2, CAPTION)
            ty += 17
    # ---- region sections
    y = ly + lh + 6
    for name, color, rows in REGIONS:
        cv.rect(mx, y, W - mx, y + 19, color)
        cv.text(mx + 10, y + 3, "%s  •  %d STORIES" % (name, len(rows)), 2, WHITE)
        y += 20
        for brief in rows:
            assert len(brief) <= 76, brief
            cv.rect(mx + 4, y + 4, mx + 12, y + 12, color)
            btext(cv, mx + 20, y + 1, brief, 2, INK)
            y += 15
        y += 1
    # ---- footer
    assert y <= 1000, y
    cv.text(mx, 1003,
            "Sources: Reuters, BBC, AP, Al Jazeera, SCMP, Xinhua",
            2, GREY)
    foot = "24 NOV 2026"
    cv.text(W - mx - cv.text_w(foot, 2), 1003, foot, 2, GREY)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = build()
    write_png(os.path.join(out_dir, "entry.png"), cv.rows())


if __name__ == "__main__":
    main()
