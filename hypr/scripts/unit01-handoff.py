#!/usr/bin/python3
"""unit-01 handoff: the bridge from the Plymouth splash into the Hyprland desktop.

Plymouth ends on solid #0f0f1e. Hyprland starts on the same colour (misc.background_color).
This overlay maps on every monitor in that colour and draws a short unit-01 "session link"
(sync line, 接続 header, ENTRY PLUG / A10 NERVE / power chips, where the power chip reads
the battery: 外部電源 on AC, 内部電源 + time to 活動限界 on battery). With --lock it then
starts hyprlock (the boot autologs in, so this is the real password prompt) and waits for it.
Finally it dissolves hex by hex outward from the line, revealing the desktop underneath.
Sibling of the desktop's magi-handoff.py (Tjabooo/dotfiles-desktop).

Modes
  unit01-handoff.py [--lock]        run the overlay (exec once at Hyprland start); --lock runs
                                    hyprlock before the dissolve when tty1 autologs in
  unit01-handoff.py --wait -- CMD   wait until the overlay covers the screens, then exec CMD
                                    (gate for the session target, so nothing flashes before it)
  unit01-handoff.py --preview DIR [BG.png]   render preview frames (no compositor needed)
Env: UNIT01_HANDOFF_LEAD (s of plain colour first, default 0.4), UNIT01_HANDOFF_DEBUG=1 (fps).
"""
import glob
import json
import math
import os
import subprocess
import sys
import threading
import time

SIG = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "nosig")
READY = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), f"unit01-handoff-{SIG}.ready")

# ------------------------------------------------------------------ gate mode (no GTK import)
if len(sys.argv) > 1 and sys.argv[1] == "--wait":
    cmd = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[2:]
    deadline = time.monotonic() + 3.0
    while not os.path.exists(READY) and time.monotonic() < deadline:
        time.sleep(0.03)
    os.execvp("sh", ["sh", "-c", " ".join(cmd)])

import cairo  # noqa: E402
import gi  # noqa: E402

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402


def rgb(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


BG = "#0f0f1e"
PANEL = "#1a1a2f"
LINE = "#2a2a45"
FG = "#e0e0f0"
DIM = "#6c6c8a"
VIOLET = "#9b5de5"
PINK = "#f15bb5"
GREEN = "#9ef01a"

# timeline (seconds, after LEAD of plain colour while Hyprland settles the outputs)
LEAD = float(os.environ.get("UNIT01_HANDOFF_LEAD", "0.4"))
T_LINE0, T_LINE1 = 0.25, 0.80        # sync line draws outward
T_TEXT = 0.45                        # header fades in
T_CHIPS = (0.62, 0.74, 0.86)         # ENTRY PLUG, A10 NERVE, power
T_CODE = 0.98                        # status line
T_LINKED = 1.20                      # earliest wave start (held until the desktop is up)
T_LOCK = 1.25                        # --lock: hyprlock starts here; the wave waits for the unlock
UNLOCK_GAP = 0.25                    # after the unlock, before the wave
WAVE = 1.05                          # wave duration, centre to far corner
EDGE_IN, OPEN = 0.16, 0.18           # hex edge glow lead-in, then fade-out
R = 34                               # hex radius (logical px)
MAX_HOLD = 3.0                       # never wait longer than this for the desktop
DEBUG = bool(os.environ.get("UNIT01_HANDOFF_DEBUG"))


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def clamp01(x):
    return min(max(x, 0.0), 1.0)


def power():
    """('ac', None) | ('bat', (percent, 'H:MM:SS' or None)) from sysfs; ('ac', None) if unknown."""
    try:
        for ps in glob.glob("/sys/class/power_supply/*"):
            if open(f"{ps}/type").read().strip() == "Mains" and open(f"{ps}/online").read().strip() == "1":
                return "ac", None
        for ps in glob.glob("/sys/class/power_supply/BAT*"):
            cap = int(open(f"{ps}/capacity").read())
            left = None
            try:
                e, p = int(open(f"{ps}/energy_now").read()), int(open(f"{ps}/power_now").read())
                if p > 500000:
                    s = int(e / p * 3600)
                    left = f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}"
            except (OSError, ValueError):
                pass
            return "bat", (cap, left)
    except (OSError, ValueError):
        pass
    return "ac", None


class Scene:
    """Geometry for one monitor in global layout coordinates."""

    def __init__(self, mx, my, mw, mh, main, span):
        self.mx, self.my, self.mw, self.mh = mx, my, mw, mh
        self.main = main
        cx, cy = main[0] + main[2] / 2, main[1] + main[3] / 2
        self.cx, self.cy = cx, cy
        self.is_main = (mx, my, mw, mh) == tuple(main)
        dx, dy = 1.5 * R, math.sqrt(3) * R
        dmax = max(math.hypot((x - cx) * 0.30, (y - cy)) for x, y in span)
        self.hexes = []
        r = R + 0.8
        c0 = int((mx - R) // dx) - 1
        c1 = int((mx + mw + R) // dx) + 1
        for c in range(c0, c1 + 1):
            hx = c * dx
            off = (dy / 2) if c % 2 else 0
            r0 = int((my - R - off) // dy) - 1
            r1 = int((my + mh + R - off) // dy) + 1
            for rr in range(r0, r1 + 1):
                hy = rr * dy + off
                d = math.hypot((hx - cx) * 0.30, hy - cy) / dmax
                jitter = (math.sin(c * 12.9898 + rr * 78.233) * 43758.5453) % 1.0
                t_open = WAVE * (d ** 0.85) + 0.07 * jitter
                pts = [(hx - mx + r * math.cos(math.pi / 3 * k), hy - my + r * math.sin(math.pi / 3 * k))
                       for k in range(6)]
                self.hexes.append((t_open, pts))
        self.hexes.sort(key=lambda h: h[0])
        self.wave_len = max(h[0] for h in self.hexes) + OPEN + 0.05


def hexpath(cr, pts):
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path()


def text(cr, s, x, y, size, color, weight="Regular", spacing=0.0, anchor="c", family="JetBrainsMono Nerd Font",
         measure=False):
    layout = PangoCairo.create_layout(cr)
    fd = Pango.FontDescription.from_string(f"{family} {weight}")
    fd.set_absolute_size(size * Pango.SCALE)
    layout.set_font_description(fd)
    attrs = Pango.AttrList()
    if spacing:
        attrs.insert(Pango.attr_letter_spacing_new(int(spacing * Pango.SCALE)))
    layout.set_attributes(attrs)
    layout.set_text(s, -1)
    w, h = layout.get_pixel_size()
    if measure:
        return w
    ox = {"c": -w / 2, "l": 0, "r": -w}[anchor]
    cr.move_to(x + ox, y - h / 2)
    cr.set_source_rgba(*color)
    PangoCairo.show_layout(cr, layout)
    return w


JP = "Noto Sans CJK JP"


def lattice(cr, sc, ly):
    """The faint hex lattice, drawn once into a surface: stroking ~1000 hexes every frame costs
    ~65 ms at the panel's 2x buffer. Done on the first (plain colour) frame, where it isn't seen."""
    surf = cr.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA, int(sc.mw), int(sc.mh))
    c2 = cairo.Context(surf)
    c2.set_line_width(1.0)
    for _, pts in sc.hexes:
        hexpath(c2, pts)
    grad = cairo.LinearGradient(0, ly - 380, 0, ly + 380)
    grad.add_color_stop_rgba(0.0, *rgb(LINE, 0))
    grad.add_color_stop_rgba(0.5, *rgb(LINE, 0.22 * 2.2))
    grad.add_color_stop_rgba(1.0, *rgb(LINE, 0))
    c2.set_source(grad)
    c2.stroke()
    sc.lattice = surf


def draw(cr, sc, t, wave_t0, pw):
    """t: seconds since the overlay first showed; wave_t0: when the dissolve starts (or None)."""
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.set_source_rgba(0, 0, 0, 0)
    cr.paint()
    cr.set_operator(cairo.OPERATOR_OVER)
    w_t = (t - wave_t0) if wave_t0 is not None else -1.0
    lx, ly = sc.cx - sc.mx, sc.cy - sc.my

    # ---------------- background: solid until the wave, then the closed hexes
    if w_t < 0:
        cr.set_source_rgba(*rgb(BG))
        cr.paint()
    else:
        # closed hexes live on a persistent surface; each is cut out of it once, when it starts to
        # open, so a frame only draws the few hexes in transition (cheap at the 2x buffer)
        if getattr(sc, "closed", None) is None:
            sc.closed = cr.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA, int(sc.mw), int(sc.mh))
            c = cairo.Context(sc.closed)
            c.set_source_rgba(*rgb(BG))
            c.paint()
            sc.ci = 0
        c = cairo.Context(sc.closed)
        c.set_operator(cairo.OPERATOR_CLEAR)
        c.set_antialias(cairo.ANTIALIAS_NONE)
        n = 0
        while sc.ci < len(sc.hexes) and sc.hexes[sc.ci][0] <= w_t:
            hexpath(c, sc.hexes[sc.ci][1])
            sc.ci += 1
            n += 1
        if n:
            c.fill()
        cr.set_source_surface(sc.closed, 0, 0)
        cr.paint()
        cr.set_antialias(cairo.ANTIALIAS_NONE)
        buckets, edges = {}, {}
        for t_open, pts in sc.hexes:
            dt = w_t - t_open
            if dt <= -EDGE_IN:
                break                                  # sorted by t_open: the rest are still closed
            if dt >= OPEN:
                continue
            if dt > 0:
                buckets.setdefault(round((1 - dt / OPEN) * 12), []).append(pts)
            ea = clamp01((dt + EDGE_IN) / EDGE_IN) if dt <= 0 else 1 - dt / OPEN
            edges.setdefault(round(ea * 10), []).append(pts)
        for q, lst in buckets.items():
            for pts in lst:
                hexpath(cr, pts)
            cr.set_source_rgba(*rgb(BG, q / 12))
            cr.fill()
        cr.set_line_width(1.4)                         # no AA: the 2x buffer is downscaled anyway
        for q, lst in edges.items():
            if not q:
                continue
            for pts in lst:
                hexpath(cr, pts)
            cr.set_source_rgba(*rgb(VIOLET, 0.85 * q / 10))
            cr.stroke()
        cr.set_antialias(cairo.ANTIALIAS_DEFAULT)

    # ---------------- faint hex lattice foreshadowing the dissolve
    if getattr(sc, "lattice", None) is None and w_t < 0.2:
        lattice(cr, sc, ly)
    if w_t < 0.2:
        la = 0.22 * ease_out((t - T_LINE0) / 0.6) * (1 - clamp01(w_t / 0.2) if w_t > 0 else 1)
        if la > 0.01:
            cr.set_source_surface(sc.lattice, 0, 0)
            cr.paint_with_alpha(la / 0.22)

    # ---------------- the sync line (global, spans every monitor)
    grow = ease_out((t - T_LINE0) / (T_LINE1 - T_LINE0))
    if grow > 0:
        fade = 1 - clamp01(w_t / 0.35) if w_t > 0 else 1.0
        flash = math.exp(-((t - (wave_t0 if wave_t0 is not None else 99)) / 0.08) ** 2)
        half = grow * 2000 * 1.1
        x0, x1 = lx - half, lx + half
        for lw, a in ((9, 0.10), (3.5, 0.25), (1.4, 1.0)):
            cr.set_line_width(lw)
            g = cairo.LinearGradient(x0, 0, x1, 0)
            g.add_color_stop_rgba(0.0, *rgb(PINK, 0))
            g.add_color_stop_rgba(0.5, *rgb(GREEN if flash > 0.3 else VIOLET, min(1, a * fade * (1 + 2 * flash))))
            g.add_color_stop_rgba(1.0, *rgb(PINK, 0))
            cr.set_source(g)
            cr.move_to(x0, ly)
            cr.line_to(x1, ly)
            cr.stroke()

    # ---------------- text block (main monitor only)
    if sc.is_main:
        tf = 1 - clamp01(w_t / 0.22) if w_t > 0 else 1.0
        a = ease_out((t - T_TEXT) / 0.25) * tf
        if a > 0:
            wj = text(cr, "接続", 0, 0, 24, None, "Medium", 0, "l", JP, measure=True)
            wt = text(cr, "UNIT-01 SESSION LINK", 0, 0, 21, None, "Bold", 4, "l", measure=True)
            hx = lx - (wj + 16 + wt) / 2
            text(cr, "接続", hx, ly - 36, 24, rgb(GREEN, a), "Medium", 0, "l", JP)
            text(cr, "UNIT-01 SESSION LINK", hx + wj + 16, ly - 36, 21, rgb(FG, a), "Bold", 4, "l")
        kind, info = pw
        if kind == "ac":
            pchip, pon = "UMBILICAL", "外部"
        else:
            pchip, pon = f"BATTERY {info[0]}%", "内部"
        chips = (("ENTRY PLUG", "同期"), ("A10 NERVE", "同期"), (pchip, pon))
        cw, gap = 176, 14
        x = lx - (3 * cw + 2 * gap) / 2
        for i, ((nm, on_s), tc) in enumerate(zip(chips, T_CHIPS)):
            ca = ease_out((t - (tc - 0.12)) / 0.15) * tf
            on = ease_out((t - tc) / 0.10)
            if ca > 0:
                cr.set_line_width(1.3)
                cr.rectangle(x + 0.5, ly + 24.5, cw, 34)
                cr.set_source_rgba(*rgb(GREEN, ca * (0.15 + 0.85 * on) * 0.95 if on > 0 else 0.0))
                cr.fill_preserve()
                cr.set_source_rgba(*rgb(GREEN if on > 0 else LINE, ca))
                cr.stroke()
                col = rgb(BG, ca) if on > 0.5 else rgb(DIM, ca)
                text(cr, nm, x + 12, ly + 41, 13.5, col, "Bold", 1.2, "l")
                text(cr, on_s if on > 0.5 else "──", x + cw - 22, ly + 41, 13, col, "Bold", 0, "c", JP)
            x += cw + gap
        ca = ease_out((t - T_CODE) / 0.2) * tf
        if ca > 0:
            if kind == "ac":
                code = "CODE : 000   ·   EXTERNAL POWER   ·   DESKTOP ONLINE"
            elif info[1]:
                code = f"CODE : 000   ·   INTERNAL POWER   ·   ACTIVE TIME {info[1]}"
            else:
                code = f"CODE : 000   ·   INTERNAL POWER {info[0]}%   ·   DESKTOP ONLINE"
            text(cr, code, lx, ly + 84, 12.5, rgb(DIM, ca), "Regular", 2.5, "c")


# ------------------------------------------------------------------ preview mode
def preview(outdir, bgpath=None):
    os.makedirs(outdir, exist_ok=True)
    W, H = 1920, 1200
    main = (0, 0, W, H)
    sc = Scene(0, 0, W, H, main, [(0, 0), (W, 0), (0, H), (W, H)])
    bg = cairo.ImageSurface.create_from_png(bgpath) if bgpath else None
    for pw in (("ac", None), ("bat", (76, "02:01:07"))):
        for t in (0.5, 0.9, 1.1, 1.3, 1.55, 1.8, 2.05):
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            cr = cairo.Context(surf)
            if bg:
                cr.set_source_surface(bg, 0, 0)
                cr.paint()
            layer = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            draw(cairo.Context(layer), sc, t, T_LINKED, pw)
            cr.set_source_surface(layer, 0, 0)
            cr.paint()
            surf.write_to_png(os.path.join(outdir, f"{pw[0]}-t{t:.2f}.png"))
    print("wave length", round(sc.wave_len, 2), "s; hexes", len(sc.hexes))


if len(sys.argv) > 1 and sys.argv[1] == "--preview":
    preview(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    sys.exit(0)


# ------------------------------------------------------------------ overlay mode
def touch_ready():
    try:
        with open(READY, "w"):
            pass
    except OSError:
        pass


def desktop_up():
    """True once the wallpaper and waybar layers exist (or Hyprland can't be asked)."""
    try:
        out = subprocess.run(["hyprctl", "layers", "-j"], capture_output=True, text=True, timeout=1).stdout
        names = set()

        def walk(o):
            if isinstance(o, dict):
                if "namespace" in o:
                    names.add(o["namespace"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(json.loads(out))
        return bool(names & {"wallpaper", "hyprpaper", "swaybg"}) and "waybar" in names
    except Exception:
        return True


def run_lock(state):
    """hyprlock until it exits 0 (unlocked); one retry if it dies at once. Then mark unlocked."""
    for attempt in range(3):
        t0 = time.monotonic()
        try:
            rc = subprocess.run(["hyprlock"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL).returncode
        except OSError as e:
            print(f"unit01-handoff: hyprlock failed to start: {e}", file=sys.stderr)
            break
        if rc == 0 or time.monotonic() - t0 > 5:
            break
        print(f"unit01-handoff: hyprlock exited {rc} after {time.monotonic() - t0:.1f}s, retrying", file=sys.stderr)
        time.sleep(0.3)
    state["unlocked_at"] = time.monotonic()


AUTOLOGIN = "/etc/systemd/system/getty@tty1.service.d/unit01-autologin.conf"


def main():
    # --lock only matters when tty1 logs in by itself (plymouth-theme/install.sh); after a typed
    # login the password was just given. UNIT01_LOCK=always|never overrides.
    mode = os.environ.get("UNIT01_LOCK", "auto")
    lock = "--lock" in sys.argv and (mode == "always" or (mode == "auto" and os.path.exists(AUTOLOGIN)))
    try:
        os.unlink(READY)
    except OSError:
        pass
    try:
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import Gdk, GLib, Gtk, GtkLayerShell
    except Exception:
        touch_ready()
        if lock:
            subprocess.Popen(["hyprlock"])
        raise

    display = Gdk.Display.get_default()
    mons = [display.get_monitor(i) for i in range(display.get_n_monitors())]
    geos = [(m.get_geometry().x, m.get_geometry().y, m.get_geometry().width, m.get_geometry().height) for m in mons]
    # main monitor: the built-in panel if it is there, else the highest refresh rate
    main_i = max(range(len(mons)), key=lambda i: (mons[i].get_refresh_rate(), mons[i].is_primary()))
    for i, m in enumerate(mons):
        if geos[i][:2] == (0, 0):
            main_i = i
            break
    span = [(x, y) for gx, gy, gw, gh in geos for x, y in ((gx, gy), (gx + gw, gy), (gx, gy + gh), (gx + gw, gy + gh))]
    pw = power()

    state = {"t0": None, "wave_t0": None, "drawn": set(), "up": False, "done": False,
             "lock_started": False, "unlocked_at": None, "last": time.monotonic()}

    def poll():
        start = time.monotonic()
        while not state["done"]:
            if desktop_up() or time.monotonic() - start > MAX_HOLD:
                state["up"] = True
                return
            time.sleep(0.1)

    wins, scenes = [], []
    for i, (m, g) in enumerate(zip(mons, geos)):
        sc = Scene(*g, geos[main_i], span)
        win = Gtk.Window()
        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(win, "unit01-handoff")
        GtkLayerShell.set_monitor(win, m)
        GtkLayerShell.set_exclusive_zone(win, -1)
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.NONE)
        for e in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(win, e, True)
        win.set_app_paintable(True)
        vis = win.get_screen().get_rgba_visual()
        if vis:
            win.set_visual(vis)

        def on_draw(w, cr, sc=sc, i=i):
            now = time.monotonic()
            state["last"] = now
            if state["t0"] is None:
                state["t0"] = now
            t = now - state["t0"] - LEAD
            if lock and not state["lock_started"] and t >= T_LOCK:
                state["lock_started"] = True
                threading.Thread(target=run_lock, args=(state,), daemon=True).start()
            if state["wave_t0"] is None and t >= T_LINKED and state["up"]:
                if not lock:
                    state["wave_t0"] = t
                elif state["unlocked_at"] is not None:
                    state["wave_t0"] = max(t, state["unlocked_at"] - state["t0"] - LEAD + UNLOCK_GAP)
            draw(cr, sc, t, state["wave_t0"], pw)
            if DEBUG:
                state.setdefault("frames", []).append((i, t, time.monotonic() - now))
            if i not in state["drawn"]:
                state["drawn"].add(i)
                if len(state["drawn"]) == len(wins):
                    GLib.timeout_add(40, lambda: (touch_ready(), False)[1])
                    threading.Thread(target=poll, daemon=True).start()
            if state["wave_t0"] is not None and t - state["wave_t0"] > max(s.wave_len for s in scenes):
                state["done"] = True
                GLib.idle_add(Gtk.main_quit)
            return True

        win.connect("draw", on_draw)
        win.connect("realize", lambda w: w.get_window().input_shape_combine_region(cairo.Region(), 0, 0))
        win.add_tick_callback(lambda w, clock: (w.queue_draw(), True)[1])
        wins.append(win)
        scenes.append(sc)

    for w in wins:
        w.show_all()

    # safety: never leave the screens covered. While hyprlock runs the overlay is hidden anyway
    # and may get no frames; the clock restarts at the unlock.
    def watchdog():
        if state["done"]:
            return False
        ref = state["unlocked_at"] if lock and state["unlocked_at"] else (state["t0"] or time.monotonic())
        if lock and state["lock_started"] and state["unlocked_at"] is None:
            return True
        if time.monotonic() - ref > MAX_HOLD + 5:
            Gtk.main_quit()
            return False
        return True
    GLib.timeout_add(500, watchdog)
    Gtk.main()
    touch_ready()
    if DEBUG:
        fr = state.get("frames", [])
        for i in range(len(wins)):
            ts = [f[1] for f in fr if f[0] == i]
            dr = sorted(f[2] for f in fr if f[0] == i)
            gaps = sorted(b - a for a, b in zip(ts, ts[1:]))
            if len(gaps) > 2:
                print(f"mon{i}: {len(ts)} frames over {ts[-1]:.2f}s, draw median {dr[len(dr)//2]*1000:.1f}ms "
                      f"max {dr[-1]*1000:.1f}ms, gap median {gaps[len(gaps)//2]*1000:.1f}ms "
                      f"p95 {gaps[int(len(gaps)*.95)]*1000:.1f}ms, wave at {state['wave_t0']}")
                fi = [f for f in fr if f[0] == i]
                slow = [(round(a[1], 2), round((b[1] - a[1]) * 1000), round(b[2] * 1000)) for a, b in zip(fi, fi[1:])
                        if b[1] - a[1] > 0.04]
                print("slow frames (t, gap ms, draw ms):", slow[:12])


if __name__ == "__main__":
    try:
        main()
    finally:
        touch_ready()
