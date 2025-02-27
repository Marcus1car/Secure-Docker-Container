#!/bin/sh
set -ex

if [ "$(id -u)" = "0" ]; then
  # Create directories and set permissions
  mkdir -p /app/yara-rules
  chown -R fileanalyst:fileanalyst /app/yara-rules
  chmod 770 /app/yara-rules

  # Drop privileges
  exec gosu fileanalyst "$@"
fi

exec "$@"