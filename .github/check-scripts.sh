#!/usr/bin/env bash
# Checks every tracked script by its type: Python files (by .py or shebang) must parse,
# sh/bash scripts (by .sh or shebang) must pass shellcheck. zsh is skipped (shellcheck has no zsh).
# Usage: check-scripts.sh [shellcheck severity, default warning]
set -uo pipefail
severity=${1:-warning}
status=0 py=0 sh=0
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  first=$(head -n1 "$f" 2>/dev/null | tr -d '\r' || true)
  case "$first" in *zsh*) continue ;; esac
  if [[ $f == *.py || $first == '#!'*python* ]]; then
    py=$((py + 1))
    python3 -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1])' "$f" || status=1
  elif [[ $f == *.sh || $first =~ ^\#!.*(/|[[:space:]])(sh|bash|dash)([[:space:]]|$) ]]; then
    sh=$((sh + 1))
    shellcheck -S "$severity" "$f" || status=1
  fi
done < <(git ls-files -z)
echo "checked $py Python and $sh shell scripts"
exit $status
