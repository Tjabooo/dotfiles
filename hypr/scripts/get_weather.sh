#!/usr/bin/env bash

# Meteosource API key: $METEOSOURCE_API_KEY, or the first line of ~/.config/hypr/meteosource.key
# (kept out of the repo). Without one the lock screen just shows no weather.
API_KEY=${METEOSOURCE_API_KEY:-$(head -n1 "$HOME/.config/hypr/meteosource.key" 2>/dev/null)}
[ -n "$API_KEY" ] || exit 0
LOCATION="stockholm"
UNITS="metric"

data=$(curl -s "https://www.meteosource.com/api/v1/free/point?place_id=$LOCATION&sections=current&units=$UNITS&key=$API_KEY")

temp=$(echo "$data" | jq -r '.current.temperature' | awk '{print int($1)}')
summary=$(echo "$data" | jq -r '.current.icon')

case "$summary" in
  "sunny"|"Sunny") icon="☀️" ;;
  "mostly_sunny") icon="🌤️" ;;
  "clear"|"Clear") icon="🌕" ;;
  "partly_sunny"|"mostly_cloudy"|"partly_clear") icon="⛅" ;;
  "cloudy"|"Cloudy") icon="☁️" ;;
  "overcast"|"Overcast") icon="☁️" ;;
  "fog"|"Fog") icon="🌫️" ;;
  "rain"|"rain_shower"|"psbl_rain") icon="🌧️" ;;
  "snow") icon="❄️" ;;
  "storm") icon="⛈️" ;;
  *) icon="" ;;
esac

if [ -n "$temp" ]; then
  echo "${icon} ${temp}°"
else
  echo "${icon}"
fi
