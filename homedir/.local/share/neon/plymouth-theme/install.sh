#!/bin/bash
# Install the "unit01" Plymouth splash on this machine (run: sudo ./install.sh).
# Build first with ./build.py (as your user); this only installs what's in ./unit01.
#   - plymouth package, theme -> /usr/share/plymouth/themes/unit01, plymouthd.conf Theme=unit01
#   - unit01-splash-hold.service: plymouth-quit (and so the tty1 login) waits for the animation
#   - mkinitcpio HOOKS += plymouth (right after systemd), rebuilds the initramfs images
#   - /etc/default/grub: "splash" + a neon console palette (colour 0 = #0f0f1e) on the kernel
#     command line; regenerates grub.cfg
#   - tty1 autologin ($SUDO_USER), silent: no banner, no prompt, so the splash's last frame
#     (#0f0f1e) runs straight into Hyprland (~/.zprofile execs start-hyprland on tty1).
#     The password is still asked: ~/.config/hypr/scripts/unit01-handoff.py --lock runs hyprlock
#     before the desktop appears whenever this autologin drop-in exists.
#   - every getty re-applies /etc/vconsole.conf (the font is skipped at boot while Plymouth
#     holds the consoles: "All allocated virtual consoles are busy")
# Backups of edited files go to /var/backups/unit01-boot/ (first run only).
# Undo: sudo ./install.sh --remove
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd)
NAME=unit01
THEME=/usr/share/plymouth/themes/$NAME
BK=/var/backups/unit01-boot
LIB=/usr/local/lib/$NAME-boot

if [[ ${1:-} == --remove ]]; then
    systemctl disable $NAME-splash-hold.service 2>/dev/null || true
    rm -f /etc/systemd/system/$NAME-splash-hold.service
    rm -f /etc/systemd/system/getty@tty1.service.d/$NAME-autologin.conf /etc/systemd/system/getty@.service.d/$NAME-vconsole.conf
    rm -rf "$LIB" "$THEME"
    [[ -f $BK/mkinitcpio.conf ]] && cp "$BK/mkinitcpio.conf" /etc/mkinitcpio.conf
    [[ -f $BK/grub ]] && cp "$BK/grub" /etc/default/grub
    [[ -f $BK/plymouthd.conf ]] && cp "$BK/plymouthd.conf" /etc/plymouth/plymouthd.conf || rm -f /etc/plymouth/plymouthd.conf
    systemctl daemon-reload
    grub-mkconfig -o /boot/grub/grub.cfg
    mkinitcpio -P
    echo "removed (plymouth package left installed)"
    exit 0
fi

[[ -f $HERE/$NAME/$NAME.script ]] || { echo "build first: python3 $HERE/build.py" >&2; exit 1; }
pacman -Q plymouth &>/dev/null || pacman -S --needed --noconfirm plymouth

mkdir -p "$BK"
[[ -f $BK/mkinitcpio.conf ]] || cp /etc/mkinitcpio.conf "$BK/mkinitcpio.conf"
[[ -f $BK/grub ]] || cp /etc/default/grub "$BK/grub"
[[ -f $BK/plymouthd.conf || ! -f /etc/plymouth/plymouthd.conf ]] || cp /etc/plymouth/plymouthd.conf "$BK/plymouthd.conf"

# theme
rm -rf "$THEME"
install -d "$THEME"
install -m644 "$HERE"/$NAME/*.png "$HERE"/$NAME/$NAME.plymouth "$HERE"/$NAME/$NAME.script "$THEME"/
mkdir -p /etc/plymouth
cat > /etc/plymouth/plymouthd.conf <<EOF
[Daemon]
Theme=$NAME
ShowDelay=0
DeviceTimeout=8
EOF

# boot hold
install -Dm755 "$HERE/$NAME/$NAME-splash-hold" "$LIB/$NAME-splash-hold"
install -Dm644 "$HERE/$NAME/$NAME-splash-hold.service" /etc/systemd/system/$NAME-splash-hold.service
systemctl daemon-reload
systemctl enable $NAME-splash-hold.service

# tty1 autologin + console font after Plymouth
AUTOLOGIN_USER=${SUDO_USER:-tjabo}
install -d /etc/systemd/system/getty@tty1.service.d /etc/systemd/system/getty@.service.d
cat > /etc/systemd/system/getty@tty1.service.d/$NAME-autologin.conf <<EOF
# unit-01 boot (plymouth-theme/install.sh): silent autologin. The splash plays the "login";
# Hyprland's unit01-handoff.py --lock then asks the real password with hyprlock.
[Service]
ExecStart=
ExecStart=-/usr/bin/agetty -o '-p -f -- \\\\u' --skip-login --noissue --nonewline --autologin $AUTOLOGIN_USER %I \$TERM
EOF
cat > /etc/systemd/system/getty@.service.d/$NAME-vconsole.conf <<'EOF'
# unit-01 boot (plymouth-theme/install.sh): apply the vconsole.conf font once Plymouth has let go
[Service]
ExecStartPre=-/usr/lib/systemd/systemd-vconsole-setup /dev/%I
EOF
systemctl daemon-reload
systemctl cat getty@tty1.service | grep -E '^ExecStart'

# initramfs hook: plymouth right after systemd (the systemd hook must come first)
sed -i -E '/^HOOKS=/ { s/ plymouth\b//; s/\(base systemd /(base systemd plymouth / }' /etc/mkinitcpio.conf
grep -E '^HOOKS=' /etc/mkinitcpio.conf

# kernel command line: splash, and the console palette = the neon terminal (alacritty) with colour 0
# = #0f0f1e, so tty1 under the splash and before Hyprland is the splash's last colour
VT='vt.default_red=15,255,129,255,138,155,92,186,74,255,165,255,169,241,139,224 vt.default_grn=15,107,199,195,168,93,207,187,74,143,214,216,189,91,233,224 vt.default_blu=30,129,132,113,255,229,230,241,106,163,167,155,255,181,253,240'
grep -qE '^GRUB_CMDLINE_LINUX_DEFAULT=".*\bsplash\b' /etc/default/grub || \
    sed -i -E 's/^(GRUB_CMDLINE_LINUX_DEFAULT="[^"]*\bquiet\b)/\1 splash/' /etc/default/grub
grep -qE '^GRUB_CMDLINE_LINUX_DEFAULT=".*vt\.default_red' /etc/default/grub || \
    sed -i -E "s/^(GRUB_CMDLINE_LINUX_DEFAULT=\"[^\"]*)\"/\1 $VT\"/" /etc/default/grub
grep -E '^GRUB_CMDLINE_LINUX_DEFAULT' /etc/default/grub

grub-mkconfig -o /boot/grub/grub.cfg
mkinitcpio -P
echo "installed; reboot to see it (sudo ./install.sh --remove to undo)"
