#!/usr/bin/env bash

API_KEY="e86wdau2kemmoh1j5fdr842p1m8pb44cc77akz4m"
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
  "rain"|"rain_shower") icon="🌧️" ;;
  "snow") icon="❄️" ;;
  "storm") icon="⛈️" ;;
  *) icon="" ;;
esac

if [ -n "$temp" ]; then
  echo "${icon} ${temp}°"
else
  echo "${icon}"
fi
