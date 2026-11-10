#!/bin/sh
# Builds a copy of the system ALSA mixer paths with the internal mic capped, so
# neither WirePlumber nor an app's auto gain can push it past MAX_STEP.
# Rebuilt on every WirePlumber start, so package updates carry over.
# Capture steps run 0..63 at 0.75 dB each, 23 = 0 dB, 47 = +18 dB. Mic Boost stays at 0 dB.
MAX_STEP=47
src=/usr/share/alsa-card-profile/mixer/paths
dst=$HOME/.local/share/acp-mic-cap/paths
rm -rf "$dst"; mkdir -p "$dst"
ln -s "$src"/* "$dst"/
f=analog-input-internal-mic.conf
rm "$dst/$f"
awk -v max="$MAX_STEP" '
  /^\[/ { sec = $0 }
  sec == "[Element Capture]" && /^volume = merge/ { print; print "volume-limit = " max; next }
  sec == "[Element Internal Mic Boost]" && /^volume = merge/ { print "volume = zero"; next }
  { print }' "$src/$f" > "$dst/$f"
