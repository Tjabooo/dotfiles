#!/usr/bin/env python3
"""Build the "magi-neon" GRUB theme (midnight neon, Unit-01 activation board) into ./magi-neon.
Laptop sibling of the desktop's ember "magi" theme (Tjabooo/dotfiles-desktop).

    python3 ~/.local/share/neon/grub-theme/build.py [--preview]

Left: the EVA unit-01 activation board (sync-ratio ring, ENTRY PLUG / LCL / A10 / UMBILICAL
status units, harmonics). Right: the menu card. intro.py plays the activation that ends on this
picture, and ../plymouth-theme continues from it.

Drawn on a 2560x1600 (16:10) design canvas, the desktop's 2560x1440 layout shifted down by OY,
then scaled exactly 1.125x to the Zenbook's native 2880x1800. theme.txt coordinates and font
sizes get the same 1.125 factor, so everything lines up.

scene(S) draws any state of the board (intro.py and the Plymouth theme reuse it);
background() is scene(FINAL). --preview also writes preview.png: a mockup of the menu on top.

Install: sudo ./install.sh (copies ./magi-neon to /boot/grub/themes, adds the intro).
Theme files are not signature-checked (GRUB is sbctl-signed, no shim), so this can't affect
Secure Boot; a broken theme only drops GRUB to its plain text menu.
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 2560, 1600            # design canvas (16:10)
LW, LH = 2560, 1440          # the desktop layout, drawn on a layer...
OY = 80                      # ...placed this far down
FW, FH = 2880, 1800          # final size = native panel
S = FW / W                   # 1.125, uniform
HERE = Path(__file__).resolve().parent
OUT = HERE / "magi-neon"

# midnight neon palette (same as hyprland.lua / waybar / dunst) + unit-01 green
BG, PANEL, LINE = "#0f0f1e", "#1a1a2f", "#2a2a45"
FG, DIM = "#e0e0f0", "#6c6c8a"
VIOLET, PINK, CYAN, RED = "#9b5de5", "#f15bb5", "#00c6ff", "#ff5252"
GREEN = "#9ef01a"            # EVA-01's fluorescent green
SEL, ITEM = "#251b40", "#a0a0c8"
TRACK = "#1d1d36"

TTF = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-{}.ttf"
CJK = "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"

# layout (pixels on the 2560x1440 layer; theme.txt gets native pixels)
CARD = (1380, 380, 2440, 960)          # menu card
MENU = (1420, 548, 2400, 860)          # GRUB boot_menu area inside the card
ITEM_H, ITEM_GAP = 84, 14
TIMEOUT_LABEL_Y, BAR_Y = 858, 930      # countdown text + bar (bar top = BAR_Y - 25)
HINTS_Y = 1010

RC = (470, 665)                        # sync ring centre
R_OUT = 262
CHIP_X0, CHIP_W, CHIP_H = 840, 380, 100
CHIP_Y = (425, 553, 681, 809)
CHIPS = [("ENTRY PLUG", "挿入 · INSERTED"), ("LCL", "注水 · FILLED"),
         ("A10 NERVE", "神経接続 · CONNECTED"), ("UMBILICAL", "外部電源 · EXTERNAL")]
HARM = (120, 965, 1220, 1065)          # harmonics strip
VERDICT_Y = 1118
SYNC = 41.3                            # Shinji's first sync ratio


def font(weight, size):
    return ImageFont.truetype(TTF.format(weight), size)


def cjk(size):
    return ImageFont.truetype(CJK, size)


def rgba(hexcol, a=255):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def chamfer(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1, y0), (x1, y1 - c), (x1 - c, y1), (x0, y1), (x0, y0 + c)]


def text(d, xy, s, f, fill, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def mixed(d, xy, parts, anchor="ls"):
    """Draw [(str, font, colour), ...] left to right from xy (anchor l*); returns the end x."""
    x, y = xy
    for s, f, col in parts:
        text(d, (x, y), s, f, col, anchor)
        x += d.textlength(s, font=f)
    return x


def faded(layer, k):
    if k >= 1:
        return layer
    a = np.asarray(layer).copy()
    a[..., 3] = (a[..., 3].astype(np.float32) * max(k, 0)).round().astype(np.uint8)
    return Image.fromarray(a, "RGBA")


# ── scene state ──────────────────────────────────────────────────────────────
FINAL = dict(glow=1, title=True, htext="final", rule=1, footer=True, brackets=1, card="final", hints=True,
             ring=1, sync=SYNC, core=2, links=4, chips=[3, 3, 3, 3], harm=1, converge=1,
             verdict=("4 / 4", "  SYSTEMS NORMAL  ·  LAUNCH AUTHORIZED"), log=[], online=4)


def base_layers():
    """Glow and hex grid on the full design canvas (separate, so the intro can fade them)."""
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for (cx, cy, r, a, col) in ((RC[0] + 40, RC[1] + OY, 620, 48, VIOLET), (1910, 670 + OY, 520, 26, PINK)):
        gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgba(col, a))
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    r = 34
    hw, hh = math.sqrt(3) * r, 1.5 * r
    for row in range(int(H / hh) + 2):
        for col in range(int(1300 / hw) + 2):
            cx = col * hw + (hw / 2 if row % 2 else 0)
            cy = row * hh
            pts = [(cx + r * math.cos(math.radians(60 * k + 30)), cy + r * math.sin(math.radians(60 * k + 30)))
                   for k in range(6)]
            fade = max(0, 1 - abs(cx - 660) / 900) * max(0, 1 - abs(cy - 720 - OY) / 800)
            if fade > 0.05:
                gd.polygon(pts, outline=rgba(VIOLET, int(26 * fade)))
    scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scan)
    for y in range(0, H, 4):
        sd.line((0, y, W, y), fill=(0, 0, 0, 34))
    return glow, grid, scan


_LAYERS = None


def layers():
    global _LAYERS
    if _LAYERS is None:
        _LAYERS = base_layers()
    return _LAYERS


def scene(st, native=True):
    """Any state of the GRUB picture. native=True -> 2880x1800 RGB, else the 2560x1600 design canvas."""
    S_ = dict(FINAL)
    S_.update(st)
    glow, grid, scan = layers()
    img = Image.new("RGBA", (W, H), rgba(BG))
    if S_["glow"] > 0:
        img.alpha_composite(faded(glow, S_["glow"]))
        img.alpha_composite(faded(grid, S_["glow"]))
    lay = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    header(d, S_)
    board(lay, d, S_)
    card(lay, d, S_)
    if S_["hints"]:
        hints(d)
    footer(d, S_)
    img.alpha_composite(lay, (0, OY))
    d = ImageDraw.Draw(img)
    if S_["brackets"] > 0:
        n = round(70 * S_["brackets"])
        for (x, y, sx, sy) in ((40, 40, 1, 1), (W - 40, 40, -1, 1), (40, H - 40, 1, -1), (W - 40, H - 40, -1, -1)):
            d.line((x, y, x + n * sx, y), fill=VIOLET, width=3)
            d.line((x, y, x, y + n * sy), fill=GREEN, width=3)
    img.alpha_composite(scan)
    img = img.convert("RGB")
    return img.resize((FW, FH), Image.LANCZOS) if native else img


def header(d, S_):
    if S_["title"]:
        text(d, (120, 112), "UNIT-01", font("ExtraBold", 64), VIOLET, "ls")
    if S_["htext"]:
        f, fc = font("Regular", 22), cjk(22)
        if S_["htext"] == "final":
            mixed(d, (440, 104), [("EVANGELION  ·  ", f, DIM), ("初号機", fc, DIM), ("  ·  BOOT CONTROL", f, DIM)])
        else:
            mixed(d, (440, 104), [("EVANGELION  ·  ", f, DIM), ("起動", fc, DIM), ("  ·  ACTIVATION", f, DIM)])
        text(d, (2440, 92), "NEON // unit-01", font("Bold", 24), FG, "rs")
        text(d, (2440, 124), "SECURE BOOT · SBCTL CHAIN VERIFIED", font("Regular", 18), DIM, "rs")
    if S_["rule"] > 0:
        d.line((120, 150, 120 + round(2320 * S_["rule"]), 150), fill=LINE, width=2)
        k = min(1, S_["rule"] * 2)
        d.line((120, 150, 120 + round(180 * k), 150), fill=VIOLET, width=4)
        if k > 0.5:
            d.line((300, 150, 300 + round(160 * (k - 0.5) * 2), 150), fill=GREEN, width=4)


def footer(d, S_):
    if S_["footer"]:
        d.line((120, 1320, 2440, 1320), fill=LINE, width=2)
        text(d, (120, 1362), "ZENBOOK S 16  ·  RYZEN AI 9 HX 370  ·  RADEON 890M  ·  linux", font("Regular", 18), DIM, "ls")
        f = font("Regular", 18)
        parts = [("NERV  ·  ", f), ("初号機", cjk(18)), ("  ·  TEST TYPE", f)]
        mixed(d, (2440 - sum(d.textlength(s, font=ff) for s, ff in parts), 1362), [(s, ff, DIM) for s, ff in parts])


# ── the activation board ─────────────────────────────────────────────────────
SS = 3


def ring_sprite(S_):
    """Sync ring (supersampled): track, ticks, sync arc, dashed inner ring. Returns (img, x, y)."""
    pad = 34
    R = R_OUT + pad
    size = 2 * R
    im = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = R * SS
    k = S_["ring"]

    def circ(r, **kw):
        d.ellipse((c - r * SS, c - r * SS, c + r * SS, c + r * SS), **kw)

    if k <= 0:
        return None
    # outer rim + ticks, revealed clockwise from the top as k grows
    sweep = 360 * min(1, k)
    d.arc((c - R_OUT * SS, c - R_OUT * SS, c + R_OUT * SS, c + R_OUT * SS), -90, -90 + sweep,
          fill=rgba(LINE), width=2 * SS)
    for i in range(120):
        a = i * 3
        if a > sweep:
            break
        major = i % 10 == 0
        r0, r1 = (220, 250) if major else (234, 246)
        ang = math.radians(a - 90)
        col = rgba(DIM) if major else rgba(LINE)
        d.line((c + r0 * SS * math.cos(ang), c + r0 * SS * math.sin(ang),
                c + r1 * SS * math.cos(ang), c + r1 * SS * math.sin(ang)), fill=col, width=(3 if major else 2) * SS)
    if k >= 1:
        # track + sync arc
        rr = 196
        box = (c - rr * SS, c - rr * SS, c + rr * SS, c + rr * SS)
        d.arc(box, 0, 360, fill=rgba(TRACK), width=18 * SS)
        frac = S_["sync"] / 100
        if frac > 0:
            d.arc(box, -90, -90 + 360 * frac, fill=rgba(VIOLET), width=18 * SS)
            ang = math.radians(-90 + 360 * frac)
            ex, ey = c + (rr - 9) * SS * math.cos(ang), c + (rr - 9) * SS * math.sin(ang)
            d.ellipse((ex - 12 * SS, ey - 12 * SS, ex + 12 * SS, ey + 12 * SS), fill=rgba(GREEN))
        # dashed inner ring
        for i in range(48):
            a0 = i * 7.5
            d.arc((c - 160 * SS, c - 160 * SS, c + 160 * SS, c + 160 * SS), a0, a0 + 3.5, fill=rgba(LINE), width=2 * SS)
    im = im.resize((size, size), Image.LANCZOS)
    return im, RC[0] - R, RC[1] - R


def board(img, d, S_):
    # connectors ring -> status units
    nl = S_["links"]
    for i, cy in enumerate(CHIP_Y):
        p = 1 if nl > i else 0
        if p:
            ty = cy + CHIP_H / 2
            ang = math.atan2(ty - RC[1], CHIP_X0 - RC[0])
            sx, sy = RC[0] + (R_OUT + 4) * math.cos(ang), RC[1] + (R_OUT + 4) * math.sin(ang)
            d.line((sx, sy, CHIP_X0 - 30, ty, CHIP_X0, ty), fill=rgba(CYAN, 140), width=2)
            d.rectangle((sx - 3, sy - 3, sx + 3, sy + 3), fill=rgba(CYAN, 200))
    r = ring_sprite(S_)
    if r:
        img.alpha_composite(r[0], (r[1], r[2]))
    core(d, S_)
    for i, stt in enumerate(S_["chips"]):
        if stt:
            chip(img, d, i, stt)
    harmonics(img, d, S_)
    if S_["verdict"]:
        f_big, f_sm = font("ExtraBold", 26), font("Regular", 20)
        left_s, right_s = S_["verdict"]
        wl, wr = d.textlength(left_s, font=f_big), d.textlength(right_s, font=f_sm)
        x = (HARM[0] + HARM[2]) / 2 - (wl + wr) / 2
        text(d, (x, VERDICT_Y), left_s, f_big, GREEN, "ls")
        text(d, (x + wl, VERDICT_Y), right_s, f_sm, DIM, "ls")


def core(d, S_):
    cx, cy = RC
    if S_["core"] >= 1:
        text(d, (cx, cy - 40), "初号機", cjk(78), FG if S_["core"] == 2 else LINE, "mm")
        text(d, (cx, cy + 26), "EVANGELION  UNIT-01", font("Bold", 16), DIM, "mm")
    if S_["core"] == 2 or S_["sync"] > 0:
        d.line((cx - 92, cy + 48, cx + 92, cy + 48), fill=LINE, width=2)
        text(d, (cx, cy + 74), "SYNC RATIO", font("Bold", 15), DIM, "mm")
        s = f"{S_['sync']:.1f}"
        f = font("ExtraBold", 46)
        w = d.textlength(s, font=f) + d.textlength("%", font=font("Bold", 26)) + 4
        x = cx - w / 2
        text(d, (x, cy + 132), s, f, GREEN if S_["sync"] >= SYNC else VIOLET, "ls")
        text(d, (x + d.textlength(s, font=f) + 4, cy + 132), "%", font("Bold", 26), DIM, "ls")


def chip(img, d, i, stt):
    """stt 1 = standby (dim), 2 = flash (solid green, 起動 knocked out), 3 = final (正常 stamp)."""
    name, sub = CHIPS[i]
    x0, y0 = CHIP_X0, CHIP_Y[i]
    x1, y1 = x0 + CHIP_W, y0 + CHIP_H
    pts = chamfer(x0, y0, x1, y1, 22)
    fill = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(fill).polygon(pts, fill=rgba(GREEN) if stt == 2 else rgba(PANEL, 235))
    img.alpha_composite(fill)
    fn, fs, fst = font("ExtraBold", 26), cjk(17), cjk(32)
    sx0, sy0, sx1, sy1 = x1 - 132, y0 + 18, x1 - 22, y1 - 18
    if stt == 2:
        d.polygon(pts, outline=rgba("#d4ff8a"), width=3)
        text(d, (x0 + 24, y0 + 44), name, fn, BG, "ls")
        text(d, (x0 + 24, y0 + 78), sub, fs, BG, "ls")
        text(d, ((sx0 + sx1) / 2, (sy0 + sy1) / 2), "起動", fst, BG, "mm")
    elif stt == 1:
        d.polygon(pts, outline=LINE, width=3)
        text(d, (x0 + 24, y0 + 44), name, fn, DIM, "ls")
        text(d, (x0 + 24, y0 + 78), sub, fs, LINE, "ls")
        d.rectangle((sx0, sy0, sx1, sy1), outline=LINE, width=2)
        text(d, ((sx0 + sx1) / 2, (sy0 + sy1) / 2), "STANDBY", font("Bold", 15), DIM, "mm")
    else:
        d.polygon(pts, outline=VIOLET, width=3)
        text(d, (x0 + 24, y0 + 44), name, fn, FG, "ls")
        text(d, (x0 + 24, y0 + 78), sub, fs, DIM, "ls")
        d.rectangle((sx0, sy0, sx1, sy1), outline=GREEN, width=3)
        d.rectangle((sx0 + 6, sy0 + 6, sx1 - 6, sy1 - 6), outline=rgba(GREEN, 100), width=1)
        text(d, ((sx0 + sx1) / 2, (sy0 + sy1) / 2 - 2), "正常", fst, GREEN, "mm")


def wave_y(x, j, conv):
    """Harmonics trace j at x: three traces that drift apart (conv 0) or lock together (conv 1)."""
    base = math.sin(x / 38.0) * 0.62 + math.sin(x / 13.0 + 1.1) * 0.22 + math.sin(x / 71.0) * 0.16
    wild = [math.sin(x / 23.0 + 2.0) * 0.8 + math.sin(x / 9.0) * 0.3,
            math.sin(x / 51.0 + 4.0) * 0.9 + math.sin(x / 17.0 + 0.5) * 0.25,
            math.sin(x / 31.0 + 1.0) * 0.7 + math.sin(x / 7.0 + 3.0) * 0.3][j]
    off = (j - 1) * 0.07 * conv
    return base * conv + wild * (1 - conv) + off


def harmonics(img, d, S_):
    h = S_["harm"]
    if h <= 0:
        return
    x0, y0, x1, y1 = HARM
    fill = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(fill).rectangle(HARM, fill=rgba(PANEL, 200))
    img.alpha_composite(fill)
    d.rectangle(HARM, outline=LINE, width=2)
    d.rectangle((x0, y0, x0 + 4, y1), fill=VIOLET)
    text(d, (x0 + 28, y0 + 42), "HARMONICS", font("ExtraBold", 22), FG, "ls")
    text(d, (x0 + 28, y0 + 74), "ハーモニクス", cjk(17), DIM, "ls")
    conv = S_["converge"]
    ok = conv >= 1
    text(d, (x1 - 24, y0 + 42), "全て正常値" if ok else "調整中", cjk(20), GREEN if ok else DIM, "rs")
    text(d, (x1 - 24, y0 + 72), "ALL NORMAL" if ok else "CALIBRATING", font("Bold", 15), GREEN if ok else DIM, "rs")
    gx0, gx1, gy = 330, 1000, (y0 + y1) / 2
    # baseline grid
    for gx in range(gx0, gx1 + 1, 67):
        d.line((gx, y0 + 16, gx, y1 - 16), fill=rgba(LINE, 160), width=1)
    d.line((gx0, gy, gx1, gy), fill=rgba(LINE, 200), width=1)
    span = gx0 + (gx1 - gx0) * min(1, h)
    sp = Image.new("RGBA", ((gx1 - gx0 + 20) * SS, (y1 - y0) * SS), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sp)
    amp = 28
    for j, col in enumerate((PINK, CYAN, GREEN)):
        pts = []
        x = gx0
        while x <= span:
            pts.append(((x - gx0 + 10) * SS, (gy - y0 + wave_y(x, j, conv) * amp) * SS))
            x += 2
        if len(pts) > 1:
            sd.line(pts, fill=rgba(col, 230), width=3 * SS, joint="curve")
    sp = sp.resize((gx1 - gx0 + 20, y1 - y0), Image.LANCZOS)
    img.alpha_composite(sp, (gx0 - 10, y0))


# ── menu card + hints ────────────────────────────────────────────────────────
def card(img, d, S_):
    st = S_["card"]
    if st == "none":
        return
    x0, y0, x1, y1 = CARD
    fill = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    ImageDraw.Draw(fill).rectangle(CARD, fill=rgba(BG, 240))
    img.alpha_composite(fill)
    d.rectangle(CARD, outline=LINE, width=2)
    if st == "frame":
        return
    d.rectangle((x0, y0, x1, y0 + 5), fill=VIOLET)
    if st == "final":
        text(d, (x0 + 40, y0 + 70), "SELECT SYSTEM", font("ExtraBold", 34), VIOLET, "ls")
        mixed(d, (x0 + 40, y0 + 108), [("発進", cjk(20), DIM), (" · LAUNCH TARGET REQUIRED", font("Regular", 20), DIM)])
        text(d, (x1 - 40, y0 + 70), "03 TARGETS", font("Bold", 20), PINK, "rs")
        d.line((x0 + 40, y0 + 136, x1 - 40, y0 + 136), fill=LINE, width=2)
        return
    done = st == "done"
    mixed(d, (x0 + 40, y0 + 70), [("起動 ", cjk(34), VIOLET), ("ACTIVATION", font("ExtraBold", 34), VIOLET)])
    sub = "CODE : 001 · ACTIVATION COMPLETE" if done else "CODE : 101 · EVA-01 ACTIVATION SEQUENCE ..."
    text(d, (x0 + 40, y0 + 108), sub, font("Regular", 20), GREEN if done else DIM, "ls")
    text(d, (x1 - 40, y0 + 70), f"0{S_['online']} / 04", font("Bold", 20), PINK, "rs")
    d.line((x0 + 40, y0 + 136, x1 - 40, y0 + 136), fill=LINE, width=2)
    mx0, my0, mx1, _ = MENU
    f = font("Regular", 26)
    for i, row in enumerate(S_["log"]):
        label, status = row[0], row[1]
        y = my0 + 30 + i * 60
        if isinstance(label, tuple):          # (cjk, latin)
            xe = mixed(d, (mx0 + 22, y), [(label[0] + " ", cjk(24), ITEM), (label[1], f, ITEM)], "lm")
        else:
            text(d, (mx0 + 22, y), label, f, ITEM, "lm")
            xe = mx0 + 22 + d.textlength(label, font=f)
        x = xe + 22
        while x < mx1 - 220:
            d.rectangle((x, y + 8, x + 3, y + 11), fill=LINE)
            x += 16
        if status:
            text(d, (mx1 - 22, y), status, font("ExtraBold", 26), DIM if status in ("LOADING", "...") else GREEN, "rm")


def hints(d):
    chips = [("↑ ↓", "select"), ("ENTER", "boot"), ("E", "edit"), ("C", "console")]
    fk, fl = font("ExtraBold", 20), font("Regular", 20)
    x = CARD[0] + 40
    for key, label in chips:
        kw = d.textlength(key, font=fk) + 24
        d.rectangle((x, HINTS_Y - 18, x + kw, HINTS_Y + 18), fill=VIOLET)
        text(d, (x + kw / 2, HINTS_Y), key, fk, BG, "mm")
        x += kw + 12
        text(d, (x, HINTS_Y), label, fl, DIM, "lm")
        x += d.textlength(label, font=fl) + 40


def background():
    return scene({})


# ── selection pixmaps (9-slice) + icons ──────────────────────────────────────
def pixmaps():
    sel, bar = rgba(SEL), rgba(VIOLET)
    def save(name, w, h, cols):
        im = Image.new("RGBA", (w, h))
        for x, col in enumerate(cols):
            for y in range(h):
                im.putpixel((x, y), col)
        im.save(OUT / f"select_{name}.png")
    left = [bar] * 6 + [sel] * 10     # violet accent bar + inner padding
    save("w", 16, 1, left)
    save("nw", 16, 2, left)
    save("sw", 16, 2, left)
    save("n", 1, 2, [sel])
    save("s", 1, 2, [sel])
    save("c", 1, 1, [sel])
    save("e", 2, 1, [sel] * 2)
    save("ne", 2, 2, [sel] * 2)
    save("se", 2, 2, [sel] * 2)


def icons():
    (OUT / "icons").mkdir(exist_ok=True)
    f = font("Regular", 50)
    for cls, cp in (("arch", 0xF303), ("windows", 0xF17A), ("efi", 0xF061A)):
        im = Image.new("RGBA", (62, 62), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.text((31, 31), chr(cp), font=f, fill=FG, anchor="mm")
        im.save(OUT / "icons" / f"{cls}.png")


# ── fonts + theme.txt ────────────────────────────────────────────────────────
RANGES = "0x20-0x7E,0xA0-0x17F,0x2010-0x2027,0x2190-0x21FF,0x2500-0x259F,0x25A0-0x25FF"
FONTS = [("Regular", 25, False), ("Regular", 34, False), ("ExtraBold", 34, True)]


def fonts():
    for weight, size, bold in FONTS:
        out = OUT / f"magi-{'bold-' if bold else ''}{size}.pf2"
        if out.exists():
            continue
        cmd = ["grub-mkfont", "-n", "MAGI", "-s", str(size), "-r", RANGES, "-o", str(out)]
        if bold:
            cmd.append("-b")
        subprocess.run(cmd + [TTF.format(weight)], check=True)


def X(v):
    # GRUB only accepts whole numbers here ("55%", "1420", "50%+10"); "55.469%" is a
    # parse error that kills the whole theme. Design px → native px.
    return str(int(round(v * S)))


def Y(v):
    return str(int(round((v + OY) * S)))


def grub_px(p, n, total):
    # what gfxmenu computes for "p%+n": prop = round(p * 65536 / 100), then (total * prop) / 65536
    prop = (p * 65536 * 2 + 100) // 200
    return n + (total * prop) // 65536


def geometry():
    """Native-pixel (x, y, w, h) of the menu, countdown label and bar, as theme.txt places them."""
    mx0, my0, mx1, my1 = MENU
    cx0, _, cx1, _ = CARD
    return {
        "menu": (int(X(mx0)), int(Y(my0)), int(X(mx1 - mx0)), int(X(my1 - my0))),
        "label": (int(X(cx0 + 40)), int(Y(TIMEOUT_LABEL_Y)), int(X(cx1 - cx0 - 80)), 34),
        "bar": (int(X(cx0 + 40)), int(Y(BAR_Y - 25)), int(X(cx1 - cx0 - 80)), 7),
        "item_h": int(X(ITEM_H)), "item_gap": int(X(ITEM_GAP)),
    }


def theme():
    G = geometry()
    t = f'''# GRUB theme "magi-neon" (midnight neon, unit-01). Generated by ~/.local/share/neon/grub-theme/build.py;
# edit that, not this file. Layout is drawn for 2880x1800 (GRUB_GFXMODE).
title-text: ""
desktop-image: "background.png"
desktop-image-scale-method: "stretch"
desktop-color: "{BG}"
terminal-font: "MAGI Regular 25"
terminal-left: "6%"
terminal-top: "14%"
terminal-width: "88%"
terminal-height: "76%"
terminal-border: "0"

+ boot_menu {{
    left = {G["menu"][0]}
    top = {G["menu"][1]}
    width = {G["menu"][2]}
    height = {G["menu"][3]}
    item_font = "MAGI Regular 34"
    selected_item_font = "MAGI Bold 34"
    item_color = "{ITEM}"
    selected_item_color = "{VIOLET}"
    item_height = {G["item_h"]}
    item_padding = 25
    item_spacing = {G["item_gap"]}
    icon_width = 50
    icon_height = 50
    item_icon_space = 29
    selected_item_pixmap_style = "select_*.png"
    scrollbar = false
}}

+ label {{
    id = "__timeout__"
    left = {G["label"][0]}
    top = {G["label"][1]}
    width = {G["label"][2]}
    height = 34
    align = "left"
    text = "AUTO-SELECT IN %d s"
    font = "MAGI Regular 25"
    color = "{DIM}"
}}

+ progress_bar {{
    id = "__timeout__"
    left = {G["bar"][0]}
    top = {G["bar"][1]}
    width = {G["bar"][2]}
    height = 7
    show_text = false
    fg_color = "{VIOLET}"
    bg_color = "{LINE}"
    border_color = "{LINE}"
}}
'''
    (OUT / "theme.txt").write_text(t)


# ── preview mockup (what GRUB should roughly draw on top of the background) ──
def preview(bg):
    img = bg.convert("RGBA")
    d = ImageDraw.Draw(img)
    G = geometry()
    entries = [("arch", "Arch Linux"), ("windows", "Windows 11"), ("efi", "UEFI Firmware Settings")]
    fi, fs = font("Regular", 34), font("ExtraBold", 34)
    mx, my, mw, _ = G["menu"]
    ih = G["item_h"]
    for i, (cls, label) in enumerate(entries):
        y = my + i * (ih + G["item_gap"])
        if i == 0:
            d.rectangle((mx, y, mx + mw, y + ih), fill=SEL)
            d.rectangle((mx, y, mx + 6, y + ih), fill=VIOLET)
        ic = Image.open(OUT / "icons" / f"{cls}.png").resize((50, 50))
        img.alpha_composite(ic, (mx + 25, y + (ih - 50) // 2))
        text(d, (mx + 25 + 50 + 29, y + ih // 2), label, fs if i == 0 else fi, VIOLET if i == 0 else ITEM, "lm")
    lx, ly, lw, _ = G["label"]
    text(d, (lx, ly + 17), "AUTO-SELECT IN 3 s", font("Regular", 25), DIM, "lm")
    bx, by, bw, _ = G["bar"]
    d.rectangle((bx, by, bx + bw, by + 7), fill=LINE)
    d.rectangle((bx, by, bx + int(bw * 0.6), by + 7), fill=VIOLET)
    img.convert("RGB").save(HERE / "preview.png")


def main():
    OUT.mkdir(exist_ok=True)
    random.seed(9)
    bg = background()
    bg.save(OUT / "background.png", optimize=True)
    pixmaps()
    icons()
    fonts()
    theme()
    if "--preview" in sys.argv:
        preview(bg)
    print(f"built {OUT}")


if __name__ == "__main__":
    main()
