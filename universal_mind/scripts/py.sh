#!/usr/bin/env bash
# R48-9 — THE INTERPRETER LOCK: the platform's real interpreter, found
# deterministically — never by PATH luck. An internet outage once swapped
# `python` to a dependency-less build and the whole suite silently
# failed to even import. This script is the one door every tool goes
# through (Makefile, verify, cron, probes).
#
# Resolution order (first that can import numpy+pytest wins):
#   1. UM_PYTHON env (explicit override)
#   2. The Hermes agent venv (3.11 — the interpreter every prior round
#      was built and verified on)
#   3. py -3.11 launcher
#   4. plain python (last resort, and it FAILS LOUDLY below if wrong)
set -euo pipefail

HOMEP="${LOCALAPPDATA:-$HOME/AppData/Local}"
CANDIDATES=(
  "${UM_PYTHON:-}"
  "$HOMEP/hermes/hermes-agent/venv/Scripts/python.exe"
  "C:/Users/EliteBook/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
)

for PY in "${CANDIDATES[@]}"; do
  [ -n "$PY" ] || continue
  [ -x "$PY" ] || command -v "$PY" >/dev/null 2>&1 || continue
  if "$PY" -c "import numpy, pytest, sklearn" >/dev/null 2>&1; then
    echo "$PY"
    exit 0
  fi
done

# launcher fallback
if command -v py >/dev/null 2>&1; then
  for V in 3.11 3.12 3.13; do
    if py -"$V" -c "import numpy, pytest, sklearn" >/dev/null 2>&1; then
      py -"$V" -c "import sys; print(sys.executable)"
      exit 0
    fi
  done
fi

echo "ERROR: no interpreter with numpy+pytest+sklearn found." >&2
echo "  Set UM_PYTHON to the project's python." >&2
exit 3
