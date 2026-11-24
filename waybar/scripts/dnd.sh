#!/usr/bin/env bash
# Do not disturb for waybar: pauses/resumes dunst.
#   dnd.sh          -> waybar JSON (bell, or bell-off + "activated" when paused)
#   dnd.sh toggle   -> flip it and refresh the bar (signal 17)
case "$1" in
  toggle)
    dunstctl set-paused toggle
    pkill -RTMIN+17 waybar
    ;;
  *)
    nl='\n'  # JSON newline escape, kept literal
    if [ "$(dunstctl is-paused 2>/dev/null)" = true ]; then
      n=$(dunstctl count waiting 2>/dev/null || echo 0)
      icon=$(printf '\363\260\202\233')   # nf-md-bell_off
      printf '{"text":"%s","class":"activated","tooltip":"Do not disturb: on (%s waiting)%sClick to let notifications through"}\n' "$icon" "$n" "$nl"
    else
      icon=$(printf '\363\260\202\232')   # nf-md-bell
      printf '{"text":"%s","class":"off","tooltip":"Do not disturb: off%sClick to silence notifications"}\n' "$icon" "$nl"
    fi
    ;;
esac
