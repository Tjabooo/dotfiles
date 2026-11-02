#!/usr/bin/env python3
"""Build the "magi-neon" GRUB theme (midnight neon palette) into ./magi-neon next to this script.
Laptop port of the desktop's ember "magi" theme (Tjabooo/dotfiles-desktop).

    python3 ~/.local/share/neon/grub-theme/build.py [--preview]

Drawn on a 2560x1600 (16:10) design canvas, the same pixel layout as the desktop's 2560x1440
shifted down by OY, then scaled exactly 1.125x to the Zenbook's native 2880x1800. theme.txt
coordinates and font sizes get the same 1.125 factor, so everything lines up.

Everything is generated: background art (MAGI triad + menu card baked in),
selection pixmaps, menu icons, GRUB fonts (grub-mkfont) and theme.txt.
--preview also writes preview.png: a mockup of what GRUB will draw on top.

Install (sudo, see README in the output folder):
    sudo cp -r magi-neon /boot/grub/themes/
    GRUB_THEME="/boot/grub/themes/magi-neon/theme.txt" in /etc/default/grub
    sudo grub-mkconfig -o /boot/grub/grub.cfg
Theme files are not signature-checked (GRUB is sbctl-signed, no shim), so this can't affect Secure Boot;
a broken theme only drops GRUB to its plain text menu.
"""
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 2560, 1600            # design canvas (16:10)
LW, LH = 2560, 1440          # the desktop layout, drawn on a layer...
OY = 80                      # ...placed this far down
FW, FH = 2880, 1800          # final size = native panel
S = FW / W                   # 1.125, uniform
HERE = Path(__file__).resolve().parent
OUT = HERE / "magi-neon"

# midnight neon palette (same as hyprland.lua / waybar / dunst)
BG, PANEL, LINE = "#0f0f1e", "#1a1a2f", "#2a2a45"
FG, DIM = "#e0e0f0", "#6c6c8a"
VIOLET, PINK, CYAN, RED = "#9b5de5", "#f15bb5", "#00c6ff", "#ff5252"
SEL, ITEM = "#251b40", "#a0a0c8"

TTF = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-{}.ttf"
CJK = "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"

# layout (pixels at 2560x1440; theme.txt gets percentages)
CARD = (1380, 380, 2440, 960)          # menu card
MENU = (1420, 548, 2400, 860)          # GRUB boot_menu area inside the card
ITEM_H, ITEM_GAP = 84, 14
TIMEOUT_LABEL_Y, BAR_Y = 858, 930      # countdown text + bar (bar top = BAR_Y - 25)
HINTS_Y = 1010


def font(weight, size):
    return ImageFont.truetype(TTF.format(weight), size)


def rgba(hexcol, a=255):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def chamfer(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1, y0), (x1, y1 - c), (x1 - c, y1), (x0, y1), (x0, y0 + c)]


def text(d, xy, s, f, fill, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


# ── background ───────────────────────────────────────────────────────────────
def background():
    img = Image.new("RGBA", (W, H), rgba(BG))

    # warm glow behind the triad + a fainter one behind the card
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for (cx, cy, r, a, col) in ((660, 720 + OY, 620, 46, VIOLET), (1910, 670 + OY, 520, 26, PINK)):
        gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgba(col, a))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(220)))

    # faint hex grid on the left half
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
    img.alpha_composite(grid)

    base = img
    img = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))   # the desktop layout layer
    d = ImageDraw.Draw(img)

    # header
    text(d, (120, 112), "MAGI", font("ExtraBold", 64), VIOLET, "ls")
    text(d, (330, 104), "SYSTEM  ·  BOOT ARBITRATION", font("Regular", 22), DIM, "ls")
    text(d, (2440, 92), "NEON // unit-01", font("Bold", 24), FG, "rs")
    text(d, (2440, 124), "SECURE BOOT · SBCTL CHAIN VERIFIED", font("Regular", 18), DIM, "rs")
    d.line((120, 150, 2440, 150), fill=LINE, width=2)
    d.line((120, 150, 300, 150), fill=VIOLET, width=4)
    d.line((300, 150, 460, 150), fill=PINK, width=4)

    triad(img, d)
    card(img, d)
    hints(d)

    # footer
    d.line((120, 1320, 2440, 1320), fill=LINE, width=2)
    text(d, (120, 1362), "ZENBOOK S 16  ·  RYZEN AI 9 HX 370  ·  RADEON 890M  ·  linux", font("Regular", 18), DIM, "ls")
    text(d, (2440, 1362), "MELCHIOR · BALTHASAR · CASPER", font("Regular", 18), DIM, "rs")

    base.alpha_composite(img, (0, OY))
    img, d = base, ImageDraw.Draw(base)

    # corner brackets (full canvas)
    for (x, y, sx, sy) in ((40, 40, 1, 1), (W - 40, 40, -1, 1), (40, H - 40, 1, -1), (W - 40, H - 40, -1, -1)):
        d.line((x, y, x + 70 * sx, y), fill=PINK, width=3)
        d.line((x, y, x, y + 70 * sy), fill=VIOLET, width=3)

    # scanlines
    scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scan)
    for y in range(0, H, 4):
        sd.line((0, y, W, y), fill=(0, 0, 0, 34))
    img.alpha_composite(scan)
    return img.convert("RGB").resize((FW, FH), Image.LANCZOS)


def unit(img, d, cx, cy, name, idx):
    w, h, c = 400, 210, 30
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    fill = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    ImageDraw.Draw(fill).polygon(chamfer(x0, y0, x1, y1, c), fill=rgba(PANEL, 235))
    img.alpha_composite(fill)
    d.polygon(chamfer(x0, y0, x1, y1, c), outline=VIOLET, width=3)
    d.line((x0 + 18, y0 + 58, x1 - 18, y0 + 58), fill=LINE, width=2)
    text(d, (x0 + 26, y0 + 42), name, font("ExtraBold", 28), FG, "ls")
    text(d, (x1 - 26, y0 + 42), f"· {idx}", font("Bold", 24), DIM, "rs")
    # approval stamp
    sx0, sy0, sx1, sy1 = cx - 112, y0 + 78, cx + 112, y0 + 172
    d.rectangle((sx0, sy0, sx1, sy1), outline=VIOLET, width=3)
    d.rectangle((sx0 + 7, sy0 + 7, sx1 - 7, sy1 - 7), outline=rgba(VIOLET, 110), width=1)
    text(d, (cx, sy0 + 50), "承認", ImageFont.truetype(CJK, 62), VIOLET, "mm")
    text(d, (cx, y1 - 14), "APPROVED", font("Bold", 16), PINK, "ms")


def triad(img, d):
    cx, cy = 660, 712
    top, left, right = (cx, 470), (cx - 236, 930), (cx + 236, 930)
    # connectors to the core
    for (px, py) in (top, left, right):
        d.line((cx, cy, px, py), fill=rgba(CYAN, 140), width=2)
    unit(img, d, *top, "BALTHASAR", 2)
    unit(img, d, *left, "CASPER", 3)
    unit(img, d, *right, "MELCHIOR", 1)
    # core
    r = 66
    hexpts = [(cx + r * math.cos(math.radians(60 * k)), cy + r * math.sin(math.radians(60 * k))) for k in range(6)]
    d.polygon(hexpts, fill=BG, outline=CYAN, width=3)
    text(d, (cx, cy - 4), "MAGI", font("ExtraBold", 30), VIOLET, "mm")
    text(d, (cx, cy + 24), "CORE", font("Regular", 14), DIM, "mm")
    # verdict
    vy = 1110
    f_big, f_sm = font("ExtraBold", 26), font("Regular", 20)
    left_s, right_s = "3 / 3", "  UNITS CONCUR  ·  BOOT AUTHORIZED"
    wl, wr = d.textlength(left_s, font=f_big), d.textlength(right_s, font=f_sm)
    x = cx - (wl + wr) / 2
    text(d, (x, vy), left_s, f_big, PINK, "ls")
    text(d, (x + wl, vy), right_s, f_sm, DIM, "ls")


def card(img, d):
    x0, y0, x1, y1 = CARD
    fill = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    ImageDraw.Draw(fill).rectangle(CARD, fill=rgba(BG, 240))
    img.alpha_composite(fill)
    d.rectangle(CARD, outline=LINE, width=2)
    d.rectangle((x0, y0, x1, y0 + 5), fill=VIOLET)
    text(d, (x0 + 40, y0 + 70), "SELECT SYSTEM", font("ExtraBold", 34), VIOLET, "ls")
    text(d, (x0 + 40, y0 + 108), "決議 · RESOLUTION REQUIRED", ImageFont.truetype(CJK, 20), DIM, "ls")
    text(d, (x1 - 40, y0 + 70), "03 TARGETS", font("Bold", 20), PINK, "rs")
    d.line((x0 + 40, y0 + 136, x1 - 40, y0 + 136), fill=LINE, width=2)


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


# ── selection pixmaps (9-slice) + icons ──────────────────────────────────────
def pixmaps():
    sel, bar = rgba(SEL), rgba(VIOLET)
    def save(name, w, h, cols):
        im = Image.new("RGBA", (w, h))
        for x, col in enumerate(cols):
            for y in range(h):
                im.putpixel((x, y), col)
        im.save(OUT / f"select_{name}.png")
    left = [bar] * 6 + [sel] * 10     # orange accent bar + inner padding
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


def theme():
    mx0, my0, mx1, my1 = MENU
    cx0, _, cx1, _ = CARD
    t = f'''# GRUB theme "magi-neon" (midnight neon). Generated by ~/.local/share/neon/grub-theme/build.py;
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
    left = {X(mx0)}
    top = {Y(my0)}
    width = {X(mx1 - mx0)}
    height = {X(my1 - my0)}
    item_font = "MAGI Regular 34"
    selected_item_font = "MAGI Bold 34"
    item_color = "{ITEM}"
    selected_item_color = "{VIOLET}"
    item_height = {X(ITEM_H)}
    item_padding = 25
    item_spacing = {X(ITEM_GAP)}
    icon_width = 50
    icon_height = 50
    item_icon_space = 29
    selected_item_pixmap_style = "select_*.png"
    scrollbar = false
}}

+ label {{
    id = "__timeout__"
    left = {X(cx0 + 40)}
    top = {Y(TIMEOUT_LABEL_Y)}
    width = {X(cx1 - cx0 - 80)}
    height = 34
    align = "left"
    text = "AUTO-SELECT IN %d s"
    font = "MAGI Regular 25"
    color = "{DIM}"
}}

+ progress_bar {{
    id = "__timeout__"
    left = {X(cx0 + 40)}
    top = {Y(BAR_Y - 25)}
    width = {X(cx1 - cx0 - 80)}
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
    n = lambda v: int(round(v * S))
    ny = lambda v: int(round((v + OY) * S))
    entries = [("arch", "Arch Linux"), ("windows", "Windows 11"), ("efi", "UEFI Firmware Settings")]
    fi, fs = font("Regular", 34), font("ExtraBold", 34)
    mx0, my0, mx1, _ = MENU
    ih = n(ITEM_H)
    for i, (cls, label) in enumerate(entries):
        y = ny(my0) + i * (ih + n(ITEM_GAP))
        if i == 0:
            d.rectangle((n(mx0), y, n(mx1), y + ih), fill=SEL)
            d.rectangle((n(mx0), y, n(mx0) + 6, y + ih), fill=VIOLET)
        if cls:
            ic = Image.open(OUT / "icons" / f"{cls}.png").resize((50, 50))
            img.alpha_composite(ic, (n(mx0) + 25, y + (ih - 50) // 2))
        text(d, (n(mx0) + 25 + 50 + 29, y + ih // 2), label, fs if i == 0 else fi,
             VIOLET if i == 0 else ITEM, "lm")
    cx0, _, cx1, _ = CARD
    text(d, (n(cx0 + 40), ny(TIMEOUT_LABEL_Y) + 17), "AUTO-SELECT IN 3 s", font("Regular", 25), DIM, "lm")
    bx0, bx1, by = n(cx0 + 40), n(cx1 - 40), ny(BAR_Y - 25)
    d.rectangle((bx0, by, bx1, by + 7), fill=LINE)
    d.rectangle((bx0, by, bx0 + int((bx1 - bx0) * 0.6), by + 7), fill=VIOLET)
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
