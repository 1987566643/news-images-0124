#!/usr/bin/env python3
"""News-image entry for make.fun's news-image-20261124 bounty, v3.

Draws one 1024x1024 image summing up the world's news of Tuesday
24 November 2026 and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output). Pure Python 3.13 standard library: the PNG is
encoded by hand (zlib + struct) and the text is set in an embedded
5x7 bitmap font written for this program, so it runs offline in the
grader's sandbox with nothing installed. Fully deterministic: two
runs write identical bytes.

Layout: a 1920s broadsheet front page, black-and-white throughout.
Cream newsprint, black ink with one oxblood accent, a big serif
masthead, a UTC timeline strip, three lead stories each with its own
engraved halftone illustration (satellite, corvette, burning tanker),
small spot illustrations on the next ten stories, all 40 dated
stories in 7 regional sections, a schematic "WHERE IT HAPPENED"
world map, a DATE CHECK box, and a sources line. The structure
borrows from the round-3 winning entry of the 23 November contest
(@kevin, 33 stories): timeline, illustrated leads, map, credibility
tags, date check. The look stays vintage newspaper: every picture is
black-and-white stipple and hatching, no colour art.

Every story is a real event of, or first reported on, Tuesday
24 November 2026; the full list with sources is in NEWS.md. Times in
the timeline are only the ones the sources support (market closes
and the night of 23-24 Nov). Credibility tags are conservative:
CONFIRMED means 2+ outlets, OFFICIAL means an authority's own word,
CLAIM means one side's assertion; stories whose sources support no
tag carry none.
"""
import math
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


def _in_poly(x, y, pts):
    """Even-odd point-in-polygon test."""
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                inside = not inside
    return inside


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

    def stipple_poly(self, pts, density, color, seed):
        """Halftone fill clipped to a polygon (for the map's land)."""
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            for x in range(min(xs), max(xs) + 1):
                if _in_poly(x, y, pts) and _hash(x, y, seed) < density:
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

    def tag(self, x, y, word, color=OXBLOOD):
        """Small bordered credibility tag, scale 1; returns its width."""
        w = len(word) * 6 + 8
        self.rect(x, y, x + w, y + 11, PAPER)
        self.rect(x, y, x + w, y + 1, color)
        self.rect(x, y + 10, x + w, y + 11, color)
        self.rect(x, y, x + 1, y + 11, color)
        self.rect(x + w - 1, y, x + w, y + 11, color)
        self.text(x + 4, y + 2, word, 1, color)
        return w

    def rows(self):
        return [bytes(self.px[y * W * 3:(y + 1) * W * 3]) for y in range(H)]

# ---------------------------------------------------------------- layout
# 40 dated stories, 7 regions, 3 leads. Every story is a real event
# of, or first reported on, Tuesday 24 November 2026; the full list
# with sources is in NEWS.md. Rows are (brief, tag, spot icon):
# tag is a credibility tag (None where the sources support none),
# icon names a small spot illustration for stories 4-13.
LEADS = [
    # (headline, deck, tag, picture slug, illustration)
    ("NATO vows to defend space", "NATO will defend space.",
     "OFFICIAL", "SPACE DEFENCE", "satellite"),
    ("Ukraine sinks Russian warship", "Drones sank the Merkuriy.",
     "CONFIRMED", "SUNK OFF LIBYA", "corvette"),
    ("Three tankers hit by sea mines", "Tankers burn in Hormuz.",
     "CLAIM", "BURNING IN HORMUZ", "tanker"),
]

# The day in UTC. Only times the sources support: the night of
# 23-24 Nov (Polish airspace drone, NEWS.md story 6) and the market
# closes (Nikkei 15:00 JST = 06:00 UTC, Wall St opens 09:30 EST =
# 14:30 UTC, NYSE closes 16:00 EST = 21:00 UTC; story 37).
TIMELINE = [
    ("NIGHT", "Drone enters Polish airspace"),
    ("06:00", "Nikkei closes up 3.9%"),
    ("14:30", "Wall Street opens"),
    ("21:00", "S&P 500 ends up 4.7%"),
]

REGIONS = [
    ("EUROPE", [
        ("Medvedev warns of 'preventive nuclear attack'",
         "OFFICIAL", "burst"),
        ("Russia threatens Estonia with 'open war'",
         "CLAIM", "flag"),
        ("Russian drone briefly enters Polish airspace",
         "OFFICIAL", "drone"),
        ("EU proposes 22nd sanctions package, including a sports ban",
         "OFFICIAL", "ban"),
        ("Spain's top court amnesties Catalan leader Carles Puigdemont",
         "OFFICIAL", "gavel"),
    ]),
    ("UKRAINE WAR", [
        ("Germany first to gain access to Ukraine's Delta battle system",
         None, "screen"),
        ("US delays transfer of about 60 Patriot interceptors to Kyiv",
         "CONFIRMED", "missile"),
        ("Russian strikes on Kharkiv region injure 21, damage homes",
         None, "flame"),
        ("Repeated drone strikes on Vinnytsia injure four, hit power grid",
         None, "bolt"),
        ("Ukraine says it hit 16 Russian Iskander and S-400 launchers",
         "CLAIM", "launcher"),
    ]),
    ("MIDDLE EAST", [
        ("UK logs record Iranian attacks in Strait of Hormuz", None, None),
        ("Israeli strikes kill at least six in Gaza, medics say",
         None, None),
        ("Houthis say Saudi strike kills 17 in Yemen's Hodeida",
         None, None),
        ("Strikes on Yemen buses and trucks kill about 25 in Lahj",
         None, None),
        ("Iraq orders takeover of oilfields in Kurdish-held areas",
         None, None),
    ]),
    ("ASIA-PACIFIC", [
        ("Suspect North Korean jet enters South Korean airspace",
         None, None),
        ("China names first foreign astronaut for its space station",
         None, None),
        ("ICJ rules Myanmar committed genocide against Rohingya",
         None, None),
        ("India pledges major aid package as Nepal PM visits Delhi",
         None, None),
        ("Indonesia factory fire kills 26, dozens still missing",
         None, None),
        ("Magnitude 5.6 quake hits Nepal, felt across N. India",
         None, None),
        ("Ousted PM Hasina plans return to Bangladesh on Dec 16",
         None, None),
    ]),
    ("AMERICAS", [
        ("Car bomb injures dozens in Villavicencio, Colombia",
         None, None),
        ("Mexico to try 'Chapo Isidro' despite US plea", None, None),
        ("Trump vows faster executions, hits Newsom", None, None),
        ("States sue SpaceX over Grok child-abuse images", None, None),
        ("US loses measles-free status after 25 years", None, None),
    ]),
    ("AFRICA", [
        ("DR Congo fighting traps Ebola response teams", None, None),
        ("DR Congo warplane missing; rebels claim shootdown",
         None, None),
        ("Somalia, Uganda step up anti-al-Shabaab operations",
         None, None),
    ]),
    ("TECH & WORLD", [
        ("Nvidia reinstates Huang; shares jump 31% in a day",
         None, None),
        ("Sanofi agrees $41bn takeover of US biotech Insmed",
         None, None),
        ("Arm extends CEO Rene Haas' tenure to 2033", None, None),
        ("S&P 500 jumps 4.7% as tech rally lifts stocks", None, None),
        ("COP31 fallout: first no-deal summit since 2009", None, None),
        ("UN: 47,000 women killed by partners, family in 2025",
         None, None),
        ("Astronomers find most distant glowing black hole",
         None, None),
    ]),
]

N_STORIES = 3 + sum(len(rows) for _, rows in REGIONS)

# DATE CHECK: only what NEWS.md's dating notes support. COP31 itself
# ended Sun 22 Nov (only its fallout is 24 Nov news); Trump's
# death-row speech was Mon 23 Nov (the memo and responses ran 24 Nov);
# Shenzhou-24 launches Wed 25 Nov; Hasina's return is planned Dec 16.
DATECHECK = (
    "Left out, before Tuesday: the COP31 summit itself ended Sun 22 Nov; "
    "only its fallout is 24 Nov news. Background only: Trump's death-row "
    "speech was Mon 23 Nov. Not yet: Shenzhou-24 launches Wed 25 Nov; "
    "Hasina plans to return Dec 16."
)

# Schematic world map: rough continent outlines (the map is labelled
# schematic) and numbered pins for the three lead stories.
CONTINENTS = [
    [(716, 732), (748, 720), (786, 726), (792, 742),
     (772, 752), (748, 760), (728, 752), (714, 742)],
    [(768, 772), (790, 766), (796, 784), (786, 806),
     (772, 794), (764, 782)],
    [(836, 722), (856, 718), (864, 728), (852, 734), (838, 732)],
    [(842, 742), (864, 740), (870, 756), (860, 780),
     (850, 768), (842, 754)],
    [(866, 720), (952, 716), (986, 728), (978, 750),
     (940, 758), (902, 748), (872, 736)],
    [(946, 800), (974, 794), (982, 806), (958, 814), (944, 808)],
]
MAP_PINS = [(850, 726, "1"), (856, 744, "2"), (908, 740, "3")]

# ---------------------------------------------------------------- drawing

def draw_spot(pg, cx, cy, kind, color):
    """A tiny spot illustration (~12 px) for stories 4-13."""
    if kind == "burst":
        for dx, dy in ((0, -5), (4, -4), (5, 0), (4, 4), (0, 5),
                       (-4, 4), (-5, 0), (-4, -4)):
            pg.line(cx, cy, cx + dx, cy + dy, color)
        pg.circle(cx, cy, 2, color, fill=True)
    elif kind == "flag":
        pg.vline(cx - 4, cy - 6, cy + 6, color, 1)
        pg.poly([(cx - 4, cy - 6), (cx + 5, cy - 4), (cx - 4, cy - 1)],
                color)
    elif kind == "drone":
        pg.rect(cx - 3, cy - 1, cx + 3, cy + 2, color)
        pg.hline(cx - 6, cx - 2, cy - 4, color)
        pg.hline(cx + 2, cx + 6, cy - 4, color)
        pg.line(cx - 3, cy + 2, cx - 5, cy + 5, color)
        pg.line(cx + 3, cy + 2, cx + 5, cy + 5, color)
    elif kind == "ban":
        pg.circle(cx, cy, 5, color, width=1)
        pg.line(cx - 4, cy + 4, cx + 4, cy - 4, color)
    elif kind == "gavel":
        pg.rect(cx - 5, cy - 5, cx + 2, cy - 2, color)
        pg.line(cx - 1, cy - 2, cx + 5, cy + 5, color)
    elif kind == "screen":
        pg.rect(cx - 5, cy - 5, cx + 5, cy + 2, color)
        pg.rect(cx - 4, cy - 4, cx + 4, cy + 1, PAPER)
        pg.vline(cx, cy + 2, cy + 5, color, 1)
        pg.hline(cx - 3, cx + 3, cy + 5, color)
    elif kind == "missile":
        pg.poly([(cx, cy - 6), (cx + 3, cy + 2), (cx - 3, cy + 2)], color)
        pg.poly([(cx + 3, cy + 1), (cx + 5, cy + 4), (cx + 2, cy + 3)],
                color)
        pg.poly([(cx - 3, cy + 1), (cx - 5, cy + 4), (cx - 2, cy + 3)],
                color)
        pg.circle(cx, cy + 5, 1, color, fill=True)
    elif kind == "flame":
        pg.poly([(cx, cy - 6), (cx + 4, cy - 1), (cx + 3, cy + 4),
                 (cx - 3, cy + 4), (cx - 4, cy - 1)], color)
        pg.circle(cx, cy + 2, 2, PAPER, fill=True)
    elif kind == "bolt":
        pg.poly([(cx + 1, cy - 6), (cx - 3, cy + 1), (cx, cy + 1),
                 (cx - 1, cy + 6), (cx + 3, cy - 1), (cx, cy - 1)], color)
    elif kind == "launcher":
        pg.rect(cx - 5, cy + 2, cx + 5, cy + 5, color)
        pg.line(cx - 2, cy + 2, cx + 3, cy - 5, color)
        pg.circle(cx - 3, cy + 6, 1, color, fill=True)
        pg.circle(cx + 3, cy + 6, 1, color, fill=True)


def _slug_bar(pg, x0, y1, x1, text):
    """Black caption slug across the foot of an illustration."""
    pg.rect(x0, y1 - 16, x1, y1, INK)
    tw = pg.text_w(text, 2)
    pg.text((x0 + x1 - tw) // 2, y1 - 15, text, 2, WHITE)


def draw_lead_sat(pg, x0, y0, x1, y1):
    """NATO in space: a satellite above the curve of the earth,
    engraved halftone style. Sky stipple, stars, a dashed orbit,
    the earth as a stippled band along the foot of the frame."""
    pg.rect(x0, y0, x1, y0 + 2, INK)
    pg.rect(x0, y1 - 2, x1, y1, INK)
    pg.rect(x0, y0, x0 + 2, y1, INK)
    pg.rect(x1 - 2, y0, x1, y1, INK)
    ix0, iy0, ix1, iy1 = x0 + 2, y0 + 2, x1 - 2, y1 - 18
    pg.stipple(ix0, iy0, ix1, iy1, 5, INK, 41)
    for sx, sy in ((60, 12), (120, 26), (240, 10), (280, 30), (30, 40),
                   (200, 44), (150, 8)):
        ax, ay = ix0 + sx, iy0 + sy
        pg.set(ax, ay, INK)
        pg.set(ax - 1, ay, INK)
        pg.set(ax + 1, ay, INK)
        pg.set(ax, ay - 1, INK)
        pg.set(ax, ay + 1, INK)
    # Dashed orbit across the sky.
    for t in range(0, 360, 10):
        ax = (ix0 + ix1) // 2 + int(120 * math.cos(math.radians(t)))
        ay = iy0 + 24 + int(10 * math.sin(math.radians(t)))
        pg.rect(ax, ay, ax + 2, ay + 2, INK)
    # The earth: a stippled band along the foot of the frame, its top
    # edge an arc rising towards the centre (the planet's limb).
    edge = []
    steps = 20
    for i in range(steps + 1):
        ex = ix0 + (ix1 - ix0) * i // steps
        ey = iy1 - 6 - int(16 * math.sin(math.pi * i / steps))
        edge.append((ex, ey))
    pg.stipple_poly(edge + [(ix1, iy1), (ix0, iy1)], 30, INK, 42)
    for (ax, ay), (bx, by) in zip(edge, edge[1:]):
        pg.line(ax, ay, bx, by, INK)
        pg.line(ax, ay + 2, bx, by + 2, INK)
    # The satellite: body, two panels, a dish.
    sx, sy = (ix0 + ix1) // 2 - 10, iy0 + 20
    pg.rect(sx - 44, sy - 4, sx - 12, sy + 4, INK)
    pg.rect(sx - 42, sy - 2, sx - 14, sy + 2, PAPER)
    pg.rect(sx + 12, sy - 4, sx + 44, sy + 4, INK)
    pg.rect(sx + 14, sy - 2, sx + 42, sy + 2, PAPER)
    pg.rect(sx - 10, sy - 6, sx + 10, sy + 6, INK)
    pg.rect(sx - 6, sy - 3, sx + 6, sy + 3, PAPER)
    pg.vline(sx, sy - 10, sy - 6, INK, 1)
    pg.circle(sx, sy + 12, 5, INK, width=1)
    pg.line(sx, sy + 6, sx, sy + 8, INK)
    pg.line(sx, sy + 5, sx, sy + 7, INK)
    _slug_bar(pg, x0, y1, x1, "SPACE DEFENCE")


def draw_lead_ship(pg, x0, y0, x1, y1):
    """The corvette Merkuriy at sea: stippled sky, one cloud, a sea
    drone, the corvette with smoke from her funnel, bow foam."""
    pg.rect(x0, y0, x1, y0 + 2, INK)
    pg.rect(x0, y1 - 2, x1, y1, INK)
    pg.rect(x0, y0, x0 + 2, y1, INK)
    pg.rect(x1 - 2, y0, x1, y1, INK)
    ix0, iy0, ix1, iy1 = x0 + 2, y0 + 2, x1 - 2, y1 - 18
    horizon = iy0 + 26
    pg.stipple(ix0, iy0, ix1, horizon, 5, INK, 51)
    pg.ellipse(ix0 + 52, iy0 + 10, 30, 6, PAPER, fill=True)
    pg.stipple_ellipse(ix0 + 52, iy0 + 10, 30, 6, 10, INK, 52)
    pg.ellipse(ix0 + 52, iy0 + 10, 30, 6, INK)
    # A sea drone, upper right.
    dx, dy = ix1 - 42, iy0 + 12
    pg.rect(dx - 5, dy - 2, dx + 5, dy + 2, INK)
    pg.line(dx - 13, dy - 7, dx - 4, dy - 2, INK)
    pg.line(dx + 4, dy - 2, dx + 13, dy - 7, INK)
    pg.hline(dx - 15, dx - 3, dy - 8, INK)
    pg.hline(dx + 3, dx + 15, dy - 8, INK)
    # Sea: stipple deepening downwards, plus wave strokes.
    pg.stipple(ix0, horizon, ix1, horizon + 10, 8, INK, 53)
    pg.stipple(ix0, horizon + 10, ix1, iy1, 16, INK, 54)
    for wy in (horizon + 6, horizon + 16, horizon + 24):
        x = ix0 + 6
        while x < ix1 - 20:
            pg.hline(x, x + 12, wy, INK)
            x += 26
    # The corvette, centre: hull, superstructure, funnel, smoke.
    deck = horizon + 12
    cx0, cx1 = ix0 + 78, ix1 - 78
    pg.poly([(cx0, deck), (cx1, deck), (cx1 - 4, deck + 8),
             (cx0 + 10, deck + 8), (cx0 + 2, deck + 4)], INK)
    pg.hline(cx0 + 4, cx1 - 4, deck + 1, PAPER)
    for px in range(cx0 + 16, cx1 - 10, 18):
        pg.rect(px, deck + 4, px + 2, deck + 7, PAPER)
    pg.rect(cx0 + 34, deck - 12, cx0 + 84, deck, INK)
    for wx in range(cx0 + 40, cx0 + 78, 14):
        pg.rect(wx, deck - 8, wx + 6, deck - 3, PAPER)
    pg.rect(cx0 + 40, deck - 18, cx0 + 66, deck - 12, INK)
    pg.rect(cx0 + 92, deck - 11, cx0 + 104, deck, INK)
    pg.vline(cx0 + 52, deck - 28, deck - 18, INK, 2)
    pg.poly([(cx0 + 54, deck - 28), (cx0 + 64, deck - 25),
             (cx0 + 54, deck - 22)], INK)
    for px, py, pr, seed in ((cx0 + 98, deck - 18, 8, 55),
                             (cx0 + 110, deck - 23, 9, 56)):
        pg.ellipse(px, py, pr, pr - 3, PAPER, fill=True)
        pg.stipple_ellipse(px, py, pr, pr - 3, 35, INK, seed)
        pg.ellipse(px, py, pr, pr - 3, INK)
    pg.ellipse(cx0 + 14, deck + 9, 22, 3, PAPER, fill=True)
    pg.ellipse(cx1 - 14, deck + 9, 20, 3, PAPER, fill=True)
    _slug_bar(pg, x0, y1, x1, "SUNK OFF LIBYA")


def draw_lead_tanker(pg, x0, y0, x1, y1):
    """A tanker burning in the Strait of Hormuz: stippled sky, a
    long low hull, stern superstructure, funnel smoke, flames
    amidships, and a sea mine in the foreground water."""
    pg.rect(x0, y0, x1, y0 + 2, INK)
    pg.rect(x0, y1 - 2, x1, y1, INK)
    pg.rect(x0, y0, x0 + 2, y1, INK)
    pg.rect(x1 - 2, y0, x1, y1, INK)
    ix0, iy0, ix1, iy1 = x0 + 2, y0 + 2, x1 - 2, y1 - 18
    horizon = iy0 + 26
    pg.stipple(ix0, iy0, ix1, horizon, 5, INK, 61)
    pg.ellipse(ix0 + 250, iy0 + 10, 28, 6, PAPER, fill=True)
    pg.stipple_ellipse(ix0 + 250, iy0 + 10, 28, 6, 10, INK, 62)
    pg.ellipse(ix0 + 250, iy0 + 10, 28, 6, INK)
    pg.stipple(ix0, horizon, ix1, horizon + 10, 8, INK, 63)
    pg.stipple(ix0, horizon + 10, ix1, iy1, 16, INK, 64)
    for wy in (horizon + 6, horizon + 16, horizon + 24):
        x = ix0 + 6
        while x < ix1 - 20:
            pg.hline(x, x + 12, wy, INK)
            x += 26
    # The tanker: long low hull, stern castle, funnel, flames.
    deck = horizon + 12
    tx0, tx1 = ix0 + 40, ix1 - 40
    pg.poly([(tx0, deck), (tx1, deck), (tx1 - 6, deck + 9),
             (tx0 + 8, deck + 9)], INK)
    pg.hline(tx0 + 4, tx1 - 4, deck + 1, PAPER)
    pg.rect(tx1 - 52, deck - 20, tx1 - 22, deck, INK)
    for wy in range(deck - 16, deck - 4, 6):
        pg.rect(tx1 - 48, wy, tx1 - 26, wy + 2, PAPER)
    pg.rect(tx1 - 16, deck - 14, tx1 - 6, deck, INK)
    pg.vline(tx0 + 60, deck - 26, deck - 12, INK, 2)
    for px, py, pr, seed in ((tx0 + 54, deck - 30, 8, 65),
                             (tx0 + 68, deck - 36, 9, 66)):
        pg.ellipse(px, py, pr, pr - 3, PAPER, fill=True)
        pg.stipple_ellipse(px, py, pr, pr - 3, 35, INK, seed)
        pg.ellipse(px, py, pr, pr - 3, INK)
    # Flames amidships: wide ink tongues with paper cores, each
    # topped by a puff of smoke.
    for fx in (tx0 + 110, tx0 + 138, tx0 + 164):
        pg.poly([(fx, deck - 14), (fx + 8, deck - 4), (fx + 6, deck),
                 (fx - 6, deck), (fx - 8, deck - 4)], INK)
        pg.poly([(fx, deck - 8), (fx + 3, deck - 2), (fx - 3, deck - 2)],
                PAPER)
        pg.ellipse(fx, deck - 20, 7, 5, PAPER, fill=True)
        pg.stipple_ellipse(fx, deck - 20, 7, 5, 35, INK, 67)
        pg.ellipse(fx, deck - 20, 7, 5, INK)
    pg.ellipse(tx0 + 60, deck + 10, 60, 3, PAPER, fill=True)
    pg.ellipse(tx1 - 60, deck + 10, 50, 3, PAPER, fill=True)
    # A sea mine in the foreground water, lower right.
    mx, my = ix1 - 34, iy1 - 8
    pg.circle(mx, my, 5, INK, fill=True)
    for dx, dy in ((0, -8), (6, -6), (8, 0), (6, 6), (0, 8),
                   (-6, 6), (-8, 0), (-6, -6)):
        pg.line(mx, my, mx + dx, my + dy, INK)
    _slug_bar(pg, x0, y1, x1, "BURNING IN HORMUZ")


def draw_map(pg, x0, y0, x1, y1):
    """Schematic world map: stippled continent blobs, numbered pins
    for the three lead stories. Deliberately simple; the legend says
    the map is schematic."""
    pg.rect(x0, y0, x1, y0 + 1, INK)
    pg.rect(x0, y1 - 1, x1, y1, INK)
    pg.rect(x0, y0, x0 + 1, y1, INK)
    pg.rect(x1 - 1, y0, x1, y1, INK)
    for pts in CONTINENTS:
        pg.stipple_poly(pts, 14, INK, 71)
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            pg.line(ax, ay, bx, by, INK)
    # A few wave dashes in the sea, and a small compass rose.
    for wx, wy in ((720, 800), (900, 780), (760, 830), (950, 720),
                   (820, 820), (920, 800)):
        pg.hline(wx, wx + 14, wy, FAINT)
    pg.circle(726, 834, 8, INK, width=1)
    pg.line(726, 834, 726, 824, INK)
    pg.line(726, 834, 734, 834, INK)
    pg.text(723, 812, "N", 1, INK)
    for px, py, num in MAP_PINS:
        pg.circle(px, py, 7, INK, fill=True)
        pg.circle(px, py, 7, PAPER, width=1)
        pg.text(px - 2, py - 3, num, 1, WHITE)

# ---------------------------------------------------------------- layout build

def draw_section(pg, y, name, rows, x0, x1, max_len):
    """One regional section: black bar, then one row per story.
    Returns the y just below the section (including a 1 px gap)."""
    pg.rect(x0, y, x1, y + 17, INK)
    pg.text(x0 + 10, y + 2, "%s  •  %d STORIES" % (name, len(rows)),
            2, WHITE)
    y += 17
    for brief, tag, icon in rows:
        assert len(brief) <= max_len, brief
        if icon:
            draw_spot(pg, x0 + 10, y + 7, icon, OXBLOOD)
        else:
            pg.rect(x0 + 4, y + 3, x0 + 12, y + 11, OXBLOOD)
        pg.btext(x0 + 20, y + 1, brief, 2, INK)
        if tag:
            assert len(brief) <= 62, brief
            w = len(tag) * 6 + 8
            pg.tag(x1 - 2 - w, y + 2, tag)
        y += 15
    return y + 1


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
    # ---- the day in UTC
    pg.hline(mx, W - mx, 126, INK, 1)
    pg.hline(mx, W - mx, 150, INK, 1)
    pg.rect(mx, 127, 124, 149, INK)
    pg.text(32, 133, "THE DAY IN UTC", 1, WHITE)
    bounds = [124, 343, 562, 781, 1000]
    for bx in bounds[1:-1]:
        pg.vline(bx, 127, 149, INK, 1)
    for (when, what), cx0 in zip(TIMELINE, bounds):
        pg.btext(cx0 + 10, 127, when, 2, INK)
        pg.text(cx0 + 10, 141, what, 1, INK)
    # ---- lead stories, each with its own halftone illustration
    lw = (W - 2 * mx - 2 * 14) // 3
    for i, (head, deck, tag, slug, art) in enumerate(LEADS):
        x = mx + i * (lw + 14)
        if art == "satellite":
            draw_lead_sat(pg, x, 156, x + lw, 232)
        elif art == "corvette":
            draw_lead_ship(pg, x, 156, x + lw, 232)
        else:
            draw_lead_tanker(pg, x, 156, x + lw, 232)
        head_lines = pg.wrap(head, 2, lw)
        assert len(head_lines) <= 2, head_lines
        ty = 238
        for line in head_lines:
            pg.btext(x, ty, line, 2, INK)
            ty += 17
        tw = pg.tag(x, 275, tag)
        pg.text(x + tw + 6, 277, deck, 1, GREY)
    # ---- region sections, first four full width
    y = 294
    for name, rows in REGIONS[:4]:
        y = draw_section(pg, y, name, rows, mx, W - mx, 79)
    # ---- bottom split: last three regions left, map + date check right
    y = draw_section(pg, y, "AMERICAS", REGIONS[4][1], mx, 688, 52)
    y = draw_section(pg, y, "AFRICA", REGIONS[5][1], mx, 688, 52)
    y = draw_section(pg, y, "TECH & WORLD", REGIONS[6][1], mx, 688, 52)
    assert y <= 978, y
    pg.rect(704, 696, 1000, 712, INK)
    pg.text(712, 698, "WHERE IT HAPPENED", 2, WHITE)
    draw_map(pg, 704, 716, 1000, 852)
    pg.text(704, 856, "1 NATO SPACE VOW • 2 MERKURIY OFF LIBYA", 1, INK)
    pg.text(704, 865, "3 TANKERS IN HORMUZ • MAP IS SCHEMATIC", 1, INK)
    # DATE CHECK box
    lines = pg.wrap(DATECHECK, 1, 280)
    box_y1 = 896 + 4 + len(lines) * 9 + 4
    pg.rect(704, 880, 1000, 896, OXBLOOD)
    pg.text(712, 882, "DATE CHECK", 2, WHITE)
    pg.rect(704, 880, 1000, 881, OXBLOOD)
    pg.rect(704, box_y1 - 1, 1000, box_y1, OXBLOOD)
    pg.rect(704, 880, 705, box_y1, OXBLOOD)
    pg.rect(999, 880, 1000, box_y1, OXBLOOD)
    ly = 900
    for line in lines:
        pg.text(712, ly, line, 1, INK)
        ly += 9
    assert box_y1 <= 978, box_y1
    # ---- sources and tag legend
    pg.hline(mx, W - mx, 994, INK, 1)
    src = ("SOURCES: REUTERS, BBC, AP, GUARDIAN, INDEPENDENT, "
           "KYIV INDEPENDENT, SCMP, XINHUA, CNN, UN NEWS")
    pg.text((W - pg.text_w(src, 1)) // 2, 999, src, 1, GREY)
    leg = ("CONFIRMED 2+ OUTLETS • OFFICIAL AN AUTHORITY'S OWN WORD "
           "• CLAIM ONE SIDE SAYS")
    pg.text((W - pg.text_w(leg, 1)) // 2, 1008, leg, 1, GREY)
    return pg


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    pg = build()
    write_png(os.path.join(out_dir, "entry.png"), pg.rows())


if __name__ == "__main__":
    main()
