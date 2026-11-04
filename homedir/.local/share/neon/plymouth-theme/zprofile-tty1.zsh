
# tty1 -> Hyprland (unit-01 boot, ~/.local/share/neon/plymouth-theme). Clear the console and hide
# its cursor first, and keep start-hyprland/Hyprland output off the screen (it lands in
# $XDG_RUNTIME_DIR/hypr/*/hyprland.log anyway): the Plymouth splash fades to #0f0f1e, tty1 stays
# that colour, then ~/.config/hypr/scripts/unit01-handoff.py takes over (and asks the password
# with hyprlock when tty1 logged in by itself). Other ttys stay plain shells.
if [[ -z $WAYLAND_DISPLAY && $(tty) == /dev/tty1 ]]; then
    printf "\e[?25l\e[H\e[2J"
    exec start-hyprland >/dev/null 2>&1
fi
