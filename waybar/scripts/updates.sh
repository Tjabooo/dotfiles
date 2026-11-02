#!/bin/sh
# waybar custom/updates: cached + locked `checkupdates` (30 min). neon-update clears the
# cache and sends RTMIN+8 after an upgrade so the count drops straight away.
cache=${XDG_RUNTIME_DIR:-/tmp}/neon-updates
exec 9>"$cache.lock"
flock 9
now=$(date +%s)
if [ -f "$cache" ] && [ $((now - $(stat -c %Y "$cache"))) -lt 1500 ]; then
  n=$(cat "$cache")
else
  n=$(checkupdates 2>/dev/null | wc -l)
  echo "$n" > "$cache"
fi
[ "${n:-0}" -gt 0 ] && echo "$n" || true
