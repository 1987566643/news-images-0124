#!/usr/bin/env python3
"""News-image entry for make.fun's news-image-20261124 bounty.

Draws one 1024x1024 image summing up the world's news of Tuesday
24 November 2026 and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output). Pure Python 3.13 standard library: the PNG is
encoded by hand (zlib + struct) and the text is set in an embedded
5x7 bitmap font written for this program, so it runs offline in the
grader's sandbox with nothing installed. Fully deterministic: two
runs write identical bytes.

Layout: a 1920s broadsheet front page. Cream newsprint, black ink
with one oxblood accent, a big serif masthead, a dateline, a large
halftone-style picture of the day (the corvette Merkuriy at sea),
three lead stories, and all 40 dated stories in 7 regional columns.
Every story is a real event of, or first reported on, 24 November
2026; the full list with sources is in NEWS.md.
"""
import os
import struct
import zlib

# ---------------------------------------------------------------- font
# 5x7 bitmap font, designed for this program. Each glyph is 7 rows of
# 5 bits, written as strings ("#" set, "." clear), top row first.
# "?" is the fallback glyph.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10001", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00100", "00010", "00010", "10010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11110", "01000", "01000", "01000", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "/": ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    "*": ("00000", "01010", "00100", "01110", "00100", "01010", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "•": ("00000", "00000", "01100", "01100", "00000", "00000", "00000"),
    "—": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "’": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
}

# ---------------------------------------------------------------- canvas
W, H = 1024, 1024
PAPER = (247, 243, 234)      # cream newsprint
INK = (24, 22, 20)           # black ink
OXBLOOD = (138, 30, 32)      # the one accent colour
GREY = (112, 108, 98)        # captions and fine print
FAINT = (120, 116, 106)      # distant objects
WHITE = (255, 255, 255)


def _chunk(kind, data):
    body = kind + data
    return (struct.pack(">I", len(data)) + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))


def write_png(path, rows):
    raw = b"".join(b"\x00" + row for row in rows)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw, 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


def _hash(x, y, seed):
    """Deterministic 0..99 pseudo-random value for stipple patterns."""
    v = (x * 2654435761 + y * 40503 + seed * 974634) & 0xFFFFFFFF
    return (v ^ (v >> 16)) % 100


class Page:
    def __init__(self):
        self.px = bytearray(PAPER * W * H)

    def set(self, x, y, color):
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
                self.set(x, y + dy, color)

    def vline(self, x, y0, y1, color, w=1):
        for dx in range(w):
            for y in range(y0, y1):
                self.set(x + dx, y, color)

    def line(self, x0, y0, x1, y1, color):
        """Bresenham line, 1 px wide."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, fill=False, width=2):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if fill:
                    if d <= r:
                        self.set(x, y, color)
                elif abs(d - r) <= width / 2:
                    self.set(x, y, color)

    def ellipse(self, cx, cy, rx, ry, color, fill=False, width=2):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                v = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if fill:
                    if v <= 1:
                        self.set(x, y, color)
                elif abs(v - 1) <= 0.14:
                    self.set(x, y, color)

    def poly(self, pts, color):
        """Scanline-filled polygon."""
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
                    self.set(x, y, color)

    def diamond(self, cx, cy, r, color):
        self.poly([(cx, cy - r), (cx + r, cy),
                   (cx, cy + r), (cx - r, cy)], color)

    def stipple(self, x0, y0, x1, y1, density, color, seed):
        """Halftone dots: a pixel is set when its hash is under density."""
        for y in range(max(y0, 0), min(y1, H)):
            for x in range(max(x0, 0), min(x1, W)):
                if _hash(x, y, seed) < density:
                    self.set(x, y, color)

    def stipple_ellipse(self, cx, cy, rx, ry, density, color, seed):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                v = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if v <= 1 and _hash(x, y, seed) < density:
                    self.set(x, y, color)

    def text(self, x, y, s, scale, color):
        for ch in s:
            glyph = FONT.get(ch, FONT["?"])
            for row, bits in enumerate(glyph):
                for col, bit in enumerate(bits):
                    if bit == "1":
                        self.rect(x + col * scale, y + row * scale,
                                  x + (col + 1) * scale,
                                  y + (row + 1) * scale, color)
            x += 6 * scale
        return x

    def btext(self, x, y, s, scale, color):
        """Bold-struck text: drawn twice, 1 px apart, for legibility."""
        self.text(x, y, s, scale, color)
        self.text(x + 1, y, s, scale, color)

    def text_w(self, s, scale):
        return len(s) * 6 * scale

    def wrap(self, s, scale, width):
        """Greedy word wrap; returns lines fitting width."""
        per = max(1, width // (6 * scale))
        words, lines, cur = s.split(" "), [], ""
        for word in words:
            trial = (cur + " " + word).strip()
            if len(trial) <= per:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                while len(word) > per:
                    lines.append(word[:per])
                    word = word[per:]
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def rows(self):
        return [bytes(self.px[y * W * 3:(y + 1) * W * 3]) for y in range(H)]

# ---------------------------------------------------------------- layout
# 40 dated stories, 7 regions, 3 leads. Every story is a real event
# of, or first reported on, Tuesday 24 November 2026; the full list
# with sources is in NEWS.md. Briefs are one line each (<= 79 chars).
LEADS = [
    ("NATO", "NATO vows to defend space",
     "NATO will defend space.", "satellite"),
    ("LIBYA", "Ukraine sinks Russian warship",
     "Drones sank the Merkuriy.", "ship"),
    ("HORMUZ", "Three tankers hit by sea mines",
     "Tankers burn in Hormuz.", "flame"),
]

REGIONS = [
    ("EUROPE", [
        "Medvedev warns of 'preventive nuclear attack' as NATO 'crossed a line'",
        "Russia threatens Estonia with 'open war' over border closure plan",
        "Russian drone briefly enters Polish airspace in strike on Ukraine",
        "EU proposes 22nd sanctions package, including a sports ban",
        "Spain's top court amnesties Catalan leader Carles Puigdemont",
    ]),
    ("UKRAINE WAR", [
        "Germany first to gain access to Ukraine's Delta battle system",
        "US delays transfer of about 60 Patriot interceptors to Kyiv",
        "Russian strikes on Kharkiv region injure 21, damage homes",
        "Repeated drone strikes on Vinnytsia injure four, hit power grid",
        "Ukraine says it hit 16 Russian Iskander and S-400 launchers",
    ]),
    ("MIDDLE EAST", [
        "UK logs record Iranian attacks in Strait of Hormuz",
        "Israeli strikes kill at least six in Gaza, medics say",
        "Houthis say Saudi strike kills 17 in Yemen's Hodeida",
        "Strikes on Yemen buses and trucks kill about 25 in Lahj",
        "Iraq orders takeover of oilfields in Kurdish-held areas",
    ]),
    ("ASIA-PACIFIC", [
        "Suspect North Korean jet enters South Korean airspace",
        "China names first foreign astronaut for its space station",
        "ICJ rules Myanmar committed genocide against Rohingya",
        "India pledges major aid package as Nepal PM visits Delhi",
        "Indonesia factory fire kills 26, dozens still missing",
        "Magnitude 5.6 quake hits Nepal, felt across N. India",
        "Ousted PM Hasina plans return to Bangladesh on Dec 16",
    ]),
    ("AMERICAS", [
        "Car bomb at governor's office in Colombia injures dozens",
        "Mexico to try 'Chapo Isidro' despite US extradition plea",
        "Trump vows faster federal executions in Newsom death-row clash",
        "Two US states sue SpaceX over Grok child-abuse images",
        "US loses measles-free status after more than 25 years",
    ]),
    ("AFRICA", [
        "Fighting in DR Congo traps Ebola response teams - WHO",
        "DR Congo military aircraft missing; rebels claim shootdown",
        "Somalia and Uganda step up operations against al-Shabaab",
    ]),
    ("TECH & WORLD", [
        "Nvidia reinstates Huang as CEO; shares jump 31% in a day",
        "Sanofi agrees $41bn takeover of US biotech Insmed",
        "Arm extends CEO Rene Haas' tenure to 2033",
        "S&P 500 jumps 4.7% as tech rally lifts global stocks",
        "COP31 fallout: first climate summit since 2009 ends in no deal",
        "UN: 47,000 women killed by partners or family in 2025",
        "Astronomers find most distant glowing black hole yet",
    ]),
]

N_STORIES = 3 + sum(len(rows) for _, rows in REGIONS)


def draw_icon(pg, cx, cy, kind, color):
    """Small spot illustration for a lead column (~34 px across)."""
    if kind == "satellite":
        pg.ellipse(cx, cy, 11, 5, color)
        pg.rect(cx - 5, cy - 2, cx + 5, cy + 2, color)
        pg.rect(cx - 16, cy - 1, cx - 6, cy + 1, color)
        pg.rect(cx + 6, cy - 1, cx + 16, cy + 1, color)
        pg.line(cx - 16, cy - 1, cx - 11, cy - 6, color)
        pg.line(cx + 11, cy - 6, cx + 16, cy - 1, color)
        pg.circle(cx - 13, cy - 11, 2, color, fill=True)
    elif kind == "ship":
        pg.poly([(cx - 12, cy + 2), (cx + 12, cy + 2),
                 (cx + 8, cy + 10), (cx - 8, cy + 10)], color)
        pg.vline(cx, cy + 2, cy - 11, color, 2)
        pg.poly([(cx + 1, cy - 11), (cx + 1, cy - 1),
                 (cx + 10, cy - 1)], color)
    elif kind == "flame":
        pg.poly([(cx, cy - 12), (cx + 6, cy - 2), (cx + 6, cy + 2),
                 (cx - 6, cy + 2), (cx - 6, cy - 2)], color)
        pg.circle(cx, cy + 3, 6, color, fill=True)


def draw_photo(pg, x0, y0, x1, y1):
    """The picture of the day: the corvette Merkuriy at sea, drawn as
    an engraved halftone photograph. Stippled sky and clouds, a sea
    drone in the air, the corvette with smoke from her funnel, waves,
    and a distant ship on the horizon."""
    pg.rect(x0, y0, x1, y0 + 2, INK)
    pg.rect(x0, y1 - 2, x1, y1, INK)
    pg.rect(x0, y0, x0 + 2, y1, INK)
    pg.rect(x1 - 2, y0, x1, y1, INK)
    ix0, iy0, ix1, iy1 = x0 + 2, y0 + 2, x1 - 2, y1 - 2
    horizon = iy0 + 62
    # Sky: light stipple, denser near the horizon.
    pg.stipple(ix0, iy0, ix1, horizon - 24, 5, INK, 11)
    pg.stipple(ix0, horizon - 24, ix1, horizon, 10, INK, 12)
    # Clouds: paper ellipses cut out of the stipple, with ink rims.
    # Kept clear of the funnel smoke so the two never merge.
    for cx, cy, rx, ry, seed in ((230, iy0 + 18, 62, 10, 61),
                                 (850, iy0 + 24, 55, 9, 63)):
        pg.ellipse(cx, cy, rx, ry, PAPER, fill=True)
        pg.stipple_ellipse(cx, cy, rx, ry, 10, INK, seed)
        pg.ellipse(cx, cy, rx, ry, INK)
    # A sea drone in the sky, upper right.
    dx, dy = 820, iy0 + 24
    pg.rect(dx - 8, dy - 3, dx + 8, dy + 4, INK)
    pg.line(dx - 20, dy - 12, dx - 6, dy - 4, INK)
    pg.line(dx + 6, dy - 4, dx + 20, dy - 12, INK)
    pg.line(dx - 20, dy + 12, dx - 6, dy + 4, INK)
    pg.line(dx + 6, dy + 4, dx + 20, dy + 12, INK)
    pg.hline(dx - 24, dx - 2, dy - 13, INK)
    pg.hline(dx + 2, dx + 24, dy - 13, INK)
    pg.hline(dx - 24, dx - 2, dy + 13, INK)
    pg.hline(dx + 2, dx + 24, dy + 13, INK)
    # Sea: stipple deepening towards the bottom of the picture.
    for (ya, yb, dens, seed) in ((horizon, horizon + 20, 8, 21),
                                 (horizon + 20, horizon + 36, 14, 22),
                                 (horizon + 36, iy1, 20, 23)):
        pg.stipple(ix0, ya, ix1, yb, dens, INK, seed)
    # Wave lines: short strokes that rise and fall.
    for wy in (horizon + 8, horizon + 20, horizon + 32, horizon + 44):
        x = ix0 + 8
        while x < ix1 - 30:
            off = ((x * 7 + wy * 13) % 5) - 2
            pg.hline(x, x + 16, wy + off, INK)
            x += 34
    # Distant ship on the horizon, left, in a faint tone.
    fx, fy = ix0 + 110, horizon - 6
    pg.poly([(fx, fy + 4), (fx + 64, fy + 4), (fx + 58, fy + 12),
             (fx + 6, fy + 12)], FAINT)
    pg.rect(fx + 28, fy - 8, fx + 33, fy + 4, FAINT)
    # The corvette herself, centre: hull, superstructure, funnel
    # with smoke, masts, a gun turret forward, portholes, foam.
    deck = horizon + 26
    pg.poly([(348, deck), (666, deck), (676, deck + 6),
             (658, deck + 20), (362, deck + 20), (342, deck + 10)], INK)
    pg.hline(350, 664, deck + 1, PAPER)
    for px in range(380, 640, 36):
        pg.rect(px, deck + 10, px + 4, deck + 14, PAPER)
    pg.rect(440, deck - 26, 540, deck, INK)
    for wx in range(452, 530, 22):
        pg.rect(wx, deck - 18, wx + 10, deck - 10, PAPER)
    pg.rect(455, deck - 36, 505, deck - 26, INK)
    pg.rect(555, deck - 24, 580, deck, INK)
    pg.hline(555, 580, deck - 17, PAPER, 2)
    pg.vline(470, deck - 62, deck - 36, INK, 2)
    pg.poly([(472, deck - 62), (488, deck - 57), (472, deck - 52)], INK)
    pg.vline(620, deck - 34, deck, INK, 2)
    pg.rect(630, deck - 12, 660, deck, INK)
    pg.line(660, deck - 6, 686, deck - 10, INK)
    # Smoke from the funnel, drifting right, as small stippled puffs.
    for cx, cy, rx, ry, seed in ((566, deck - 36, 16, 8, 31),
                                 (588, deck - 46, 18, 9, 32),
                                 (612, deck - 56, 20, 10, 33)):
        pg.ellipse(cx, cy, rx, ry, PAPER, fill=True)
        pg.stipple_ellipse(cx, cy, rx, ry, 35, INK, seed)
        pg.ellipse(cx, cy, rx, ry, INK)
    # Foam where the hull meets the water.
    pg.ellipse(380, deck + 21, 46, 5, PAPER, fill=True)
    pg.ellipse(640, deck + 21, 40, 5, PAPER, fill=True)
    pg.ellipse(510, deck + 22, 120, 4, PAPER, fill=True)


def build():
    pg = Page()
    mx = 24
    # ---- masthead furniture
    pg.text(mx, 16, "NO. 14,833", 2, INK)
    mid = "VOL. I - NO. 328"
    pg.text((W - pg.text_w(mid, 2)) // 2, 16, mid, 2, INK)
    right = "PRICE ONE CENT"
    pg.text(W - mx - pg.text_w(right, 2), 16, right, 2, INK)
    kick = "THE WORLD IN ONE DAY"
    pg.btext((W - pg.text_w(kick, 6)) // 2, 36, kick, 6, INK)
    pg.hline(mx, W - mx, 84, INK, 2)
    pg.hline(mx, W - mx, 88, INK, 2)
    for dx in (256, 512, 768):
        pg.diamond(dx, 86, 5, INK)
    date = "TUESDAY, NOVEMBER 24, 2026"
    pg.btext((W - pg.text_w(date, 3)) // 2, 94, date, 3, OXBLOOD)
    pg.hline(mx, W - mx, 120, INK, 1)
    # ---- lead stories
    lw = (W - 2 * mx - 2 * 14) // 3
    ly = 126
    for i, (tag, head, cap, icon) in enumerate(LEADS):
        x = mx + i * (lw + 14)
        draw_icon(pg, x + lw - 20, ly + 18, icon, OXBLOOD)
        head_lines = pg.wrap(head, 2, lw - 48)
        assert len(head_lines) <= 2, head_lines
        ty = ly + 2
        for line in head_lines:
            pg.btext(x, ty, line, 2, INK)
            ty += 17
        pg.text(x, ly + 36, cap, 2, GREY)
    # ---- picture of the day
    draw_photo(pg, mx, 184, W - mx, 300)
    cap = "THE CORVETTE MERKURY, SUNK BY UKRAINIAN SEA DRONES OFF LIBYA."
    pg.text((W - pg.text_w(cap, 2)) // 2, 304, cap, 2, GREY)
    # ---- region sections
    y = 324
    for name, rows in REGIONS:
        pg.rect(mx, y, W - mx, y + 17, INK)
        pg.text(mx + 10, y + 2, "%s  •  %d STORIES" % (name, len(rows)),
                2, WHITE)
        y += 17
        for brief in rows:
            assert len(brief) <= 79, brief
            pg.rect(mx + 4, y + 3, mx + 12, y + 11, OXBLOOD)
            pg.btext(mx + 20, y + 1, brief, 2, INK)
            y += 15
        y += 1
    assert y <= 1006, y
    pg.hline(mx, W - mx, 1009, INK, 1)
    src = "SOURCES: REUTERS, BBC, AP, AL JAZEERA, SCMP, XINHUA, CNN"
    pg.text((W - pg.text_w(src, 1)) // 2, 1012, src, 1, GREY)
    return pg


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    pg = build()
    write_png(os.path.join(out_dir, "entry.png"), pg.rows())


if __name__ == "__main__":
    main()
