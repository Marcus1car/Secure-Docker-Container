#!/usr/bin/env bash
# Host-run smoke test for the entry points documented in README.md and docker-compose.yml.
# Requires: docker compose build secure-container
set -uo pipefail

cd "$(dirname "$0")/.."
fails=0

LOGS_SETUP_HINT="mkdir -p logs && sudo chown -R 10001:10001 logs && sudo chmod -R 775 logs"

logs_precheck() {
  local dir="./logs"

  if [ ! -d "$dir" ]; then
    echo "SETUP REQUIRED: $dir does not exist."
    echo "This is a host prerequisite from the README Quick Start step, not an entry-point regression."
    echo "Run:"
    echo "  $LOGS_SETUP_HINT"
    exit 2
  fi

  local owner perms owner_digit other_digit owner_writable other_writable
  owner=$(stat -c '%u' "$dir")
  perms=$(stat -c '%a' "$dir")
  owner_digit=${perms: -3:1}
  other_digit=${perms: -1}

  owner_writable=false
  if [ "$owner" = "10001" ] && [ $(( owner_digit & 2 )) -ne 0 ]; then
    owner_writable=true
  fi

  other_writable=false
  if [ $(( other_digit & 2 )) -ne 0 ]; then
    other_writable=true
  fi

  if [ "$owner_writable" != true ] && [ "$other_writable" != true ]; then
    echo "SETUP REQUIRED: $dir is not writable by the container user (uid 10001)."
    echo "Found: owner uid=$owner, perms=$perms"
    echo "This is a host prerequisite from the README Quick Start step, not an entry-point regression."
    echo "Run:"
    echo "  $LOGS_SETUP_HINT"
    exit 2
  fi
}

check() {
  local label="$1"; shift
  local out
  if out=$("$@" 2>&1) && echo "$out" | grep -q '"threat_level"\|"exit_code"'; then
    echo "PASS  $label"
  else
    echo "FAIL  $label"
    echo "$out" | sed 's/^/      /'
    fails=$((fails + 1))
  fi
}

logs_precheck

check "profile analyze (default command)" \
  docker compose --profile analyze run --rm analyze

check "profile execute (default command)" \
  docker compose --profile execute run --rm execute

check "README quick start: analyze" \
  docker compose run --rm analyze python3 analyze.py samples/dummy.pe

check "README quick start: execute" \
  docker compose run --rm execute python3 execute.py samples/safe_script.sh

check "README custom whitelist (-v before service name)" \
  docker compose run --rm \
    -v ./config/whitelist.json:/app/Secure-Docker-Container/config/whitelist.json \
    analyze python3 analyze.py samples/clean.txt

echo "---"
if [ "$fails" -ne 0 ]; then
  echo "$fails entry point(s) broken"
  exit 1
fi
echo "all entry points OK"
