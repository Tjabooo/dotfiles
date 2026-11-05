---@module 'hl'
-- ~/.config/hypr/hyprland.lua  —  Hyprland 0.55+ (Lua config) · laptop (Zenbook S 16)
--
--  Palette: "midnight neon"
--    base    #0f0f1e   surface  #1a1a2f   overlay #2a2a45
--    text    #e0e0f0   lavender #babbf1
--    violet  #9b5de5   pink     #f15bb5   cyan    #00c6ff
--
--  After editing:  reload   (alias: hyprctl reload && hyprctl configerrors)
--  Keybind cheat sheet: SUPER+/  — every bind with a trailing "-- comment" is listed there.

local HOME = os.getenv("HOME")

------------------------------------------------------------------
-- POWER  (read on every load; neon-power reloads the config when AC is plugged/unplugged)
------------------------------------------------------------------
local function sysfs(path)
    local f = io.open(path)
    if not f then return nil end
    local v = f:read("l")
    f:close()
    return v
end
local ON_AC = sysfs("/sys/class/power_supply/AC0/online") ~= "0"

------------------------------------------------------------------
-- PROGRAMS
------------------------------------------------------------------
local terminal = "alacritty"
local browser  = "firefox"
local files    = "thunar"
local launcher = "rofi -show drun"
local discord  = "discord"
local spotify  = "spotify --enable-features=UseOzonePlatform --ozone-platform=wayland"   -- CEF, not Electron: ignores the env hint
local bin      = HOME .. "/.local/bin/"
local menu     = HOME .. "/.config/waybar/scripts/power-menu.sh"

------------------------------------------------------------------
-- MONITORS
------------------------------------------------------------------
-- 120 Hz on AC, 60 Hz on battery (the OLED panel itself draws less at 60).
hl.monitor({
    output   = "eDP-1",
    mode     = ON_AC and "2880x1800@120" or "2880x1800@60",
    position = "0x0",
    scale    = 1.5,
    bitdepth = 10,
    cm       = "srgb",
})
-- External (TV, projector, a monitor at uni): to the right of the laptop at its own best mode
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })

------------------------------------------------------------------
-- ENVIRONMENT
------------------------------------------------------------------
hl.env("HYPRLAND_USE_NO_VFR", 1)
hl.env("HYPRLAND_USE_FRACTIONAL_SCALE", 1)
-- Electron/Chromium apps (Discord, VS Code, Obsidian, Spotify…) run as native Wayland:
-- sharp at 1.5x scale instead of blurry XWayland, and less battery.
hl.env("ELECTRON_OZONE_PLATFORM_HINT", "auto")
hl.env("QT_QPA_PLATFORM", "wayland;xcb")

------------------------------------------------------------------
-- AUTOSTART
------------------------------------------------------------------
-- Daemons (waybar, dunst, hypridle, hyprpaper, cliphist, polkit agent, neon-power) are systemd
-- user units in ~/.config/systemd/user/neon-session.target: they restart when they crash and
-- their logs are in `journalctl --user -u <name>`.
-- unit-01 handoff: Plymouth ends on solid #0f0f1e, Hyprland starts on it (misc.background_color),
-- and scripts/unit01-handoff.py covers the screens in it at once, plays the unit-01 session link,
-- runs hyprlock when tty1 logged in by itself (the real password prompt), then dissolves hex by
-- hex into the desktop. The session (waybar, wallpaper, ...) waits behind the overlay so nothing
-- flashes before it.
local handoff = os.getenv("HOME") .. "/.config/hypr/scripts/unit01-handoff.py"
hl.layer_rule({ match = { namespace = "^unit01-handoff$" }, no_anim = true })
hl.on("hyprland.start", function()
    hl.exec_cmd(handoff .. " --lock")
    hl.exec_cmd(handoff .. " --wait -- \"dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP HYPRLAND_INSTANCE_SIGNATURE ELECTRON_OZONE_PLATFORM_HINT QT_QPA_PLATFORM && systemctl --user restart neon-session.target\"")
    -- Spotify + Discord live in scratchpads (SUPER+M / SUPER+D) and launch on first toggle.
end)
hl.on("hyprland.shutdown", function()
    hl.exec_cmd("systemctl --user stop neon-session.target")
end)

------------------------------------------------------------------
-- LOOK & FEEL
------------------------------------------------------------------
hl.config({
    general = {
        gaps_in          = 6,
        gaps_out         = 12,
        border_size      = 2,
        layout           = "dwindle",
        resize_on_border = true,
        col = {
            -- deck look (neon/eww, rofi, waybar): square frames, solid violet = focused, line = idle
            active_border   = "rgba(9b5de5ff)",
            inactive_border = "rgba(2a2a45ff)",
        },
    },

    decoration = {
        rounding         = 0,     -- square like the eww decks
        active_opacity   = 1.0,
        inactive_opacity = 0.95,
        shadow = {
            enabled        = ON_AC,   -- battery: no shadows
            range          = 20,
            render_power   = 3,
            color          = "rgba(9b5de540)", -- soft violet glow on the focused window
            color_inactive = "rgba(0b0b1680)",
        },
        blur = {
            enabled           = true,
            size              = 6,
            passes            = ON_AC and 3 or 1,   -- battery: one pass (looks close, a third of the GPU work)
            new_optimizations = true,
            vibrancy          = 0.18,
            noise             = 0.015,
            popups            = true,
        },
    },

    animations = { enabled = true },

    dwindle = {
        preserve_split = true,
    },

    misc = {
        disable_hyprland_logo    = true,
        disable_splash_rendering = true,
        force_default_wallpaper  = 0,
        background_color         = "rgb(0f0f1e)",   -- = the Plymouth splash's last frame (unit-01 handoff)
        mouse_move_enables_dpms  = true,
        key_press_enables_dpms   = true,
        middle_click_paste       = false,   -- same as the desktop; set true to get X11-style middle-click paste back
    },

    cursor = {
        no_hardware_cursors = true,
    },

    xwayland = {
        force_zero_scaling = true,
    },
})

------------------------------------------------------------------
-- ANIMATIONS  (snappy springs, smooth fades, a little overshoot)
------------------------------------------------------------------
hl.curve("smooth",   { type = "bezier", points = { { 0.25, 1.0 }, { 0.5, 1.0 } } })
hl.curve("overshot", { type = "bezier", points = { { 0.13, 0.99 }, { 0.29, 1.08 } } })
hl.curve("snappy",   { type = "spring", mass = 1, stiffness = 80, damping = 15 })

hl.animation({ leaf = "windows",          enabled = true, speed = 4.5, spring = "snappy" })
hl.animation({ leaf = "windowsIn",        enabled = true, speed = 4,   spring = "snappy", style = "popin 85%" })
hl.animation({ leaf = "windowsOut",       enabled = true, speed = 3,   bezier = "smooth", style = "popin 85%" })
hl.animation({ leaf = "border",           enabled = true, speed = 6,   bezier = "smooth" })
hl.animation({ leaf = "fade",             enabled = true, speed = 4,   bezier = "smooth" })
hl.animation({ leaf = "layers",           enabled = true, speed = 3.5, bezier = "smooth", style = "fade" })
hl.animation({ leaf = "workspaces",       enabled = true, speed = 3.5, bezier = "overshot", style = "slide" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 3.5, bezier = "smooth", style = "slidevert" })

------------------------------------------------------------------
-- INPUT
------------------------------------------------------------------
hl.config({
    input = {
        kb_layout    = "us,se",
        kb_options   = "grp:win_space_toggle,fkeys:basic_13-24",
        follow_mouse = 1,
        touchpad = {
            natural_scroll       = false,
            scroll_factor        = 0.2,
            disable_while_typing = true,
        },
    },
})

hl.device({ name = "asup1207:00-093a:3012-touchpad", sensitivity = 0.2 })
hl.device({ name = "razer-razer-viper-v3-pro",       sensitivity = -0.5 })

hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })

------------------------------------------------------------------
-- SCRATCHPADS  (summon over whatever you're watching/coding)
------------------------------------------------------------------
local scratchpads = {
    ["special:discord"] = { cmd = discord,  gaps = 60 },
    ["special:music"]   = { cmd = spotify,  gaps = 80 },
    ["special:term"]    = { cmd = terminal, gaps = 80 },
    ["special:files"]   = { cmd = "kitty --class yazi-scratch -e yazi", gaps = 80 },
}
for name, pad in pairs(scratchpads) do
    hl.workspace_rule({ workspace = name, gaps_out = pad.gaps })
end
-- launch the app when its scratchpad is summoned empty
hl.on("workspace.created", function(ws)
    local pad = scratchpads[ws.name] or scratchpads["special:" .. ws.name]
    if pad and ws.is_empty then hl.exec_cmd(pad.cmd) end
end)

------------------------------------------------------------------
-- WINDOW RULES
------------------------------------------------------------------
-- Keep Discord / Spotify / yazi in their scratchpads however they're opened
hl.window_rule({ name = "discord-scratch", match = { class = "^(discord|vesktop)$" },  workspace = "special:discord silent" })
hl.window_rule({ name = "spotify-scratch", match = { class = "^(Spotify|spotify)$" },  workspace = "special:music silent" })
hl.window_rule({ name = "yazi-scratch",    match = { class = "^(yazi-scratch)$" },     workspace = "special:files silent" })

-- Translucency (slightly less than before so code stays readable)
hl.window_rule({ name = "glass-editors", match = { class = "^(Code|dev\\.zed\\.Zed|jetbrains-idea)$" }, opacity = "0.9" })
hl.window_rule({ name = "glass-discord", match = { class = "^(discord|vesktop)$" }, opacity = "0.80" })
hl.window_rule({ name = "glass-spotify", match = { class = "^(Spotify|spotify)$" }, opacity = "0.85" })

-- YouTube / movie Picture-in-Picture: floating, pinned, bottom-right
hl.window_rule({
    name              = "pip",
    match             = { title = "^(Picture-in-Picture)$" },
    float             = true,
    pin               = true,
    keep_aspect_ratio = true,
    size              = { "monitor_w*0.28", "monitor_h*0.28" },
    move              = { "monitor_w*0.71", "monitor_h*0.69" },
})

-- Don't let the screen sleep while anything is fullscreen (movies, YouTube)
hl.window_rule({ name = "no-idle-fullscreen", match = { class = ".*" }, idle_inhibit = "fullscreen" })

-- Small utility windows float centred instead of tiling
hl.window_rule({
    name   = "float-utils",
    match  = { class = "^(pavucontrol|org\\.pulseaudio\\.pavucontrol|nm-connection-editor|blueman-manager)$" },
    float  = true,
    center = true,
    size   = { "monitor_w*0.45", "monitor_h*0.55" },
})
hl.window_rule({
    name   = "float-dialogs",
    match  = { title = "^(Open File|Open Folder|Save As|Select a File|File Upload.*|File Operation Progress)$" },
    float  = true,
    center = true,
})

-- Satty (screenshot editor) opens as a centred floating window
hl.window_rule({
    name   = "satty",
    match  = { class = "^(com\\.gabm\\.satty|satty)$" },
    float  = true,
    center = true,
    size   = { "monitor_w*0.75", "monitor_h*0.75" },
})

------------------------------------------------------------------
-- LAYER RULES  (blur behind the bar and launcher)
------------------------------------------------------------------
hl.layer_rule({ match = { namespace = "waybar" }, blur = true, ignore_alpha = 0.3 })
hl.layer_rule({ match = { namespace = "rofi" },   blur = true, ignore_alpha = 0.3 })

------------------------------------------------------------------
-- KEYBINDS   (the trailing comment is what SUPER+/ shows)
------------------------------------------------------------------
-- Apps
hl.bind("SUPER + T",    hl.dsp.exec_cmd(terminal))  -- terminal
hl.bind("ALT + RETURN", hl.dsp.exec_cmd("alacritty msg create-window || alacritty"))  -- terminal (fast window)
hl.bind("SUPER + B",    hl.dsp.exec_cmd(browser))  -- browser
hl.bind("SUPER + E",    hl.dsp.exec_cmd("kitty --class yazi -e yazi"))  -- yazi file manager
hl.bind("SUPER + R",    hl.dsp.exec_cmd(launcher))  -- app launcher
hl.bind("SUPER + C",    hl.dsp.exec_cmd("code"))  -- VS Code
hl.bind("SUPER + Z",    hl.dsp.exec_cmd("/usr/bin/zeditor"))  -- Zed
hl.bind("SUPER + I",    hl.dsp.exec_cmd("intellij-idea-ultimate-edition"))  -- IntelliJ
hl.bind("SUPER + O",    hl.dsp.exec_cmd("obsidian"))  -- Obsidian
hl.bind("SUPER + P",    hl.dsp.exec_cmd("parsecd"))  -- Parsec
hl.bind("SUPER + SHIFT + F23", hl.dsp.exec_cmd("gaiaui"))  -- GAIA UI
hl.bind("SUPER + V",    hl.dsp.exec_cmd(bin .. "clipdeck show"))  -- clipboard (every machine)
hl.bind("SUPER + SHIFT + A", hl.dsp.exec_cmd(terminal .. " --class archfleet --title Archfleet -e " .. bin .. "archfleet"))  -- fleet dashboard

-- Scratchpads
hl.bind("SUPER + D",         hl.dsp.workspace.toggle_special("discord"))  -- Discord scratchpad
hl.bind("SUPER + ALT + V",   hl.dsp.exec_cmd(bin .. "neon-vpn menu"))  -- VPN deck (on/off, relay, lockdown)
hl.bind("SUPER + M",         hl.dsp.workspace.toggle_special("music"))  -- Spotify scratchpad
hl.bind("SUPER + grave",     hl.dsp.workspace.toggle_special("term"))  -- drop-down terminal
hl.bind("SUPER + SHIFT + E", hl.dsp.workspace.toggle_special("files"))  -- yazi scratchpad

-- Bar / notifications / help
hl.bind("SUPER + W",         hl.dsp.exec_cmd("pkill -SIGUSR1 waybar"))  -- show / hide waybar (movies)
hl.bind("SUPER + N",         hl.dsp.exec_cmd("dunstctl history-pop"))  -- last notification again
hl.bind("SUPER + SHIFT + N", hl.dsp.exec_cmd("dunstctl close-all"))  -- clear notifications
hl.bind("SUPER + slash", hl.dsp.exec_cmd(bin .. "neon-keys show"))  -- this cheat sheet
-- while the sheet is open (neon-keys enters this submap only once the overlay is on screen):
-- Esc / Enter / SUPER+/ close it
local function close_keys()
    hl.exec_cmd(bin .. "neon-keys hide")
    hl.dispatch(hl.dsp.submap("reset"))
end
hl.define_submap("keys", function()
    hl.bind("Escape", close_keys)
    hl.bind("Return", close_keys)
    hl.bind("SUPER + slash", close_keys)
    hl.bind("catchall", close_keys)  -- any other key closes it too: the submap can never trap you
end)

-- Windows
hl.bind("CTRL + Q",  hl.dsp.window.close())  -- close window
hl.bind("SUPER + S", hl.dsp.window.float({ action = "toggle" }))  -- float / tile
hl.bind("SUPER + F", hl.dsp.window.fullscreen())  -- fullscreen
hl.bind("SUPER + J", hl.dsp.layout("togglesplit"))  -- flip split

for _, dir in ipairs({ "left", "right", "up", "down" }) do
    hl.bind("SUPER + " .. dir,         hl.dsp.focus({ direction = dir }))  -- focus window
    hl.bind("SUPER + SHIFT + " .. dir, hl.dsp.window.move({ direction = dir }))  -- move window
end

hl.bind("SUPER + mouse:272", hl.dsp.window.drag(),   { mouse = true })  -- drag window
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })  -- resize window
hl.bind("ALT + mouse:272",   hl.dsp.window.resize(), { mouse = true })  -- resize window (touchpad)

-- Groups (tabs)
hl.bind("SUPER + G",   hl.dsp.group.toggle())  -- tab group on / off
hl.bind("SUPER + tab", hl.dsp.group.next({ forward = false }))  -- next tab in group

-- Workspaces: SUPER+n = go to, ALT+n = send window
for i = 1, 10 do
    local key = tostring(i % 10)
    hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = i }))  -- go to workspace
    hl.bind("ALT + " .. key,   hl.dsp.window.move({ workspace = i }))  -- send window there
end
hl.bind("SUPER + mouse_down", hl.dsp.focus({ workspace = "e+1" }))  -- next workspace
hl.bind("SUPER + mouse_up",   hl.dsp.focus({ workspace = "e-1" }))  -- previous workspace

-- Screenshots (satty: Enter copies + closes, saved copies go to ~/Pictures/Screenshots)
local shot = bin .. "neon-shot "
hl.bind("Print",         hl.dsp.exec_cmd(shot .. "region"))  -- region → editor
hl.bind("SHIFT + Print", hl.dsp.exec_cmd(shot .. "region-clip"))  -- region → clipboard
hl.bind("ALT + Print",   hl.dsp.exec_cmd(shot .. "window"))  -- window → editor
hl.bind("CTRL + Print",  hl.dsp.exec_cmd(shot .. "output"))  -- whole screen → editor
hl.bind("SUPER + Print", hl.dsp.exec_cmd(shot .. "edit"))  -- edit last saved screenshot

-- Lock / power
hl.bind("SUPER + L",      hl.dsp.exec_cmd("pidof hyprlock || hyprlock"))  -- lock
hl.bind("SUPER + Escape", hl.dsp.exec_cmd(menu))  -- power menu (incl. reboot to Windows)

-- Hardware keys (on-screen bar; work on the lock screen, volume/brightness repeat when held)
local osd = bin .. "neon-osd "
hl.bind("XF86MonBrightnessUp",   hl.dsp.exec_cmd(osd .. "light up"),   { locked = true, repeating = true })  -- brightness up
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd(osd .. "light down"), { locked = true, repeating = true })  -- brightness down
hl.bind("XF86AudioRaiseVolume",  hl.dsp.exec_cmd(osd .. "vol up"),     { locked = true, repeating = true })  -- volume up
hl.bind("XF86AudioLowerVolume",  hl.dsp.exec_cmd(osd .. "vol down"),   { locked = true, repeating = true })  -- volume down
hl.bind("XF86AudioMute",         hl.dsp.exec_cmd(osd .. "vol mute"),   { locked = true })  -- mute output
hl.bind("XF86AudioMicMute",      hl.dsp.exec_cmd(osd .. "mic mute"),   { locked = true })  -- mute microphone
hl.bind("XF86AudioPlay",         hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })  -- play / pause
hl.bind("XF86AudioNext",         hl.dsp.exec_cmd("playerctl next"),        { locked = true })  -- next track
hl.bind("XF86AudioPrev",         hl.dsp.exec_cmd("playerctl previous"),    { locked = true })  -- previous track

-- >>> clipdeck
-- clipboard picker (SUPER+V): `clipdeck show` opens the overlay, then enters this submap.
-- Each entry's key copies it here; ←/→, PgUp/PgDn, Home/End flip pages; Esc / Enter / SUPER+V / any other key close it.
local clipdeck = HOME .. "/.local/bin/clipdeck "
local function clip_close()
    hl.exec_cmd(clipdeck .. "hide")
    hl.dispatch(hl.dsp.submap("reset"))
end
hl.define_submap("clip", function()
    for k in ("1234567890QWERTYUIOPASDFGHJKL"):gmatch(".") do
        hl.bind(k, hl.dsp.exec_cmd(clipdeck .. "pick " .. k))
    end
    -- flip every column a page (held keys repeat); the same keys then pick from that page
    for key, dir in pairs({ Right = "next", Left = "prev", Next = "next", Prior = "prev", Home = "first", End = "last" }) do
        hl.bind(key, hl.dsp.exec_cmd(clipdeck .. "page " .. dir), { repeating = true })
    end
    hl.bind("Escape", clip_close)
    hl.bind("Return", clip_close)
    hl.bind("SUPER + V", clip_close)
    hl.bind("catchall", clip_close)  -- any other key closes it too: the submap can never trap you
end)
-- <<< clipdeck
