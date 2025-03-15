#!/bin/sh
set -ex

# if container running as root
if [ "$(id -u)" = "0" ]; then
  # Ensure proper permissions for mounted volumes
  chown fileanalyst:fileanalyst /app/Secure-Docker-Container/logs
  exec gosu fileanalyst "$@"
fi

exec "$@"