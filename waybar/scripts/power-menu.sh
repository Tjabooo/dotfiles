#!/usr/bin/env bash
# ~/.config/waybar/scripts/power-menu.sh  —  wofi power menu (SUPER+Escape / waybar power button)
options=$'  Lock\n\U000f0904  Suspend\n  Reboot\n  Reboot to Windows\n  Shut down\n\U000f0343  Log out'

choice=$(printf '%s' "$options" | wofi --dmenu --prompt power --width 280 --lines 6 --cache-file /dev/null)

case "$choice" in
  *Lock)        pidof hyprlock || hyprlock ;;
  *Suspend)     (pidof hyprlock || hyprlock) & sleep 0.5; systemctl suspend ;;
  *"Reboot to Windows")
    # booted through GRUB → grub-reboot (one-shot, asks for your password via polkit);
    # booted through systemd-boot → its own one-shot entry
    grubnum=$(efibootmgr | sed -n 's/^Boot\([0-9A-F]\{4\}\)\* GRUB\b.*/\1/p' | head -1)
    if [ -n "$grubnum" ] && [ "$(efibootmgr | sed -n 's/^BootCurrent: //p')" = "$grubnum" ]; then
      pkexec grub-reboot "Windows 11" && systemctl reboot
    else
      systemctl reboot --boot-loader-entry=windows.conf
    fi || notify-send -u critical "Power menu" "Couldn't set Windows as the next boot" ;;
  *Reboot)      systemctl reboot ;;
  *"Shut down") systemctl poweroff ;;
  *"Log out")   systemctl --user stop neon-session.target; hyprctl dispatch 'hl.dsp.exit()' ;;
esac
