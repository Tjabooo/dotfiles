#!/usr/bin/env python3
"""Build the "unit01" Plymouth theme (midnight neon, EVA unit-01) into ./unit01 next to this script.
Laptop sibling of the desktop's ember "magi" splash (Tjabooo/dotfiles-desktop).

    python3 ~/.local/share/neon/plymouth-theme/build.py [--preview]

The splash continues the GRUB theme (../grub-theme): its first frame is GRUB's own
background.png. The empty menu card fills with a launch log, the activation board fades out
and a NERV emblem builds in the middle (leaf wipe, NERV, 逃げちゃダメだ typed out three
times, then "I mustn't run away."). Then a synchronization test plays (pilot typed, sync
ratio climbs to 41.3 %, LCL / A10 / HARMONICS go 正常, EVA-01 ACTIVATED), the unit-01 art
(~/.config/hypr/wallpapers/eva_lock4.jpg, the lock screen) rises behind "WELCOME, TJABO",
and it all fades to #0f0f1e, the console and Hyprland background, while tty1 autologs in
(see install.sh) and Hyprland starts.

Everything is drawn on GRUB's 2560x1600 design canvas and scaled 1.125x to the native
2880x1800 (sprite boxes snap to 8 design px = 9 native px, so the scaling is exact);
unit01.script only swaps images and sets opacity on a wall-clock timeline (Plymouth's
boot-progress time, which starts with plymouthd). Other screen sizes get the layers stretched.

The boot is held until the animation has finished: unit01-splash-hold.service sits before
plymouth-quit(-wait).service and sleeps until the splash clock has passed ANIM_END.

--preview also renders preview/ (key frames + preview.mp4) with the same timeline data.
Install with:  sudo ./install.sh   (see that file)
"""
import importlib.util
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
NAME = "unit01"
OUT = HERE / NAME
GRUB_DIR = HERE.parent / "grub-theme"
ART_SRC = Path(os.environ.get("UNIT01_ART", Path.home() / ".config/hypr/wallpapers/eva_lock4.jpg"))

_spec = importlib.util.spec_from_file_location("grub_theme_build", GRUB_DIR / "build.py")
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)

DW, DH = g.W, g.H                    # design canvas 2560x1600
W, H = g.FW, g.FH                    # native 2880x1800
K = g.S                              # 1.125
BG, PANEL, LINE, FG, DIM = g.BG, g.PANEL, g.LINE, g.FG, g.DIM
VIOLET, PINK, CYAN, GREEN = g.VIOLET, g.PINK, g.CYAN, g.GREEN
SEL, ITEM = g.SEL, g.ITEM
font, cjk, text, rgba, mixed = g.font, g.cjk, g.text, g.rgba, g.mixed
CJK_MED = "/usr/share/fonts/noto-cjk/NotoSansCJK-Medium.ttc"

# ── timeline (seconds after the splash starts) ───────────────────────────────
# The clock starts at plymouthd age max(LEAD, first frame + 0.1): frame 0 (= GRUB's background)
# is drawn as soon as the script runs, everything else loads in the background after that.
LEAD = 1.0
T_ROWS = (0.35, 0.95, 1.55)          # launch-log rows appear in the GRUB card
T_OK = (0.75, 1.35, 1.95)            # their right-hand status lands
T_BAR = (0.35, 2.25)                 # launch bar fills
T_LABEL = 2.05
T_ART_OUT = (2.6, 3.5)               # activation board + card fade out
T_GLOW_IN = (2.9, 3.9)               # centred glow + hex grid fade in
T_LEAF = (3.3, 4.8)                  # leaf wipes in from the stem up
T_WORD = 4.75                        # NERV flickers on
T_SUB = (5.35, 5.8)                  # small agency line
T_TYPE = 5.5                         # motto typing starts
T_EMBLEM_OUT = (9.0, 9.6)            # emblem fades, the sync panel takes its place
T_PANEL = 9.6
T_USER, USER_DT = 10.05, 0.11        # pilot name typed
T_SYNC = (10.85, 12.25)              # sync ratio climbs to 41.3 %
T_CHIPS = (11.45, 11.85, 12.25)      # LCL, A10, HARMONICS go 正常
T_ACT = 12.6                         # EVA-01 ACTIVATED
T_PANEL_OUT = (13.25, 13.6)
T_ARTW = (13.4, 14.5)                # unit-01 art rises
T_WELCOME, WEL_DT = 14.1, 0.055      # "WELCOME, TJABO" typed
T_WSUB = (15.0, 15.4)
T_FADE = (16.3, 17.1)                # everything fades to the console/Hyprland background
ANIM_END = 18.0                      # 0.9 s of plain background after the fade absorbs a late start
HOLD_MARGIN = 0.3
T_STATIC = 8.8                       # frame shown for shutdown/reboot splashes

CX, CY = 1280, 815                   # emblem centre (design)


# ── design -> native sprites ─────────────────────────────────────────────────
_SCAN = None


def scan_rows():
    """Per-native-row darkening of GRUB's scanlines (drawn every 4th design row, then scaled)."""
    global _SCAN
    if _SCAN is None:
        col = Image.new("RGBA", (8, DH), (0, 0, 0, 0))
        d = ImageDraw.Draw(col)
        for y in range(0, DH, 4):
            d.line((0, y, 8, y), fill=(0, 0, 0, 34))
        a = np.asarray(col.resize((9, H), Image.LANCZOS))[:, 4, 3].astype(np.float32) / 255
        _SCAN = 1 - a
    return _SCAN


def scan_native(img, y0):
    a = np.asarray(img.convert("RGBA")).astype(np.float32)
    f = scan_rows()[y0:y0 + a.shape[0]]
    a[: len(f), :, :3] *= f[:, None, None]
    return Image.fromarray(np.clip(a + 0.5, 0, 255).astype(np.uint8))


def scan_design(img, y0):
    a = np.asarray(img.convert("RGBA")).astype(np.float32)
    rows = [r for r in range(a.shape[0]) if (y0 + r) % 4 == 0]
    a[rows, :, :3] *= 1 - 34 / 255
    return Image.fromarray(np.clip(a + 0.5, 0, 255).astype(np.uint8))


class Box:
    """A transparent design-space drawing region snapped to 8 px, turned into a native sprite."""

    def __init__(self, x0, y0, x1, y1, pad=16):
        self.ox = (int(x0) - pad) // 8 * 8
        self.oy = (int(y0) - pad) // 8 * 8
        ex = -(-(int(x1) + pad) // 8) * 8
        ey = -(-(int(y1) + pad) // 8) * 8
        self.img = Image.new("RGBA", (ex - self.ox, ey - self.oy), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def p(self, x, y):
        return (x - self.ox, y - self.oy)

    def native(self, scan=True):
        im = scan_design(self.img, self.oy) if scan else self.img
        w, h = im.size
        im = im.convert("RGBa").resize((round(w * K), round(h * K)), Image.LANCZOS).convert("RGBA")
        bb = im.getbbox()
        nx, ny = round(self.ox * K), round(self.oy * K)
        if not bb:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0)), nx, ny
        return im.crop(bb), nx + bb[0], ny + bb[1]


def uncomposite(top, base):
    """RGBA layer L with L over base == top (minimal alpha), cropped. Returns (img, x, y)."""
    A = np.asarray(top.convert("RGB")).astype(np.float64)
    B = np.asarray(base.convert("RGB")).astype(np.float64)
    up = np.where(A > B, (A - B) / np.maximum(255 - B, 1e-9), 0)
    dn = np.where(A < B, (B - A) / np.maximum(B, 1e-9), 0)
    alpha = np.clip(np.max(np.maximum(up, dn), axis=2), 0, 1)
    aq = np.ceil(alpha * 255 - 1e-6) / 255
    safe = np.where(aq > 0, aq, 1)[..., None]
    C = np.clip((A - (1 - aq[..., None]) * B) / safe, 0, 255)
    out = np.dstack([C, aq * 255]).round().astype(np.uint8)
    ys, xs = np.nonzero(out[..., 3])
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return Image.fromarray(out[y0:y1, x0:x1], "RGBA"), int(x0), int(y0)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return x * x * (3 - 2 * x)


# ── full-screen pieces ───────────────────────────────────────────────────────
CHROME = dict(glow=0, card="none", hints=False, ring=0, sync=0.0, core=0, links=0, chips=[0, 0, 0, 0],
              harm=0, verdict=None)


def chrome():
    """GRUB background minus the art: header, footer, corner brackets, scanlines."""
    return g.scene(CHROME)


def center_glow():
    """chrome + a centred violet glow and hex grid (design canvas, then native)."""
    img = Image.new("RGBA", (DW, DH), rgba(BG))
    glow = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for (cx, cy, r, a, col) in ((CX - 120, CY, 640, 52, VIOLET), (CX + 300, CY + 40, 520, 14, PINK)):
        gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgba(col, a))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(220)))
    grid = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    r = 34
    hw, hh = math.sqrt(3) * r, 1.5 * r
    for row in range(int(DH / hh) + 2):
        for col in range(int(DW / hw) + 2):
            cx = col * hw + (hw / 2 if row % 2 else 0)
            cy = row * hh
            fade = max(0, 1 - abs(cx - CX) / 1100) * max(0, 1 - abs(cy - CY) / 620)
            if fade > 0.05:
                pts = [(cx + r * math.cos(math.radians(60 * k + 30)), cy + r * math.sin(math.radians(60 * k + 30)))
                       for k in range(6)]
                gd.polygon(pts, outline=rgba(VIOLET, int(26 * fade)))
    img.alpha_composite(grid)
    # chrome on top, exactly as GRUB draws it
    ch = g.scene(CHROME, native=False).convert("RGBA")
    base = Image.new("RGBA", (DW, DH), rgba(BG))
    mark, mx, my = uncomposite(ch, base)
    # scanlines are part of `mark` (dark rows over BG); apply chrome marks then the same scanlines
    img.alpha_composite(mark, (mx, my))
    return img.convert("RGB").resize((W, H), Image.LANCZOS)


# ── GRUB card: launch log rows, label, bar (native geometry, as theme.txt places them) ─────
def card_rows():
    G = g.geometry()
    mx0, my0, mw, _ = G["menu"]
    ih, gap = G["item_h"], G["item_gap"]
    fi, fs = font("Regular", 34), font("ExtraBold", 34)
    tx = 25 + 50 + 29
    rows = [("arch", "Arch Linux", "linux", True),
            (None, "ENTRY PLUG  ·  KERNEL", "OK", False),
            (None, "初号機  SYNC RATIO", "41.3 %", False)]
    out = []
    for i, (icon, label, status, sel) in enumerate(rows):
        y = my0 + i * (ih + gap)
        base = Image.new("RGBA", (mw, ih), (0, 0, 0, 0))
        d = ImageDraw.Draw(base)
        if sel:
            d.rectangle((0, 0, mw, ih), fill=SEL)
            d.rectangle((0, 0, 5, ih), fill=VIOLET)
        else:
            d.rectangle((25, ih // 2 - 3, 25 + 50, ih // 2 + 3), fill=LINE)
        if icon:
            ic = Image.open(GRUB_DIR / "magi-neon" / "icons" / f"{icon}.png").resize((50, 50))
            base.alpha_composite(ic, (25, (ih - 50) // 2))
        if label.startswith("初号機"):
            lw = mixed(d, (tx, ih // 2), [("初号機  ", cjk(30), ITEM), ("SYNC RATIO", fi, ITEM)], "lm") - tx
        else:
            text(d, (tx, ih // 2), label, fs if sel else fi, VIOLET if sel else ITEM, "lm")
            lw = d.textlength(label, font=fi)
        if not sel:
            x = tx + lw + 26
            while x < mw - 190:
                d.rectangle((x, ih // 2 + 9, x + 3, ih // 2 + 12), fill=LINE)
                x += 18
        st = Image.new("RGBA", (mw, ih), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        text(sd, (mw - 25, ih // 2), status, font("Bold", 29) if sel else font("ExtraBold", 31),
             DIM if sel else GREEN, "rm")
        out.append((scan_native(base, y), mx0, y, scan_native(st, y)))
    lx, ly, lw_, lh = G["label"]
    lab = Image.new("RGBA", (lw_, lh), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lab)
    mixed(ld, (0, lh // 2), [("LAUNCH  ·  ", font("Bold", 25), VIOLET), ("発進", cjk(24), VIOLET)], "lm")
    text(ld, (lw_, lh // 2), "AUTHORIZED", font("Regular", 25), DIM, "rm")
    return out, (scan_native(lab, ly), lx, ly), G["bar"]


def bar_frames(bx, by, bw, bh, n=24):
    frames = []
    for k in range(n):
        im = Image.new("RGBA", (bw, bh), rgba(LINE))
        fw = round(bw * ease_out(k / (n - 1)))
        if fw:
            ImageDraw.Draw(im).rectangle((0, 0, fw - 1, bh), fill=VIOLET)
            ImageDraw.Draw(im).rectangle((max(0, fw - 18), 0, fw - 1, bh), fill=GREEN)
        frames.append(scan_native(im, by))
    return frames


# ── NERV emblem (design coordinates) ─────────────────────────────────────────
SS = 4
TIP = object()
LEAF_RAW = [(0, -342), (-26, -296), (-52, -244), (-72, -190), (-82, -140), (-80, -104), (-70, -84), TIP,
            (-104, -112), (-150, -152), (-202, -188), (-264, -214), TIP,
            (-268, -170), (-258, -124), (-234, -82), (-200, -46), (-164, -14), (-140, 0), TIP,
            (-186, 4), (-240, 2), (-298, 6), TIP,
            (-294, 54), (-272, 106), (-238, 152), (-196, 190), (-148, 222), (-96, 246), (-44, 257), (0, 254)]
LEAF_PTS = []
for _p in LEAF_RAW:
    LEAF_PTS.append(LEAF_PTS[-1] if _p is TIP else _p)
LEAF_PTS[0:1] = [LEAF_PTS[0], LEAF_PTS[0]]
VEINS = [((0, -74), (-212, -176), 15, 3), ((0, 30), (-244, 12), 14, 3),
         ((0, -196), (-54, -276), 10, 2), ((0, 118), (-176, 196), 12, 2),
         ((-120, -128), (-168, -70), 7, 2), ((-150, 18), (-216, 84), 7, 2)]
LEAF_X, LEAF_Y = CX - 160, CY


def catmull(pts, steps=14):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-1])
    return out


WORD = "NERV"
WORD_SIZE = 250
WORD_X, WORD_BASE = LEAF_X - 34, CY + 40


def word_layer():
    """NERV in heavy italic + the green rule (full design canvas); also its knock-out mask."""
    f = font("ExtraBoldItalic", WORD_SIZE)
    im = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = WORD_X
    for ch in WORD:
        d.text((x, WORD_BASE), ch, font=f, fill=FG, anchor="ls")
        x += d.textlength(ch, font=f) + 14
    word_right = x - 14
    bx0, by0, bx1, by1 = im.getbbox()
    bx0, by0, bx1, by1 = bx0 - 16, by0 - 16, bx1 + 16, by1 + 16
    mask = Image.new("L", (DW, DH), 0)
    mask.paste(im.getchannel("A").crop((bx0, by0, bx1, by1)).filter(ImageFilter.MaxFilter(25)), (bx0, by0))
    d.rectangle((LEAF_X + 30, WORD_BASE + 34, word_right, WORD_BASE + 39), fill=GREEN)
    return im, mask, word_right


def leaf_layer(knock):
    xs = [p[0] for p in LEAF_PTS]
    ys = [p[1] for p in LEAF_PTS] + [342]
    x0, x1 = LEAF_X + min(xs) - 8, LEAF_X + 8
    y0, y1 = LEAF_Y + min(ys) - 8, LEAF_Y + max(ys) + 8
    w, h = x1 - x0, y1 - y0
    m = Image.new("L", (w * SS, h * SS), 0)
    d = ImageDraw.Draw(m)

    def P(p):
        return ((LEAF_X + p[0] - x0) * SS, (LEAF_Y + p[1] - y0) * SS)
    outline = catmull(LEAF_PTS) + [(0, 254), (0, -330)]
    d.polygon([P(p) for p in outline], fill=255)
    d.polygon([P(p) for p in ((0, 240), (1, 342), (-12, 338), (-14, 244))], fill=255)
    for (a, b, wa, wb) in VEINS:
        ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2
        nx, ny = math.cos(ang), math.sin(ang)
        quad = [(a[0] + nx * wa / 2, a[1] + ny * wa / 2), (b[0] + nx * wb / 2, b[1] + ny * wb / 2),
                (b[0] - nx * wb / 2, b[1] - ny * wb / 2), (a[0] - nx * wa / 2, a[1] - ny * wa / 2)]
        d.polygon([P(p) for p in quad], fill=0)
    d.rectangle((P((-5, -300))[0], P((0, -300))[1], P((-1, 0))[0], P((0, 236))[1]), fill=0)
    m = m.resize((w, h), Image.LANCZOS)
    m = ImageChops.subtract(m, knock.crop((x0, y0, x1, y1)))
    grad = np.linspace(0, 1, h)[:, None]
    top, bot = np.array(rgba("#b48af0")[:3], float), np.array(rgba("#6a2fc4")[:3], float)
    rgb = (top * (1 - grad) + bot * grad)[:, None, :].repeat(w, axis=1)
    img = Image.fromarray(np.dstack([rgb, np.asarray(m, float)]).round().astype(np.uint8))
    return img, x0, y0


def leaf_frames(leaf, x0, y0, n=46):
    """Wipe from the stem up with a hot green leading edge; frame k at ease_in_out(k/(n-1))."""
    a = np.asarray(leaf).astype(np.float32)
    h = a.shape[0]
    hot = np.array(rgba("#d4ff8a")[:3], np.float32)
    frames = []
    for k in range(n):
        p = ease_in_out(k / (n - 1))
        edge = h - p * (h + 40)
        f = a.copy()
        rows = np.arange(h, dtype=np.float32)
        vis = np.clip((rows - edge) / 6.0, 0, 1)
        heat = np.clip(1 - (rows - edge) / 46.0, 0, 1) * (rows >= edge) * (1 - p ** 6)
        f[..., 3] *= vis[:, None]
        f[..., :3] = f[..., :3] * (1 - heat[:, None, None] * 0.8) + hot * heat[:, None, None] * 0.8
        b = Box(x0, y0, x0 + leaf.width, y0 + h, pad=8)
        b.img.alpha_composite(Image.fromarray(np.clip(f + 0.5, 0, 255).astype(np.uint8)), b.p(x0, y0))
        frames.append(b.native())
    return frames


# motto: 逃げちゃダメだ ×3, then the English line
MOTTO = [("逃げちゃダメだ  逃げちゃダメだ  逃げちゃダメだ", "cjk"), ("I mustn't run away.", "latin")]
MOTTO_SIZE = 40
CPS_CJK, CPS = 13.0, 24.0


def motto_frames():
    fj, fl = ImageFont.truetype(CJK_MED, 38), font("Italic", MOTTO_SIZE)
    x0, y0 = LEAF_X + 40, WORD_BASE + 66
    lh = 62
    fonts = [fj if kind == "cjk" else fl for _, kind in MOTTO]
    total = sum(len(s) for s, _ in MOTTO)
    frames, cursor, times = [], [], []
    t = T_TYPE
    for k in range(total + 1):
        b = Box(x0, y0, x0 + 1100, y0 + lh * 2 + 20, pad=8)
        left = k
        cx, cy = 0, 0
        for li, ((s, kind), f) in enumerate(zip(MOTTO, fonts)):
            part = s[:max(0, min(len(s), left))]
            if part:
                b.d.text(b.p(x0, y0 + li * lh + 44), part, font=f, fill=FG if kind == "latin" else "#cfc6ee",
                         anchor="ls")
            if left <= len(s):
                cx, cy = f.getlength(part), li * lh
                break
            left -= len(s)
        frames.append(b.native())
        cursor.append((round((x0 + cx + 6) * K), round((y0 + cy + 8) * K)))
        times.append(round(t, 3))
        flat = "".join(s for s, _ in MOTTO)
        nxt = flat[k] if k < total else ""
        in_cjk = k < len(MOTTO[0][0])
        t += (1 / CPS_CJK if in_cjk else 1 / CPS)
        if in_cjk and nxt == " " and flat[k - 1:k] != " ":
            t += 0.16                                     # a breath between the three
        if k + 1 == len(MOTTO[0][0]):
            t += 0.45                                     # beat before the English line
    cur = Image.new("RGBA", (round(fl.getlength("M") * 0.62 * K), round(44 * K)), rgba(GREEN))
    return frames, cursor, times, cur


def agency_line():
    b = Box(LEAF_X + 40, WORD_BASE - 300, LEAF_X + 1400, WORD_BASE - 230, pad=8)
    y = WORD_BASE - 276
    x = LEAF_X + 40
    f1, f2 = cjk(26), font("Regular", 20)
    parts = [("特務機関ネルフ", f1), ("  ·  EVANGELION  ·  ", f2), ("初号機", f1), ("  ·  TEST TYPE", f2)]
    for s, f in parts:
        b.d.text(b.p(x, y), s, font=f, fill=DIM, anchor="lm")
        x += b.d.textlength(s, font=f)
    return b.native()


# ── synchronization test panel ───────────────────────────────────────────────
PANEL_BOX = (780, 510, 1780, 1090)
PILOT = "tjabo"
CHIPS = [("LCL", "正常"), ("A10 NERVE", "正常"), ("HARMONICS", "正常")]
SYNC = 41.3


def panel():
    x0, y0, x1, y1 = PANEL_BOX
    b = Box(x0, y0, x1 + 1, y1 + 1, pad=8)
    d = b.d
    d.rectangle((*b.p(x0, y0), *b.p(x1, y1)), fill=rgba(BG, 240), outline=LINE, width=2)
    d.rectangle((*b.p(x0, y0), *b.p(x1, y0 + 5)), fill=VIOLET)
    mixed(d, b.p(x0 + 40, y0 + 70), [("シンクロ ", cjk(34), VIOLET), ("SYNCHRONIZATION", font("ExtraBold", 34), VIOLET)])
    text(d, b.p(x1 - 40, y0 + 70), "ENTRY PLUG 01 · tty1", font("Bold", 20), PINK, "rs")
    text(d, b.p(x0 + 40, y0 + 108), "NEON // unit-01  ·  PILOT AUTHENTICATION  ·  SESSION hyprland",
         font("Regular", 20), DIM, "ls")
    d.line((*b.p(x0 + 40, y0 + 136), *b.p(x1 - 40, y0 + 136)), fill=LINE, width=2)
    for label, by in (("PILOT", 196), ("SYNC RATIO  ·  シンクロ率", 312)):
        if "シ" in label:
            mixed(d, b.p(x0 + 40, y0 + by - 14), [("SYNC RATIO  ·  ", font("Bold", 18), DIM), ("シンクロ率", cjk(17), DIM)])
        else:
            text(d, b.p(x0 + 40, y0 + by - 14), label, font("Bold", 18), DIM, "ls")
        d.rectangle((*b.p(x0 + 40, y0 + by), *b.p(x1 - 40, y0 + by + 64)), outline=LINE, width=2)
    d.line((*b.p(x0 + 40, y1 - 74), *b.p(x1 - 40, y1 - 74)), fill=LINE, width=2)
    return b.native()


def field_box(by):
    x0, y0, x1, _ = PANEL_BOX
    return x0 + 44, y0 + by + 4, x1 - 44, y0 + by + 61


def pilot_frames():
    fx0, fy0, fx1, fy1 = field_box(196)
    f = font("Medium", 30)
    h = fy1 - fy0

    def frame(n, caret):
        b = Box(fx0, fy0, fx1, fy1, pad=8)
        s = PILOT[:n]
        b.d.text(b.p(fx0 + 22, fy0 + h // 2 + 1), s, font=f, fill=FG, anchor="lm")
        cx = fx0 + 22 + b.d.textlength(s, font=f) + (6 if s else 0)
        if caret:
            b.d.rectangle((*b.p(cx, fy0 + 12), *b.p(cx + 13, fy1 - 12)), fill=GREEN)
        return b.native()
    frames = [frame(0, True)] + [frame(k, True) for k in range(1, len(PILOT) + 1)] + [frame(len(PILOT), False)]
    times = [T_PANEL] + [round(T_USER + (k - 1) * USER_DT, 3) for k in range(1, len(PILOT) + 1)] + [T_SYNC[0] - 0.2]
    return frames, times


def sync_frames(n=30):
    fx0, fy0, fx1, fy1 = field_box(312)
    h = fy1 - fy0
    fnum = font("ExtraBold", 32)
    bx0, bx1 = fx0 + 22, fx1 - 200
    frames, times = [], []
    for k in range(n + 1):
        v = SYNC * ease_out(k / n) if k else 0.0
        b = Box(fx0, fy0, fx1, fy1, pad=8)
        d = b.d
        # scale ticks every 10 %
        for j in range(11):
            tx = bx0 + (bx1 - bx0) * j / 10
            d.line((*b.p(tx, fy0 + 14), *b.p(tx, fy0 + 20)), fill=LINE, width=2)
        d.rectangle((*b.p(bx0, fy0 + 26), *b.p(bx1, fy0 + 36)), fill=g.TRACK)
        fw = (bx1 - bx0) * v / 100
        if fw > 0:
            d.rectangle((*b.p(bx0, fy0 + 26), *b.p(bx0 + fw, fy0 + 36)), fill=VIOLET)
            d.rectangle((*b.p(bx0 + max(0, fw - 8), fy0 + 22), *b.p(bx0 + fw, fy0 + 40)), fill=GREEN)
        s = f"{v:4.1f}"
        col = GREEN if k == n else FG
        text(d, b.p(fx1 - 60, fy0 + h // 2 + 2), s, fnum, col, "rm")
        text(d, b.p(fx1 - 22, fy0 + h // 2 + 2), "%", font("Bold", 22), DIM, "rm")
        frames.append(b.native())
        times.append(T_PANEL if k == 0 else round(T_SYNC[0] + (T_SYNC[1] - T_SYNC[0]) * k / n, 3))
    return frames, times


def chip_frames(i):
    x0, y0, _, _ = PANEL_BOX
    cw, chh, gap = 290, 70, 25
    cx, cy = x0 + 40 + i * (cw + gap), y0 + 410
    name, ok = CHIPS[i]
    out = []
    for lit in (False, True):
        b = Box(cx, cy, cx + cw + 1, cy + chh + 1, pad=8)
        d = b.d
        pts = [b.p(*p) for p in g.chamfer(cx, cy, cx + cw, cy + chh, 16)]
        if lit:
            d.polygon(pts, fill=GREEN, outline="#d4ff8a", width=2)
            text(d, b.p(cx + 18, cy + chh // 2), name, font("ExtraBold", 22), BG, "lm")
            text(d, b.p(cx + cw - 18, cy + chh // 2), ok, cjk(26), BG, "rm")
        else:
            d.polygon(pts, fill=rgba(PANEL, 235), outline=LINE, width=2)
            text(d, b.p(cx + 18, cy + chh // 2), name, font("Bold", 22), DIM, "lm")
            text(d, b.p(cx + cw - 18, cy + chh // 2), f"· {i + 1}", font("Bold", 20), DIM, "rm")
        out.append(b.native())
    return out


def status_frames():
    x0, y0, x1, y1 = PANEL_BOX
    sx, sy = x0 + 40, y1 - 70
    w, h = x1 - x0 - 80, 62
    states = [("AWAITING PILOT ...", DIM, "Regular", "0 / 3")] + \
             [("SYNCHRONIZING  ·  CROSSING THE BORDERLINE", VIOLET, "Bold", f"{n} / 3") for n in range(4)] + \
             [("EVA-01 ACTIVATED", GREEN, "ExtraBold", "3 / 3  ·  起動")]
    out = []
    for msg, col, wt, right in states:
        b = Box(sx, sy, sx + w, sy + h, pad=8)
        text(b.d, b.p(sx, sy + h // 2), msg, font(wt, 24 if wt == "ExtraBold" else 22), col, "lm")
        fr = cjk(22) if "起動" in right else font("Bold", 22)
        text(b.d, b.p(sx + w, sy + h // 2), right, fr, col, "rm")
        out.append(b.native())
    times = [T_PANEL, T_SYNC[0]] + list(T_CHIPS) + [T_ACT]
    return out, times


# ── unit-01 art + welcome ────────────────────────────────────────────────────
WELCOME = [("WELCOME, ", FG), ("TJABO", VIOLET)]
WX, WY = 200, 1150                   # welcome baseline (design), lower left, clear of the unit


def art():
    """The lock-screen art, cropped to 16:10, dimmed and shaded for text on the lower left.
    Stored at half size: unit01.script scales it to the screen (it is soft art anyway)."""
    src = Image.open(ART_SRC).convert("RGB")
    sw, sh = src.size
    tw = min(sw, round(sh * 16 / 10))
    th = round(tw * 10 / 16)
    cx = sw // 2
    src = src.crop((cx - tw // 2, (sh - th) // 2, cx - tw // 2 + tw, (sh - th) // 2 + th))
    hw, hh = W // 2, H // 2
    a = np.asarray(src.resize((hw, hh), Image.LANCZOS)).astype(np.float32)
    yy, xx = np.mgrid[0:hh, 0:hw].astype(np.float32)
    u, v = xx / hw, yy / hh
    shade = 0.62
    shade = shade * (1 - 0.55 * np.clip((0.55 - u) / 0.55, 0, 1) * np.clip((v - 0.25) / 0.6, 0, 1))  # text corner
    shade = shade * (1 - 0.45 * np.clip((v - 0.7) / 0.3, 0, 1))                                       # bottom
    vig = np.clip(1 - 0.9 * ((u - 0.55) ** 2 * 1.6 + (v - 0.45) ** 2 * 1.4), 0.35, 1)
    shade = shade * vig
    bgc = np.array(rgba(BG)[:3], np.float32)
    out = a * shade[..., None] + bgc * (1 - shade[..., None]) * 0.9
    for r in range(0, hh, 2):                                   # scanlines at half size
        out[r] *= 1 - 24 / 255
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))


def welcome_frames():
    f = font("ExtraBold", 96)
    full = "".join(s for s, _ in WELCOME)
    caret_w = round(f.getlength("M") * 0.55)
    frames, times = [], []
    for k in range(len(full) + 2):
        n = min(k, len(full))
        b = Box(WX, WY - 100, WX + f.getlength(full) + caret_w + 30, WY + 20, pad=8)
        x, left = WX, n
        for s, col in WELCOME:
            part = s[:max(0, min(len(s), left))]
            if part:
                b.d.text(b.p(x, WY), part, font=f, fill=col, anchor="ls")
            x += f.getlength(part) if part else 0
            left -= len(s)
            if left < 0:
                break
        if k <= len(full):
            cx = WX + f.getlength(full[:n])
            b.d.rectangle((*b.p(cx + 8, WY - 72), *b.p(cx + 8 + caret_w, WY + 2)), fill=GREEN)
        frames.append(b.native(scan=False))
        times.append(round(T_WELCOME + k * WEL_DT, 3) if k <= len(full) else T_WSUB[0])
    b = Box(WX, WY + 30, WX + 1400, WY + 90, pad=8)
    f1, f2 = cjk(28), font("Regular", 22)
    x = WX + 4
    for s, ff, col in (("おかえりなさい", f1, FG), ("  ·  EVA-01 LAUNCH  ·  ", f2, ITEM), ("発進", f1, GREEN),
                       ("  ·  NEON SESSION STARTING", f2, ITEM)):
        b.d.text(b.p(x, WY + 60), s, font=ff, fill=col, anchor="lm")
        x += b.d.textlength(s, font=ff)
    # a short green rule above the name, like the NERV rule
    b2 = Box(WX, WY - 150, WX + 260, WY - 140, pad=8)
    b2.d.rectangle((*b2.p(WX + 4, WY - 146), *b2.p(WX + 180, WY - 142)), fill=GREEN)
    return frames, times, b.native(scan=False), b2.native(scan=False)


# ── assemble layers + timeline ───────────────────────────────────────────────
def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    layers = []

    def save(img, name):
        img.save(OUT / name, optimize=True)
        return name

    grub_bg = Image.open(GRUB_DIR / "magi-neon" / "background.png").convert("RGB")
    assert grub_bg.size == (W, H)
    base = chrome()
    save(base, "chrome.png")
    layers.append(dict(name="chrome", files=["chrome.png"], x=0, y=0, z=0, op=[(0, 1)], full=True, need=0.9))

    art_, ax, ay = uncomposite(grub_bg, base)
    save(art_, "grub-art.png")
    layers.append(dict(name="art", files=["grub-art.png"], x=ax, y=ay, z=2,
                       op=[(T_ART_OUT[0], 1), (T_ART_OUT[1], 0)], need=1.0))
    shutil.copy(GRUB_DIR / "magi-neon" / "background.png", OUT / "first.png")
    layers.append(dict(name="first", files=["first.png"], x=0, y=0, z=3, full=True, need=-1,
                       op=[(T_ART_OUT[0], 1), (T_ART_OUT[0] + 0.001, 0)]))

    glow, gx, gy = uncomposite(center_glow(), base)
    save(glow, "glow.png")
    layers.append(dict(name="glow", files=["glow.png"], x=gx, y=gy, z=1,
                       op=[(T_GLOW_IN[0], 0), (T_GLOW_IN[1], 1)]))

    rows, (lab, lx, ly), (bx, by, bw, bh) = card_rows()
    out_k = [(T_ART_OUT[0], 1), (T_ART_OUT[1] - 0.15, 0)]
    for i, (row, rx, ry, st) in enumerate(rows):
        t0, t1 = T_ROWS[i], T_OK[i]
        layers.append(dict(name=f"row{i}", files=[save(row, f"row{i}.png")], x=rx, y=ry, z=4,
                           op=[(t0, 0), (t0 + 0.04, 1), (t0 + 0.08, 0.35), (t0 + 0.12, 1)] + out_k))
        layers.append(dict(name=f"ok{i}", files=[save(st, f"ok{i}.png")], x=rx, y=ry, z=5,
                           op=[(t1, 0), (t1 + 0.05, 1), (t1 + 0.1, 0.2), (t1 + 0.16, 1)] + out_k))
    layers.append(dict(name="label", files=[save(lab, "label.png")], x=lx, y=ly, z=4,
                       op=[(T_LABEL, 0), (T_LABEL + 0.12, 1)] + out_k))
    bars = bar_frames(bx, by, bw, bh)
    n = len(bars)
    layers.append(dict(name="bar", files=[save(b, f"bar-{k:02d}.png") for k, b in enumerate(bars)], x=bx, y=by, z=4,
                       op=[(T_BAR[0] - 0.01, 0), (T_BAR[0], 1)] + out_k,
                       seq=[round(T_BAR[0] + (T_BAR[1] - T_BAR[0]) * k / (n - 1), 3) for k in range(n)]))

    emb_out = [(T_EMBLEM_OUT[0], 1), (T_EMBLEM_OUT[1], 0)]
    word, knock, _ = word_layer()
    leaf, lfx, lfy = leaf_layer(knock)
    lf = leaf_frames(leaf, lfx, lfy)
    n = len(lf)
    layers.append(dict(name="leaf", files=[save(f, f"leaf-{k:02d}.png") for k, (f, _, _) in enumerate(lf)],
                       x=lf[0][1], y=lf[0][2], z=6, op=[(T_LEAF[0] - 0.01, 0), (T_LEAF[0], 1)] + emb_out,
                       seq=[round(T_LEAF[0] + (T_LEAF[1] - T_LEAF[0]) * k / (n - 1), 3) for k in range(n)],
                       pos_each=[(x, y) for _, x, y in lf]))

    bb = word.getbbox()
    wb = Box(*bb, pad=8)
    wb.img.alpha_composite(word.crop(bb), wb.p(bb[0], bb[1]))
    wimg, wx, wy = wb.native()
    tw = T_WORD
    layers.append(dict(name="word", files=[save(wimg, "word.png")], x=wx, y=wy, z=7,
                       op=[(tw, 0), (tw + 0.03, 0.85), (tw + 0.07, 0.1), (tw + 0.12, 0.1), (tw + 0.15, 1),
                           (tw + 0.22, 0.4), (tw + 0.27, 1)] + emb_out))

    sub, sx_, sy_ = agency_line()
    layers.append(dict(name="agency", files=[save(sub, "agency.png")], x=sx_, y=sy_, z=7,
                       op=[(T_SUB[0], 0), (T_SUB[1], 1)] + emb_out))

    mf, cursor, times, cur = motto_frames()
    layers.append(dict(name="motto", files=[save(f, f"motto-{k:02d}.png") for k, (f, _, _) in enumerate(mf)],
                       x=mf[0][1], y=mf[0][2], z=7, op=emb_out, seq=times, need=T_TYPE - 0.3,
                       pos_each=[(x, y) for _, x, y in mf]))
    t_typed = times[-1]
    blink = []
    t = t_typed
    while t + 0.6 < T_EMBLEM_OUT[0]:
        blink += [(t, 1), (t + 0.3, 1), (t + 0.3001, 0), (t + 0.5999, 0)]
        t += 0.6
    blink += [(T_EMBLEM_OUT[0], 1), (T_EMBLEM_OUT[0] + 0.3, 0)]
    layers.append(dict(name="cursor", files=[save(cur, "cursor.png")], x=cursor[0][0], y=cursor[0][1], z=8,
                       op=[(times[0] - 0.3, 0), (times[0] - 0.2999, 1), (times[0] - 0.05, 1)] + blink,
                       pos=cursor, seq=times))

    # synchronization test
    pin = [(T_PANEL, 0), (T_PANEL + 0.04, 0.9), (T_PANEL + 0.08, 0.2), (T_PANEL + 0.14, 1),
           (T_PANEL_OUT[0], 1), (T_PANEL_OUT[1], 0)]
    pan, px_, py_ = panel()
    layers.append(dict(name="panel", files=[save(pan, "sync-panel.png")], x=px_, y=py_, z=10, op=pin))

    def seq_layer(name, frames, times, z, op):
        layers.append(dict(name=name, files=[save(f, f"{name}-{k:02d}.png") for k, (f, _, _) in enumerate(frames)],
                           x=frames[0][1], y=frames[0][2], z=z, op=op, seq=times,
                           pos_each=[(x, y) for _, x, y in frames]))
    fr, ts = pilot_frames()
    seq_layer("pilot", fr, ts, 11, pin)
    fr, ts = sync_frames()
    seq_layer("sync", fr, ts, 11, pin)
    for i in range(3):
        fr = chip_frames(i)
        seq_layer(f"chip{i}", fr, [T_PANEL, T_CHIPS[i]], 11, pin)
    fr, ts = status_frames()
    seq_layer("status", fr, ts, 11, pin)

    # unit-01 art + welcome
    save(art(), "unit01-art.png")
    layers.append(dict(name="unit01art", files=["unit01-art.png"], x=0, y=0, z=9, full=3,
                       op=[(T_ARTW[0], 0), (T_ARTW[1], 1)], need=T_ARTW[0] - 1.5))
    fr, ts, wsub, wrule = welcome_frames()
    seq_layer("welcome", fr, ts, 12, [(T_WELCOME - 0.01, 0), (T_WELCOME, 1)])
    layers.append(dict(name="wsub", files=[save(wsub[0], "welcome-sub.png")], x=wsub[1], y=wsub[2], z=12,
                       op=[(T_WSUB[0], 0), (T_WSUB[1], 1)]))
    layers.append(dict(name="wrule", files=[save(wrule[0], "welcome-rule.png")], x=wrule[1], y=wrule[2], z=12,
                       op=[(T_WELCOME - 0.2, 0), (T_WELCOME, 1)]))

    fade = Image.new("RGB", (16, 16), rgba(BG)[:3])
    layers.append(dict(name="fade", files=[save(fade, "fade.png")], x=0, y=0, z=30,
                       op=[(T_FADE[0], 0), (T_FADE[1], 1)], full=2))
    for L in layers:
        L.setdefault("seq", None)
        L.setdefault("full", False)
        L.setdefault("pos", None)
        L.setdefault("pos_each", None)
        L.setdefault("need", min(t for t, v in L["op"]) if L["op"] else 0)
        if L["pos_each"] and len(set(L["pos_each"])) == 1:
            L["pos_each"] = None
    write_script(layers)
    write_hold()
    return layers


# ── Plymouth files ───────────────────────────────────────────────────────────
def write_script(layers):
    (OUT / f"{NAME}.plymouth").write_text(f"""[Plymouth Theme]
Name=UNIT-01
Description=Neon EVA unit-01 boot: continues the GRUB theme into a NERV emblem, a sync test and the unit-01 art (built by ~/.local/share/neon/plymouth-theme/build.py)
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{NAME}
ScriptFile=/usr/share/plymouth/themes/{NAME}/{NAME}.script
ConsoleLogBackgroundColor=0x{BG.lstrip('#')}
""")
    S = 200
    r, gg, b = (c / 255 for c in rgba(BG)[:3])
    out = [f"""# unit-01 Plymouth theme. Generated by ~/.local/share/neon/plymouth-theme/build.py; edit that.
# t = Plymouth boot-progress time (plymouthd age) - anchor, anchor = max(LEAD, first frame + 0.1).
# Only frame 0 is loaded before the first draw; the rest loads a few images per refresh.

Window.SetBackgroundTopColor({r:.4f}, {gg:.4f}, {b:.4f});
Window.SetBackgroundBottomColor({r:.4f}, {gg:.4f}, {b:.4f});
Plymouth.SetRefreshRate(60);

W0 = {W}; H0 = {H}; S = {S};
LEAD = {LEAD}; T_STATIC = {T_STATIC}; ANIM_END = {ANIM_END};
SW = Window.GetWidth(); SH = Window.GetHeight();
if (SW < 1) SW = W0;
if (SH < 1) SH = H0;
SX = SW / W0; SY = SH / H0;
NATIVE = 0;
if (SW == W0 && SH == H0) NATIVE = 1;
OX = Window.GetX(); OY = Window.GetY();

fun load(name, full) {{
  local.img = Image(name);
  if (full >= 2) return img.Scale(global.SW, global.SH);
  if (global.NATIVE) return img;
  if (full) return img.Scale(global.SW, global.SH);
  return img.Scale(Math.Int(img.GetWidth() * global.SX + 0.5), Math.Int(img.GetHeight() * global.SY + 0.5));
}}

fun keyval(b, n, t) {{
  if (t <= kt[b]) return kv[b];
  local.j = 1;
  while (j < n) {{
    if (t <= kt[b + j]) return kv[b + j - 1] + (kv[b + j] - kv[b + j - 1]) * (t - kt[b + j - 1]) / (kt[b + j] - kt[b + j - 1]);
    j = j + 1;
  }}
  return kv[b + n - 1];
}}
"""]
    NL = len(layers)
    o = out.append
    o(f"NL = {NL};")
    for name in ("lx", "ly", "lz", "lfull", "nf", "nk", "ns", "isseq", "ispos", "ready", "cur", "op",
                 "kt", "kv", "st", "px", "py", "fn", "img", "spr", "qi", "qk"):
        o(f"{name}[0] = 0;")
    for i, L in enumerate(layers):
        bse = i * S
        # pos: the sprite moves (cursor); pos_each: each frame of a sequence has its own spot
        pos = L["pos"] or L["pos_each"]
        o(f"# {i}: {L['name']}")
        o(f"lx[{i}] = {L['x']}; ly[{i}] = {L['y']}; lz[{i}] = {L['z']}; lfull[{i}] = {int(L['full'])}; "
          f"nf[{i}] = {len(L['files'])}; nk[{i}] = {len(L['op'])}; ready[{i}] = 0; cur[{i}] = 0; op[{i}] = -1;")
        o(f"isseq[{i}] = {int(L['seq'] is not None)}; ispos[{i}] = {2 if L['pos_each'] else int(L['pos'] is not None)}; "
          f"ns[{i}] = {len(L['seq']) if L['seq'] else 0};")
        assert len(L["files"]) < S and len(L["op"]) < S and (not L["seq"] or len(L["seq"]) < S)
        o(" ".join(f'fn[{bse + k}] = "{f}";' for k, f in enumerate(L["files"])))
        o(" ".join(f"kt[{bse + k}] = {t:.4f}; kv[{bse + k}] = {v};" for k, (t, v) in enumerate(L["op"])))
        if L["seq"]:
            o(" ".join(f"st[{bse + k}] = {t};" for k, t in enumerate(L["seq"])))
        if pos:
            o(" ".join(f"px[{bse + k}] = {x}; py[{bse + k}] = {y};" for k, (x, y) in enumerate(pos)))
    q = [(i, k) for i in sorted(range(NL), key=lambda i: layers[i]["need"]) for k in range(len(layers[i]["files"]))]
    o(f"QN = {len(q)}; qpos = 0;")
    o(" ".join(f"qi[{n}] = {i}; qk[{n}] = {k};" for n, (i, k) in enumerate(q)))
    out.append(f"""
fun load_one() {{
  local.i = qi[global.qpos];
  local.k = qk[global.qpos];
  local.b = i * S;
  global.img[b + k] = load(fn[b + k], lfull[i]);
  if (k == 0) {{
    global.spr[i] = Sprite(img[b]);
    if (ispos[i] == 2) spr[i].SetPosition(OX + px[b] * SX, OY + py[b] * SY, lz[i]);
    else spr[i].SetPosition(OX + lx[i] * SX, OY + ly[i] * SY, lz[i]);
    spr[i].SetOpacity(0);
  }}
  if (k == nf[i] - 1) global.ready[i] = 1;
  global.qpos = global.qpos + 1;
}}

fun load_some(n) {{
  while (n > 0 && global.qpos < QN) {{
    if (lfull[qi[global.qpos]]) n = 0;      # a full-screen image is a whole tick's budget
    load_one();
    n = n - 1;
  }}
}}

fun draw(t) {{
  local.i = 0;
  while (i < NL) {{
    if (ready[i]) {{
      local.b = i * S;
      local.o = keyval(b, nk[i], t);
      if (o != op[i]) {{ spr[i].SetOpacity(o); global.op[i] = o; }}
      if (isseq[i]) {{
        local.k = cur[i];
        while (k + 1 < ns[i] && st[b + k + 1] <= t) k = k + 1;
        if (k != cur[i]) {{
          if (ispos[i] == 1) spr[i].SetPosition(OX + px[b + k] * SX, OY + py[b + k] * SY, lz[i]);
          else {{
            spr[i].SetImage(img[b + k]);
            if (ispos[i] == 2) spr[i].SetPosition(OX + px[b + k] * SX, OY + py[b + k] * SY, lz[i]);
          }}
          global.cur[i] = k;
        }}
      }}
    }}
    i = i + 1;
  }}
}}

MODE = Plymouth.GetMode();
clock = -1;          # last boot-progress time (plymouthd age)
anchor = -1;
ticks = 0;
tlast = 0;

fun on_progress(duration, progress) {{
  global.clock = duration;
  global.ticks = 0;
}}

fun on_refresh() {{
  load_some(4);
  if (MODE != "boot") {{ draw(T_STATIC); return; }}
  if (global.clock < 0) {{ draw(0); return; }}
  if (global.anchor < 0) global.anchor = Math.Max(LEAD, global.clock + 0.1);
  global.ticks = global.ticks + 1;
  local.t = global.clock - global.anchor + Math.Min(global.ticks / 60, 0.05);
  if (t < global.tlast) t = global.tlast;
  global.tlast = t;
  draw(t);
}}

fun on_quit() {{
  while (global.qpos < QN) load_one();
  if (MODE == "boot") draw(ANIM_END);
}}

Plymouth.SetBootProgressFunction(on_progress);
Plymouth.SetRefreshFunction(on_refresh);
Plymouth.SetQuitFunction(on_quit);
load_some(1);        # frame 0 only
if (MODE == "boot") draw(0); else draw(T_STATIC);
""")
    (OUT / f"{NAME}.script").write_text("\n".join(out) + "\n")


def write_hold():
    (OUT / f"{NAME}-splash-hold").write_text(f"""#!/bin/bash
# Hold plymouth-quit until the unit-01 splash has played to the end.
# Generated by ~/.local/share/neon/plymouth-theme/build.py; edit that.
# The theme's clock is Plymouth's boot-progress time (plymouthd's age) and the animation starts
# at age max(LEAD, first frame + 0.1). Plymouth starts in the initramfs before the GPU driver,
# so its first frame comes right after the GPU's DRM device does: take that time from the
# kernel log (the first real "[drm] Initialized", not simpledrm; the NPU's amdxdna comes later)
# + SLACK for loading frame 0, and wait until anchor + ANIM_END + MARGIN.
# The splash ends on {ANIM_END - T_FADE[1]:.1f} s of plain background, which absorbs a small misestimate.
LEAD={LEAD}; ANIM_END={ANIM_END}; MARGIN={HOLD_MARGIN}; SLACK=0.35
plymouth --ping 2>/dev/null || exit 0
pid=$(cat /run/plymouth/pid 2>/dev/null)
[[ -r /proc/$pid/stat ]] || pid=$(pgrep -o -x plymouthd) || exit 0
start=$(awk -v t="$(getconf CLK_TCK)" '{{sub(/.*\\) /, ""); split($0, f, " "); printf "%.3f", f[20] / t}}' /proc/$pid/stat)
drm=$(dmesg -r 2>/dev/null | awk '/\\[drm\\] Initialized/ && !/simpledrm/ && !/amdxdna/ {{match($0, /\\[ *[0-9.]+\\]/); printf "%.3f", substr($0, RSTART + 1, RLENGTH - 2) + 0; exit}}')
read -r up _ < /proc/uptime
read -r anchor left < <(awk -v s="$start" -v d="${{drm:-0}}" -v u="$up" -v L="$LEAD" -v A="$ANIM_END" -v M="$MARGIN" -v K="$SLACK" \\
  'BEGIN {{ a = d - s + K; if (a < L) a = L; x = s + a + A + M - u; if (x < 0) x = 0; if (x > a + A + M) x = a + A + M;
           printf "%.2f %.2f", a, x }}')
echo "plymouthd started at ${{start}} s, GPU at ${{drm:-?}} s -> splash clock from age ${{anchor}} s; holding ${{left}} s"
sleep "$left"
""")
    (OUT / f"{NAME}-splash-hold").chmod(0o755)
    (OUT / f"{NAME}-splash-hold.service").write_text(f"""[Unit]
Description=Hold the boot until the unit-01 splash animation has finished
After=plymouth-start.service
Before=plymouth-quit.service plymouth-quit-wait.service

[Service]
Type=oneshot
ExecStart=/usr/local/lib/{NAME}-boot/{NAME}-splash-hold
TimeoutStartSec=30

[Install]
WantedBy=plymouth-quit.service plymouth-quit-wait.service
""")


# ── preview (same layer data, composited in Python) ──────────────────────────
def keyval(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


def render(layers, cache, t):
    frame = np.zeros((H, W, 3), np.float32) + np.array(rgba(BG)[:3], np.float32)
    for L in sorted(layers, key=lambda L: L["z"]):
        o = keyval(L["op"], t)
        if o <= 0:
            continue
        k = 0
        if L["seq"]:
            k = max(i for i, st in enumerate(L["seq"]) if st <= t or i == 0)
        fn = L["files"][0 if L["pos"] else k]
        if fn not in cache:
            im = Image.open(OUT / fn).convert("RGBA")
            if L["full"]:
                im = im.resize((W, H))
            cache[fn] = np.asarray(im).astype(np.float32)
        a = cache[fn]
        if L["pos"]:
            x, y = L["pos"][k]
        elif L["pos_each"]:
            x, y = L["pos_each"][k]
        else:
            x, y = L["x"], L["y"]
        h, w = a.shape[:2]
        al = a[..., 3:4] / 255 * o
        reg = frame[y:y + h, x:x + w]
        frame[y:y + h, x:x + w] = reg * (1 - al) + a[..., :3] * al
    return Image.fromarray(np.clip(frame + 0.5, 0, 255).astype(np.uint8))


KEYS = (0.0, 1.0, 2.3, 4.0, 6.6, 8.8, 9.3, 10.4, 11.6, 12.8, 13.8, 14.6, 15.6, 16.7)


def preview(layers, keys_only=False):
    pv = HERE / "preview"
    if pv.exists():
        shutil.rmtree(pv)
    (pv / "frames").mkdir(parents=True)
    cache = {}
    f0 = render(layers, cache, 0)
    grub_bg = Image.open(GRUB_DIR / "magi-neon" / "background.png").convert("RGB")
    diff = np.abs(np.asarray(f0).astype(int) - np.asarray(grub_bg).astype(int))
    print(f"frame 0 vs GRUB background: max diff {diff.max()}, pixels off {(diff.max(axis=2) > 1).sum()}")
    f1 = render(layers, cache, T_ART_OUT[0] + 0.01)
    print("art layer reproduces the GRUB board:", np.abs(np.asarray(f1).astype(int)[200:1500, 100:1500]
                                                         - np.asarray(grub_bg).astype(int)[200:1500, 100:1500]).max())
    for t in KEYS:
        render(layers, cache, t).save(pv / f"key-{t:04.1f}.png")
    if keys_only:
        return
    fps = 30
    for i in range(int(ANIM_END * fps) + 15):
        render(layers, cache, i / fps).resize((1440, 900), Image.LANCZOS).save(pv / "frames" / f"{i:04d}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(pv / "frames" / "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(pv / "preview.mp4")], check=True)
    shutil.rmtree(pv / "frames")


def main():
    layers = build()
    size = sum(f.stat().st_size for f in OUT.iterdir())
    print(f"built {OUT}: {len(list(OUT.iterdir()))} files, {size / 1e6:.1f} MB; animation {ANIM_END} s, "
          f"boot held until the splash has run {ANIM_END + HOLD_MARGIN:.1f} s")
    if "--preview" in sys.argv or "--keys" in sys.argv:
        preview(layers, keys_only="--keys" in sys.argv)


if __name__ == "__main__":
    main()
