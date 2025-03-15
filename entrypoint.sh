#!/bin/sh
set -ex

if [ "$(id -u)" = "0" ]; then
  # Ensure proper permissions for mounted volumes
  chown fileanalyst:fileanalyst /app/Secure-Docker-Container/logs
  chmod -R 775 /app/Secure-Docker-Container/logs
  exec gosu fileanalyst "$@"
fi

exec "$@"