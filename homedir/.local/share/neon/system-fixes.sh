#!/usr/bin/env bash
# system-fixes.sh — root-level fixes found by the 2026-11-02 scan of this laptop (Zenbook S 16).
# Run as YOUR user (not with sudo): it calls sudo itself and asks before every step,
# so you can skip any of them. Safe to re-run: finished steps detect that and skip.
set -uo pipefail
V=$'\e[38;2;155;93;229m' P=$'\e[38;2;241;91;181m' D=$'\e[38;2;108;108;138m' B=$'\e[1m' X=$'\e[0m'
step() { printf '\n%s%s▌ %s%s\n%s%s%s\n' "$V" "$B" "$1" "$X" "$D" "$2" "$X"; read -rp "  ${P}do it? [y/N] ${X}" a; [[ $a == [yY]* ]]; }
[[ $EUID -eq 0 ]] && { echo "run this as your normal user, not root"; exit 1; }
sudo -v || exit 1

# ── 1. fstab ────────────────────────────────────────────────────────────────────────
if grep -q '^/dev/nvme0n1p1 /boot' /etc/fstab &&
   step "fstab: disable the second /boot line" \
"  /etc/fstab mounts /boot twice: your real ESP (UUID FF19-9BA6, nvme0n1p6) AND the Windows
  ESP (nvme0n1p1). Today the first one wins, but if the order ever flips, kernel updates
  land on Windows' 260 MB partition and Arch stops booting. The line gets commented out."; then
  sudo cp -a /etc/fstab /etc/fstab.bak-2026-11-02
  sudo sed -i 's|^/dev/nvme0n1p1 /boot|# duplicate /boot (Windows ESP), disabled 2026-11-02: /dev/nvme0n1p1 /boot|' /etc/fstab
  sudo systemctl daemon-reload
  sudo findmnt --verify --tab-file /etc/fstab && echo "  fstab ok (backup: /etc/fstab.bak-2026-11-02)"
fi

# ── 2. systemd-boot Windows entry ───────────────────────────────────────────────────
if [[ -f /boot/EFI/Linux/bootmgfw.efi ]] &&
   step "systemd-boot: move bootmgfw.efi out of EFI/Linux" \
"  EFI/Linux/ is the folder for Linux UKIs. logind re-parses everything in it and logs
  'bootmgfw.efi is not a UKI' as an ERROR ~3,300 times per boot (half your journal noise).
  The SAME file moves to EFI/WindowsChain/ and windows.conf points there, so Windows boots
  exactly as before (the stray 'options chainloader' GRUB line is dropped too)."; then
  sudo mkdir -p /boot/EFI/WindowsChain
  sudo cp -a /boot/loader/entries/windows.conf /boot/loader/windows.conf.bak-2026-11-02
  sudo mv /boot/EFI/Linux/bootmgfw.efi /boot/EFI/WindowsChain/bootmgfw.efi
  printf 'title Windows 11\nefi /EFI/WindowsChain/bootmgfw.efi\n' | sudo tee /boot/loader/entries/windows.conf >/dev/null
  bootctl list --no-pager 2>/dev/null | grep -A3 -i windows
fi

# ── 3. journald size cap ────────────────────────────────────────────────────────────
if [[ ! -f /etc/systemd/journald.conf.d/size.conf ]] &&
   step "journal: cap at 500 MB (now $(journalctl --disk-usage 2>/dev/null | grep -o '[0-9.]*[KMG]' | head -1))" \
"  Your disk is 97 % full; the journal has no cap beyond journald's 10 %-of-disk default."; then
  sudo mkdir -p /etc/systemd/journald.conf.d
  printf '[Journal]\nSystemMaxUse=500M\n' | sudo tee /etc/systemd/journald.conf.d/size.conf >/dev/null
  sudo systemctl restart systemd-journald
  sudo journalctl --vacuum-size=500M
fi

# ── 4. missing packages ─────────────────────────────────────────────────────────────
need=()
for p in pacman-contrib hyprpolkitagent xdg-desktop-portal-hyprland zoxide; do pacman -Q "$p" &>/dev/null || need+=("$p"); done
if (( ${#need[@]} )) &&
   step "install: ${need[*]}" \
"  pacman-contrib          checkupdates (waybar counter), paccache, pacdiff (neon-update)
  hyprpolkitagent         you have NO polkit agent: the autostart pointed at polkit-gnome,
                          which isn't installed, so GUI password prompts (pkexec, GParted,
                          Bottles…) silently fail. neon-session.target starts it.
  xdg-desktop-portal-hyprland  screen sharing of single windows/regions in Discord,
                          Firefox, OBS; only the wlroots portal is installed now
  zoxide                  'z <dir>' jumping (already wired into .zshrc)"; then
  sudo pacman -S --needed "${need[@]}"
  systemctl --user daemon-reload
  systemctl --user restart neon-session.target
fi

# ── 5. pacman cache ─────────────────────────────────────────────────────────────────
if pacman -Q pacman-contrib &>/dev/null && ! systemctl is-enabled -q paccache.timer 2>/dev/null &&
   step "pacman cache: $(du -sh /var/cache/pacman/pkg 2>/dev/null | cut -f1) → keep the last 2 versions, weekly" \
"  paccache.timer trims it every week from now on (keeps 3 by default); right now it drops
  everything but the newest 2 versions, and all versions of uninstalled packages."; then
  sudo systemctl enable --now paccache.timer
  sudo paccache -rk2
  sudo paccache -ruk0
fi

# ── 6. user caches (no sudo) ────────────────────────────────────────────────────────
if step "user caches: yay build dirs ($(du -sh ~/.cache/yay 2>/dev/null | cut -f1)) + pip cache ($(du -sh ~/.cache/pip 2>/dev/null | cut -f1))" \
"  Both are pure download/build caches and refill on demand. NOT touched: ~/.cache/huggingface
  (73 GB of models; delete the ones you don't need yourself: 'hf cache scan' / 'hf cache delete')."; then
  rm -rf ~/.cache/yay/* ~/.cache/pip
  echo "  free now: $(df -h --output=avail / | tail -1)"
fi

# ── 7. debug packages + orphans ─────────────────────────────────────────────────────
dbg=$(pacman -Qq | grep -- '-debug$')
if [[ -n $dbg ]] &&
   step "remove $(wc -w <<<"$dbg") -debug packages" \
"  Debug symbols for AUR builds (~/.config/pacman/makepkg.conf stops new ones being made):
  $(tr '\n' ' ' <<<"$dbg")"; then
  sudo pacman -Rns $dbg
fi
# tools you use directly that only came in as dependencies: keep them
keep=(go pnpm ruff qt6-wayland)
orph=$(pacman -Qdtq | grep -vxF -f <(printf '%s\n' "${keep[@]}"))
if [[ -n $orph ]] &&
   step "remove $(wc -w <<<"$orph") orphaned packages (${keep[*]} are kept)" \
"  Installed as dependencies of things that are gone. The kept ones are marked as explicitly
  installed so they stop showing up as orphans. pacman shows the list and asks again."; then
  sudo pacman -D --asexplicit "${keep[@]}"
  sudo pacman -Rns $orph
fi

# ── 8. services ─────────────────────────────────────────────────────────────────────
if systemctl is-enabled -q supergfxd 2>/dev/null &&
   step "disable supergfxd" "  GPU-switching daemon, but this Zenbook only has the Radeon 890M iGPU: nothing to switch."; then
  sudo systemctl disable --now supergfxd
fi
if systemctl is-enabled -q input-remapper 2>/dev/null &&
   step "disable input-remapper (fails every boot)" \
"  input-remapper-git was built for Python 3.13; Arch is on 3.14 now ('No module named
  inputremapper'). If you still use it, answer N and run:  yay -S --rebuild input-remapper-git"; then
  sudo systemctl disable --now input-remapper
fi
if systemctl is-enabled -q libvirtd.service 2>/dev/null &&
   step "libvirtd: start on demand instead of at every boot" \
"  The libvirtd sockets stay enabled, so virt-manager / virsh still start it the moment you
  use them; it just isn't running all day on battery for a VM you rarely boot."; then
  sudo systemctl disable libvirtd.service
fi

# ── 9. left for you ─────────────────────────────────────────────────────────────────
printf '\n%s%s▌ left for you%s\n' "$V" "$B" "$X"
echo "  .pacnew files to merge (sudo DIFFPROG='nvim -d' pacdiff):"
find /etc \( -name '*.pacnew' -o -name '*.pacsave' \) 2>/dev/null | sed 's/^/    /'
echo "  free space now: $(df -h --output=avail / | tail -1)"
