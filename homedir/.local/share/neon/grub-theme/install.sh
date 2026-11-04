#!/bin/bash
# Install the "magi-neon" GRUB theme (unit-01 board) + the unit-01 activation intro (sudo ./install.sh).
# Build first as your user: python3 build.py && python3 intro.py
#   - copies ./magi-neon to /boot/grub/themes/magi-neon (theme files aren't signature-checked)
#   - /etc/grub.d/05_unit01_intro makes grub.cfg source magi-neon/intro.cfg before the menu entries
#   - drops the "Loading Linux / initial ramdisk" echoes from /etc/grub.d/10_neon, so GRUB's last
#     frame is the bare background (= the Plymouth splash's first frame)
#   - regenerates grub.cfg
# Needs nothing new in the signed grubx64.efi: png, play, gfxterm_background, keystatus and
# configfile are already in grub-install-signed's module list.
# Backup of 10_neon: /var/backups/unit01-boot/10_neon.pre-intro (first run only).
# Undo the intro only: sudo ./install.sh --no-intro
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd)
DEST=/boot/grub/themes/magi-neon
HOOK=/etc/grub.d/05_unit01_intro
NEON=/etc/grub.d/10_neon
BK=/var/backups/unit01-boot

if [[ ${1:-} == --no-intro ]]; then
    rm -f "$HOOK"
    rm -rf "$DEST/intro" "$DEST/intro.cfg"
    grub-mkconfig -o /boot/grub/grub.cfg
    echo "intro removed"
    exit 0
fi

[[ -f $HERE/magi-neon/theme.txt && -f $HERE/magi-neon/intro.cfg ]] || { echo "build first: python3 build.py && python3 intro.py" >&2; exit 1; }
mkdir -p "$BK"
[[ -f $BK/10_neon.pre-intro ]] || cp "$NEON" "$BK/10_neon.pre-intro"

rm -rf "$DEST/intro"
mkdir -p "$DEST"
cp -r "$HERE/magi-neon/." "$DEST/"

cat > "$HOOK" <<'EOF'
#!/bin/sh
# unit-01 activation intro (~/.local/share/neon/grub-theme/install.sh): plays before the menu.
# $root is the ESP here (00_header's last search), where the theme lives.
cat <<'CFG'
if [ -f ($root)/grub/themes/magi-neon/intro.cfg ]; then source ($root)/grub/themes/magi-neon/intro.cfg; fi
CFG
EOF
chmod 755 "$HOOK"

sed -i "/^\techo\t'Loading Linux \.\.\.'$/d; /^\techo\t'Loading initial ramdisk \.\.\.'$/d" "$NEON"
grep -c "echo.*Loading" "$NEON" || true

grub-mkconfig -o /boot/grub/grub.cfg
grep -n 'intro.cfg' /boot/grub/grub.cfg
echo "installed; reboot to see it (hold Shift to skip the intro; sudo ./install.sh --no-intro removes it)"
