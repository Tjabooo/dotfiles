#!/bin/bash
free -m | awk '/^Mem:/ {
    used=($2-$7)
    total=$2
    printf "%.1fG/%.1fG\n", used/1024, total/1024
}'
