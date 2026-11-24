#!/usr/bin/env python3
"""One-day world news poster for the make.fun news-image-20261124 bounty.

Renders a 1024x1024 broadsheet front page that sums up Tuesday
24 November 2026: a navy masthead naming the date, three lead panels
for the day's biggest stories, and seven regional sections holding
37 one-line briefs -- 40 dated stories in all. The full story list,
with the source each item was verified against, lives in NEWS.md.

Only the Python standard library is used. The PNG bytes are assembled
by hand (zlib + struct) and the lettering comes from a small 5x7
bitmap face defined below, so the program runs with no network and
nothing installed. It is deterministic: every run writes the same
bytes to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
"""

import os
import struct
import zlib

# ------------------------------------------------------------------ face
# A 5-by-7 bitmap face. One entry per character: seven rows of five
# cells, '#' for ink and '.' for paper, top row first. Anything not
# listed falls back to '?'. The face is drawn at integer scales, so a
# letter is always crisp; bold copy is the same glyph plotted once
# more, one pixel to the right.
GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "a": (".....", ".....", ".####", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "#..#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "####.", "#....", "#...."),
    "q": (".....", ".....", ".####", "#...#", ".####", "....#", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", ".####", "....#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", "..#..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", "..#..", ".#..."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "$": ("..#..", ".####", "#.#.#", ".###.", "..#.#", "####.", "..#.."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "%": ("##..#", "##..#", "....#", "...#.", "..#..", "#..##", "#..##"),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "*": (".....", ".#.#.", "..#..", ".###.", "..#..", ".#.#.", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "•": (".....", ".....", ".##..", ".##..", ".....", ".....", "....."),
    "—": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "’": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
}

# ------------------------------------------------------------------ page
PAGE_W, PAGE_H = 1024, 1024
PAPER = (247, 243, 234)
INK = (22, 22, 22)
NAVY = (14, 30, 51)
GOLD = (201, 162, 39)
GREY = (110, 108, 100)
MUTED = (60, 58, 52)
EDGE = (216, 210, 196)
WHITE = (255, 255, 255)


def _chunk(tag, payload):
    body = tag + payload
    return (struct.pack(">I", len(payload)) + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))


def save_png(path, page):
    raw = b"".join(b"\x00" + row for row in page.scanlines())
    blob = (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB",
                                          page.w, page.h, 8, 2, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(raw, 9))
            + _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(blob)


class Page:
    """A flat RGB canvas with a few drawing verbs."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(bytes(bg) * (w * h))

    def dot(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            off = (y * self.w + x) * 3
            self.buf[off:off + 3] = bytes(rgb)

    def box(self, x0, y0, x1, y1, rgb):
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, self.w), min(y1, self.h)
        if x1 <= x0 or y1 <= y0:
            return
        strip = bytes(rgb) * (x1 - x0)
        for y in range(y0, y1):
            off = (y * self.w + x0) * 3
            self.buf[off:off + len(strip)] = strip

    def hbar(self, x0, x1, y, rgb, thick=1):
        for k in range(thick):
            self.box(x0, y + k, x1, y + k + 1, rgb)

    def vbar(self, x, y0, y1, rgb, thick=1):
        for k in range(thick):
            self.box(x + k, y0, x + k + 1, y1, rgb)

    def disc(self, cx, cy, r, rgb, solid=False, thick=2):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if solid:
                    if d <= r:
                        self.dot(x, y, rgb)
                elif abs(d - r) <= thick / 2:
                    self.dot(x, y, rgb)

    def fill_poly(self, pts, rgb):
        top = max(min(p[1] for p in pts), 0)
        bot = min(max(p[1] for p in pts), self.h - 1)
        edges = list(zip(pts, pts[1:] + pts[:1]))
        for y in range(top, bot + 1):
            hits = []
            for (ax, ay), (bx, by) in edges:
                if ay == by:
                    continue
                if (ay <= y < by) or (by <= y < ay):
                    hits.append(ax + (y - ay) * (bx - ax) / (by - ay))
            hits.sort()
            for k in range(0, len(hits) - 1, 2):
                for x in range(int(hits[k]), int(hits[k + 1]) + 1):
                    self.dot(x, y, rgb)

    def glyph(self, x, y, ch, s, rgb, bold=False):
        rows = GLYPHS.get(ch, GLYPHS["?"])
        for r, line in enumerate(rows):
            for c, mark in enumerate(line):
                if mark != "#":
                    continue
                self.box(x + c * s, y + r * s,
                         x + (c + 1) * s, y + (r + 1) * s, rgb)
                if bold:
                    self.box(x + c * s + 1, y + r * s,
                             x + (c + 1) * s + 1, y + (r + 1) * s, rgb)

    def text(self, x, y, s, scale, rgb, bold=False):
        for ch in s:
            self.glyph(x, y, ch, scale, rgb, bold)
            x += 6 * scale
        return x

    def text_len(self, s, scale):
        return len(s) * 6 * scale

    def fold(self, s, scale, width):
        """Greedy wrap: most words per line that still fits."""
        per = max(1, width // (6 * scale))
        lines, cur = [], ""
        for word in s.split(" "):
            nxt = (cur + " " + word).strip()
            if len(nxt) <= per:
                cur = nxt
                continue
            if cur:
                lines.append(cur)
            while len(word) > per:
                lines.append(word[:per])
                word = word[per:]
            cur = word
        if cur:
            lines.append(cur)
        return lines

    def scanlines(self):
        step = self.w * 3
        return [bytes(self.buf[y * step:(y + 1) * step])
                for y in range(self.h)]

# ------------------------------------------------------------------ icons
def draw_art(pg, cx, cy, kind, rgb):
    """Small pictogram for a lead panel, drawn in the lead's colour."""
    if kind == "ship":
        # Hull, mast and sail as one filled silhouette.
        pg.fill_poly([(cx - 11, cy + 2), (cx + 11, cy + 2),
                      (cx + 7, cy + 10), (cx - 7, cy + 10)], rgb)
        pg.vbar(cx, cy - 10, cy + 2, rgb, 2)
        pg.fill_poly([(cx + 1, cy - 10), (cx + 1, cy - 1),
                      (cx + 9, cy - 1)], rgb)
        return
    if kind == "satellite":
        # Raised square body with a thin solar panel on each side, plus
        # a short diagonal antenna so the mark reads as a satellite
        # instead of a dashed line at small size.
        pg.box(cx - 4, cy - 3, cx + 4, cy + 5, rgb)
        pg.box(cx - 14, cy - 1, cx - 6, cy + 1, rgb)
        pg.box(cx + 6, cy - 1, cx + 14, cy + 1, rgb)
        pg.fill_poly([(cx + 3, cy - 3), (cx + 5, cy - 3),
                      (cx + 10, cy - 10), (cx + 8, cy - 10)], rgb)
        pg.box(cx + 8, cy - 12, cx + 11, cy - 9, rgb)
        return
    # "drop": a falling droplet inside a ring.
    pg.disc(cx, cy, 14, rgb, thick=2)
    pg.fill_poly([(cx, cy - 10), (cx + 6, cy),
                  (cx + 6, cy + 4), (cx - 6, cy + 4),
                  (cx - 6, cy)], rgb)
    pg.disc(cx, cy + 3, 6, rgb, solid=True)


# ------------------------------------------------------------------ news
# The three lead stories, then the seven regional sections. Every item
# is an event of, or first reported on, Tuesday 24 November 2026;
# NEWS.md documents each one with its source. Briefs stay under
# 76 characters so each fits on one line at scale 2.
TOP = [
    dict(tag="NATO", rgb=(31, 78, 121),
         head="NATO vows to defend space",
         cap="NATO will defend space from any threat.",
         art="satellite"),
    dict(tag="LIBYA", rgb=(179, 32, 44),
         head="Ukraine sinks Russian warship",
         cap="Seven sea drones sank the corvette Merkuriy.",
         art="ship"),
    dict(tag="HORMUZ", rgb=(176, 92, 12),
         head="Tankers hit by sea mines",
         cap="Tankers burn in Hormuz; UK logs record attacks.",
         art="drop"),
]

SECTIONS = [
    dict(name="EUROPE", rgb=(31, 78, 121), items=[
        "Medvedev warns of \"preventive nuclear attack\" as NATO \"crossed a line\"",
        "Russia threatens Estonia with \"open war\" over border closure plan",
        "Russian drone briefly enters Polish airspace in strike on Ukraine",
        "EU proposes 22nd sanctions package, including a sports ban",
        "Spain's top court amnesties Catalan leader Carles Puigdemont",
    ]),
    dict(name="UKRAINE WAR", rgb=(179, 32, 44), items=[
        "Germany first to gain access to Ukraine's Delta battle system",
        "US delays transfer of about 60 Patriot interceptors to Kyiv",
        "Russian strikes on Kharkiv region injure 21, damage homes",
        "Repeated drone strikes on Vinnytsia injure four, hit power grid",
        "Ukraine says it hit 16 Russian Iskander and S-400 launchers",
    ]),
    dict(name="MIDDLE EAST", rgb=(176, 92, 12), items=[
        "UK logs record Iranian attacks in Strait of Hormuz",
        "Israeli strikes kill at least six in Gaza, medics say",
        "Houthis say Saudi strike kills 17 in Yemen's Hodeida",
        "Strikes on Yemen buses and trucks kill about 25 in Lahj",
        "Iraq orders takeover of oilfields in Kurdish-held areas",
    ]),
    dict(name="ASIA-PACIFIC", rgb=(46, 125, 50), items=[
        "Suspect North Korean jet enters South Korean airspace",
        "China names first foreign astronaut for its space station",
        "ICJ rules Myanmar committed genocide against Rohingya",
        "India pledges major aid package as Nepal PM visits Delhi",
        "Indonesia factory fire kills 26, dozens still missing",
        "Magnitude 5.6 quake hits Nepal, felt across N. India",
        "Ousted PM Hasina plans return to Bangladesh on Dec 16",
    ]),
    dict(name="AMERICAS", rgb=(106, 27, 154), items=[
        "Car bomb at governor's office in Colombia injures dozens",
        "Mexico to try \"Chapo Isidro\" despite US extradition plea",
        "Trump vows faster federal executions in Newsom death-row clash",
        "Two US states sue SpaceX over Grok child-abuse images",
        "US loses measles-free status after more than 25 years",
    ]),
    dict(name="AFRICA", rgb=(0, 121, 107), items=[
        "Fighting in DR Congo traps Ebola response teams - WHO",
        "DR Congo military aircraft missing; rebels claim shootdown",
        "Somalia and Uganda step up operations against al-Shabaab",
    ]),
    dict(name="TECH & WORLD", rgb=(69, 90, 100), items=[
        "Nvidia reinstates Huang as CEO; shares jump 31% in a day",
        "Sanofi agrees $41bn takeover of US biotech Insmed",
        "Arm extends CEO Rene Haas' tenure to 2033",
        "S&P 500 jumps 4.7% as tech rally lifts global stocks",
        "COP31 fallout: first climate summit since 2009 ends in no deal",
        "UN: 47,000 women killed by partners or family in 2025",
        "Astronomers find most distant glowing black hole yet",
    ]),
]

TOTAL = len(TOP) + sum(len(s["items"]) for s in SECTIONS)

# ---------------------------------------------------------------- layout
MARGIN = 28
MASTHEAD_H = 126
LEAD_TOP = 134
LEAD_H = 126
LEAD_GAP = 16
BRIEF_STEP = 16
SECTION_GAP = 2
HEADER_H = 18
FOOTER_Y = 1003


def draw_masthead(pg):
    pg.box(0, 0, PAGE_W, MASTHEAD_H, NAVY)
    kick = "T H E   W O R L D   I N   O N E   D A Y"
    pg.text((PAGE_W - pg.text_len(kick, 3)) // 2, 18, kick, 3, GOLD)
    day = "24 NOVEMBER 2026"
    pg.text((PAGE_W - pg.text_len(day, 6)) // 2, 50, day, 6, WHITE)
    pg.hbar(PAGE_W // 2 - 180, PAGE_W // 2 + 180, 100, GOLD, 2)
    sub = ("TUESDAY  •  %d STORIES  •  7 REGIONS  •  "
           "ALL DATED 24 NOVEMBER 2026" % TOTAL)
    pg.text((PAGE_W - pg.text_len(sub, 2)) // 2, 110, sub, 2,
            (200, 205, 215))


def draw_top_stories(pg):
    span = PAGE_W - 2 * MARGIN - 2 * LEAD_GAP
    w = span // 3
    for i, lead in enumerate(TOP):
        x = MARGIN + i * (w + LEAD_GAP)
        y = LEAD_TOP
        pg.box(x, y, x + w, y + LEAD_H, WHITE)
        pg.box(x, y, x + w, y + 5, lead["rgb"])
        pg.box(x, y, x + w, y + 1, EDGE)
        pg.box(x, y + LEAD_H - 1, x + w, y + LEAD_H, EDGE)
        pg.box(x, y, x + 1, y + LEAD_H, EDGE)
        pg.box(x + w - 1, y, x + w, y + LEAD_H, EDGE)
        pg.text(x + 16, y + 13, lead["tag"], 2, lead["rgb"])
        draw_art(pg, x + w - 30, y + 24, lead["art"], lead["rgb"])
        lines = pg.fold(lead["head"], 3, w - 32)
        assert len(lines) <= 2, lines
        ty = y + 34
        for line in lines:
            pg.text(x + 16, ty, line, 3, INK, bold=True)
            ty += 25
        caps = pg.fold(lead["cap"], 2, w - 32)
        assert len(caps) <= 2, caps
        ty = y + 88
        for line in caps:
            pg.text(x + 16, ty, line, 2, MUTED)
            ty += 17


def draw_sections(pg):
    y = LEAD_TOP + LEAD_H + 6
    for sec in SECTIONS:
        pg.box(MARGIN, y, PAGE_W - MARGIN, y + HEADER_H, sec["rgb"])
        head = "%s  •  %d STORIES" % (sec["name"], len(sec["items"]))
        pg.text(MARGIN + 10, y + 2, head, 2, WHITE)
        y += HEADER_H
        for brief in sec["items"]:
            assert len(brief) <= 76, brief
            pg.box(MARGIN + 4, y + 4, MARGIN + 12, y + 12, sec["rgb"])
            pg.text(MARGIN + 20, y + 1, brief, 2, INK, bold=True)
            y += BRIEF_STEP
        y += SECTION_GAP
    return y


def draw_footer(pg):
    # A thin gold rule lifts the footer off the last region section,
    # which otherwise ends only a few pixels above the source line.
    pg.hbar(MARGIN, PAGE_W - MARGIN, 1000, GOLD, 1)
    pg.text(MARGIN, FOOTER_Y,
            "Sources: Reuters, BBC, AP, Al Jazeera, SCMP, Xinhua",
            2, GREY)
    tail = "24 NOV 2026"
    pg.text(PAGE_W - MARGIN - pg.text_len(tail, 2), FOOTER_Y,
            tail, 2, GREY)


def compose():
    pg = Page(PAGE_W, PAGE_H, PAPER)
    draw_masthead(pg)
    draw_top_stories(pg)
    end = draw_sections(pg)
    assert end <= 1000, end
    draw_footer(pg)
    return pg


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    save_png(os.path.join(out_dir, "entry.png"), compose())


if __name__ == "__main__":
    main()
