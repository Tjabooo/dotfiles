#!/usr/bin/env bash
# Current weather for the lock screen, e.g. "⛅ 7°". Open-Meteo needs no API key.
# Location: WEATHER_LAT / WEATHER_LON (default Stockholm). Offline: prints nothing.

LAT=${WEATHER_LAT:-59.33}
LON=${WEATHER_LON:-18.07}

data=$(curl -fsS --max-time 8 \
  "https://api.open-meteo.com/v1/forecast?latitude=$LAT&longitude=$LON&current=temperature_2m,weather_code,is_day" \
  2>/dev/null) || exit 0

temp=$(jq -r '.current.temperature_2m // empty' <<<"$data")
code=$(jq -r '.current.weather_code // empty' <<<"$data")
day=$(jq -r '.current.is_day // 1' <<<"$data")
[ -n "$temp" ] || exit 0

# WMO weather codes: https://open-meteo.com/en/docs
case "$code" in
  0)                         [ "$day" = 1 ] && icon="☀️" || icon="🌕" ;;
  1)                         [ "$day" = 1 ] && icon="🌤️" || icon="🌕" ;;
  2)                         icon="⛅" ;;
  3)                         icon="☁️" ;;
  45|48)                     icon="🌫️" ;;
  51|53|55|56|57|61|63|65|66|67|80|81|82) icon="🌧️" ;;
  71|73|75|77|85|86)         icon="❄️" ;;
  95|96|99)                  icon="⛈️" ;;
  *)                         icon="" ;;
esac

printf '%s %s°\n' "$icon" "$(printf '%.0f' "$temp")"
